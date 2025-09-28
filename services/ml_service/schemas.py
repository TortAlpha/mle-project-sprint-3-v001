from typing import Dict, List, Union, Optional
from pydantic import BaseModel, Field

FeatureValue = Union[int, float, str, bool, None]

class PredictItem(BaseModel):
    user_id: Union[int, str] = Field(..., examples=["u-123", 42])
    features: Dict[str, FeatureValue] = Field(
        ...,
        description="Сырые признаки как в исходном CSV. "
                    "Пайплайн сам создаёт дополнительные фичи и делает предобработку.",
        examples=[{
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
        }]
    )

class PredictBatchRequest(BaseModel):
    items: List[PredictItem] = Field(..., min_items=1, description="Список объектов для предсказания")

class PredictResponseItem(BaseModel):
    user_id: Union[int, str]
    prediction: float

class PredictBatchResponse(BaseModel):
    results: List[PredictResponseItem]