python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r services/ml_service/requirements.txt

export PYTHONPATH=$(pwd)

export MODEL_DIR=$(pwd)/services/models
export PORT=8765

uvicorn services.ml_service.main:app --host 0.0.0.0 --port ${PORT} --reload