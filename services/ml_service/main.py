import os
import json
from typing import List, Dict, Any

import pandas as pd
import yaml

from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from services.ml_service.schemas import (
    PredictItem, PredictBatchRequest,
    PredictResponseItem, PredictBatchResponse
)

from prometheus_fastapi_instrumentator import Instrumentator

DEFAULT_MODEL_DIR = os.getenv(
    "MODEL_DIR",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "models"))
)
MODEL_DIR = DEFAULT_MODEL_DIR

from mlflow import sklearn as mlflow_sklearn

app = FastAPI(
    title="Real Estate Price API",
    description="FastAPI-сервис для предсказания цены (единый sklearn-пайплайн из MLflow, локально из ./models)"
)

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
)
instrumentator.instrument(app)

import time
from prometheus_client import Counter, Histogram, Gauge, Summary

# сколько предсказаний сделали (по endpoint'у)
PREDICTIONS_TOTAL = Counter(
    "app_predictions_total",
    "Total number of predictions",
    ["endpoint"]
)

# ошибки инференса (этап: валидация/преобразование/модель)
INFERENCE_ERRORS_TOTAL = Counter(
    "app_inference_errors_total",
    "Total number of inference errors",
    ["endpoint", "stage"]
)

# задержка предсказаний (сек)
PREDICTION_LATENCY = Histogram(
    "app_prediction_latency_seconds",
    "Prediction latency in seconds",
    buckets=(0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5)
)

# состояние загрузки модели
MODEL_LOADED = Gauge(
    "app_model_loaded",
    "Model loaded flag (1=loaded, 0=not loaded)"
)

# распределение предсказанных цен (сумма/кол-во для среднего, квантилей)
PRED_VALUE = Summary(
    "app_predicted_price",
    "Summary of predicted price"
)

MODEL = None
FEATURE_ORDER: List[str] = []  # порядок входных колонок из сигнатуры (если есть)

def _maybe_load_feature_order(model_dir: str) -> List[str]:
    """
    Пробуем вытащить порядок входных фич для DataFrame:
    1) из MLmodel.signature (inputs)
    2) (fallback) из final_selected_features.json — просто как подсказку
    Если ничего нет — вернём пустой список (будем строить по объединению ключей запроса).
    """
    mlmodel_path = os.path.join(model_dir, "MLmodel")
    try:
        if os.path.exists(mlmodel_path):
            with open(mlmodel_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            sig = data.get("signature")
            if sig and "inputs" in sig:
                inputs = sig["inputs"]
                # В MLflow inputs может быть json-строкой — распарсим
                if isinstance(inputs, str):
                    inputs = json.loads(inputs)
                # Ожидаем список объектов вида {"name": "...", "type": "..."}
                names = [col.get("name") for col in inputs if isinstance(col, dict) and "name" in col]
                if names:
                    return names
    except Exception:
        pass

    # Fallback — просто список фич для справки (может не совпадать с «сырыми» колонками)
    feat_json = os.path.join(model_dir, "final_selected_features.json")
    if os.path.exists(feat_json):
        try:
            with open(feat_json, "r", encoding="utf-8") as f:
                arr = json.load(f)
            if isinstance(arr, list) and all(isinstance(x, str) for x in arr):
                return arr
        except Exception:
            pass

    return []


def _load_model():
    global MODEL, FEATURE_ORDER

    if not os.path.exists(MODEL_DIR):
        raise RuntimeError(f"MODEL_DIR not found: {MODEL_DIR}")

    MODEL = mlflow_sklearn.load_model(MODEL_DIR)
    FEATURE_ORDER = _maybe_load_feature_order(MODEL_DIR)

    print(f"[i] Model loaded from: {MODEL_DIR}")
    if FEATURE_ORDER:
        print(f"[i] Feature order (from signature or fallback): {FEATURE_ORDER}")
    else:
        print("[i] No feature order found; will build columns from request keys.")

@app.on_event("startup")
def _on_startup():
    instrumentator.expose(app, endpoint="/metrics", include_in_schema=False)
    try:
        _load_model()
        MODEL_LOADED.set(1)
    except Exception:
        MODEL_LOADED.set(0)
        raise


@app.get("/", summary="Healthcheck / info")
def root():
    return {
        "status": "ok",
        "model_dir": MODEL_DIR,
        "feature_order_len": len(FEATURE_ORDER),
        "for testing": "go to /docs",
    }


@app.post("/predict", response_model=PredictBatchResponse, summary="Предсказать цену")
def predict(req: PredictBatchRequest):
    if MODEL is None:
        INFERENCE_ERRORS_TOTAL.labels(endpoint="/predict", stage="startup").inc()
        raise HTTPException(status_code=500, detail="Model is not loaded")

    t0 = time.perf_counter()
    endpoint = "/predict"
    try:
        if len(req.items) == 0:
            return PredictBatchResponse(results=[])

        rows = [it.features for it in req.items]

        # порядок колонок
        if FEATURE_ORDER:
            cols = FEATURE_ORDER
            for i, r in enumerate(rows):
                missing = [c for c in cols if c not in r]
                if missing:
                    INFERENCE_ERRORS_TOTAL.labels(endpoint=endpoint, stage="validation").inc()
                    raise HTTPException(
                        status_code=422,
                        detail=f"Item #{i} is missing required features: {missing}"
                    )
        else:
            cols = sorted(rows[0].keys())

        try:
            X = pd.DataFrame(rows, columns=cols).fillna(0)
        except Exception as e:
            INFERENCE_ERRORS_TOTAL.labels(endpoint=endpoint, stage="build_df").inc()
            raise HTTPException(status_code=400, detail=f"Failed to build dataframe: {e}")

        # Предсказание
        try:
            preds = MODEL.predict(X)
        except Exception as e:
            INFERENCE_ERRORS_TOTAL.labels(endpoint=endpoint, stage="model_predict").inc()
            raise HTTPException(status_code=400, detail=f"Inference error: {e}")

        for p in preds:
            try:
                PRED_VALUE.observe(float(p))
            except Exception:
                pass

        out = [
            PredictResponseItem(user_id=item.user_id, prediction=float(pred))
            for item, pred in zip(req.items, preds)
        ]
        return PredictBatchResponse(results=out)

    finally:
        dt = time.perf_counter() - t0
        PREDICTION_LATENCY.observe(dt)
        PREDICTIONS_TOTAL.labels(endpoint=endpoint).inc()

try:
    from services.ml_service.load_test import make_test_load as _make_test_load

    @app.get("/make_test_load", summary="Запустить небольшую тестовую нагрузку (если включен модуль)")
    def make_test_load():
        _make_test_load()
        return {"detail": "load started"}
except Exception:
    pass

example_body = {
    "items": [
        {
            "user_id": "u-1",
            "features": {
                "flat_id": 123456,
                "building_id": 98765,
                "total_area": 55.0,
                "living_area": 35.0,
                "kitchen_area": 10.0,
                "floor": 5,
                "floors_total": 16,
                "flats_count": 120,
                "ceiling_height": 2.8,
                "rooms": 2,
                "build_year": 2005,
                "building_type_int": 2,
                "is_apartment": 0,
                "studio": 0,
                "has_elevator": 1,
                "latitude": 59.93,
                "longitude": 30.33
            }
        }
    ]
}

# добавлю пример для быстрого тестирования работы + видно сигнатуру
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    paths = openapi_schema.get("paths", {})
    if "/predict" in paths and "post" in paths["/predict"]:
        paths["/predict"]["post"]["requestBody"] = {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/PredictBatchRequest"},
                    "example": example_body,
                }
            }
        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi