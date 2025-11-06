# Real Estate Price Prediction API

Project Description

This project is a FastAPI microservice for predicting real estate prices.
The service is based on a trained ML model (RandomForest + feature engineering pipeline), saved in MLflow format and loaded locally at service startup.
The service wraps the model in a REST API and provides:
- /predict endpoint for price predictions;
- /metrics endpoint with Prometheus-format metrics for monitoring;
- Swagger UI documentation at /docs.

Goals
- Create a reproducible and isolated microservice for the ML model.
- Provide a convenient REST API for integration with other systems.
- Add quality and performance monitoring using Prometheus and Grafana.
- Simplify deployment using Docker and Docker Compose.

Technologies Used
- Python 3.10 - main development language.
- FastAPI - API framework.
- MLflow - ML model storage and loading.
- scikit-learn - model training.
- Prometheus + Grafana - monitoring system and dashboards.
- Docker, Docker Compose - containerization and service orchestration.
- pydantic - input data validation.
