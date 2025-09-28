# Инструкции по запуску микросервиса

Каждая инструкция выполняется из директории репозитория mle-sprint3-completed
Если необходимо перейти в поддиректорию, напишите соотвесвтующую команду

## 1. FastAPI микросервис в виртуальном окружение
```bash
# для запуска нужно запустить из главной директории sh services/ml_service/run.sh 

sh services/ml_service/run.sh 

# python3 -m venv .venv
# source .venv/bin/activate
# pip install --upgrade pip
# pip install -r services/ml_service/requirements.txt
# export PYTHONPATH=$(pwd)
# export MODEL_DIR=$(pwd)/services/models
# export PORT=8765
# uvicorn services.ml_service.main:app --host 0.0.0.0 --port ${PORT} --reload
```

### Пример curl-запроса к микросервису

```bash
curl -X 'POST' \
  'http://localhost:8765/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
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
  }'
```


## 2. FastAPI микросервис в Docker-контейнере

```bash
docker build -t real-estate-api:latest -f services/Dockerfile_ml_service services
docker run --rm \
  --name real-estate-api \
  -p 8765:8765 \
  --env-file services/.env \
  -v "$(pwd)/services/models:/app/models:ro" \
  real-estate-api:latest
```

### Пример curl-запроса к микросервису

```bash
# просто проверяю healthcheck
curl http://localhost:8765/ 

# проверяю модель
curl -X 'POST' \
  'http://localhost:8765/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
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
  }'
```

## 3. Docker compose для микросервиса и системы моониторинга

```bash
cd services
docker compose up --build
```

### Пример curl-запроса к микросервису

```bash
# !не забыть порт в vscode прокинуть
curl -X 'POST' \
  'http://localhost:8765/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "items": [
    {
      "user_id": "u-1",
      "features": {
        "flat_id": 123456,
        "building_id": 98765,
        "total_area": 55,
        "living_area": 35,
        "kitchen_area": 10,
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
}'
```

## 4. Скрипт симуляции нагрузки
```bash
# команды необходимые для запуска скрипта
# формула количества N_total ≈ USERS * floor( DURATION / ( SLEEP + t_req ) )
# t_req — средняя задержка одного POST

# чтобы запустить нагрузку нужно послать гет на /make_test_load

curl -X 'GET' \
  'http://localhost:8765/make_test_load' \
  -H 'accept: application/json'
```

Адреса сервисов:
- микросервис: http://localhost:8765
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000