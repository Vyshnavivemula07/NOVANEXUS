from pathlib import Path
import json
import math

import joblib
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.terrain import get_terrain


BASE_DIR = Path(__file__).resolve().parents[1]

MODEL_PATH = BASE_DIR / "models" / "landslide_model.pkl"
FEATURES_PATH = BASE_DIR / "models" / "features.json"


model = joblib.load(MODEL_PATH)

with open(FEATURES_PATH, "r", encoding="utf-8") as f:
    FEATURES = json.load(f)


app = FastAPI(
    title="Earth Sentinel",
    description="AI-Based Landslide Early Warning and Risk Monitoring System",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://earth-sentinel-jade.vercel.app",
],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PredictionRequest(BaseModel):
    rainfall_mm: float = Field(ge=0)
    elevation_m: float = Field(ge=0)
    slope_deg: float = Field(ge=0, le=90)
    aspect_deg: float = Field(ge=0, le=360)


class PredictionResponse(BaseModel):
    probability: float
    risk_score: int
    risk_level: str
    inputs: dict

class SensorData(BaseModel):
    device_id: str = "ESP32-EARTH-SENTINEL"
    latitude: float
    longitude: float
    rainfall_mm: float = Field(ge=0)
    soil_moisture: float = Field(ge=0, le=100)
    tilt_deg: float
    vibration: float = Field(ge=0)

def classify_risk(score: int) -> str:
    if score >= 75:
        return "Critical"
    if score >= 50:
        return "High"
    if score >= 25:
        return "Moderate"
    return "Low"

def analyze_sensor_condition(
    rainfall_mm: float,
    soil_moisture: float,
    tilt_deg: float,
    vibration: float,
):
    warnings = []

    if rainfall_mm >= 100:
        warnings.append("Heavy rainfall detected")
    elif rainfall_mm >= 50:
        warnings.append("Elevated rainfall detected")

    if soil_moisture >= 80:
        warnings.append("High soil moisture detected")
    elif soil_moisture >= 65:
        warnings.append("Elevated soil moisture detected")

    if abs(tilt_deg) >= 10:
        warnings.append("Significant ground tilt detected")
    elif abs(tilt_deg) >= 5:
        warnings.append("Elevated ground tilt detected")

    if vibration >= 1.0:
        warnings.append("High ground vibration detected")
    elif vibration >= 0.5:
        warnings.append("Elevated ground vibration detected")

    if len(warnings) >= 3:
        condition = "Critical"
    elif len(warnings) == 2:
        condition = "Warning"
    elif len(warnings) == 1:
        condition = "Watch"
    else:
        condition = "Normal"

    return {
        "condition": condition,
        "warnings": warnings,
    }

def predict_risk(
    rainfall_mm: float,
    elevation_m: float,
    slope_deg: float,
    aspect_deg: float,
):
    aspect_rad = math.radians(aspect_deg)

    features = {
        "rainfall_mm": rainfall_mm,
        "elevation_m": elevation_m,
        "slope_deg": slope_deg,
        "aspect_sin": math.sin(aspect_rad),
        "aspect_cos": math.cos(aspect_rad),
    }

    X = np.array(
        [[features[name] for name in FEATURES]],
        dtype=float,
    )

    probability = float(
        model.predict_proba(X)[0][1]
    )

    risk_score = int(
        round(probability * 100)
    )

    risk_level = classify_risk(
        risk_score
    )

    return (
        probability,
        risk_score,
        risk_level,
        features,
    )

latest_sensor_data = {}

@app.post("/api/sensor-data")
def receive_sensor_data(data: SensorData):
    global latest_sensor_data

    sensor_analysis = analyze_sensor_condition(
        rainfall_mm=data.rainfall_mm,
        soil_moisture=data.soil_moisture,
        tilt_deg=data.tilt_deg,
        vibration=data.vibration,
    )

    latest_sensor_data = {
        "device_id": data.device_id,
        "latitude": data.latitude,
        "longitude": data.longitude,
        "rainfall_mm": data.rainfall_mm,
        "soil_moisture": data.soil_moisture,
        "tilt_deg": data.tilt_deg,
        "vibration": data.vibration,
        "sensor_condition": sensor_analysis["condition"],
        "warnings": sensor_analysis["warnings"],
    }

    return {
        "status": "received",
        "message": "Sensor data received successfully",
        "data": latest_sensor_data,
    }


@app.get("/api/sensor-data/latest")
def get_latest_sensor_data():
    if not latest_sensor_data:
        return {
            "status": "no_data",
            "message": "No sensor data received yet",
        }

    return {
        "status": "ok",
        "data": latest_sensor_data,
    }


def calculate_sensor_risk(sensor_data: dict) -> int:
    score = 0

    rainfall = sensor_data["rainfall_mm"]
    soil_moisture = sensor_data["soil_moisture"]
    tilt = abs(sensor_data["tilt_deg"])
    vibration = sensor_data["vibration"]

    if rainfall >= 100:
        score += 30
    elif rainfall >= 50:
        score += 15

    if soil_moisture >= 80:
        score += 30
    elif soil_moisture >= 65:
        score += 15

    if tilt >= 10:
        score += 25
    elif tilt >= 5:
        score += 15

    if vibration >= 1.0:
        score += 15
    elif vibration >= 0.5:
        score += 8

    return min(score, 100)

@app.get("/api/risk/current")
def get_current_risk():

    if not latest_sensor_data:
        return {
            "status": "no_data",
            "message": "No sensor data available",
        }

    # -------------------------------------------------
    # 1. Calculate sensor risk
    # -------------------------------------------------

    sensor_risk_score = calculate_sensor_risk(
        latest_sensor_data
    )

    sensor_condition = latest_sensor_data["sensor_condition"]

    if sensor_condition == "Critical":
        sensor_risk_level = "Critical"
    elif sensor_condition == "Warning":
        sensor_risk_level = "High"
    elif sensor_condition == "Watch":
        sensor_risk_level = "Moderate"
    else:
        sensor_risk_level = "Low"

    # -------------------------------------------------
    # 2. Calculate AI risk using XGBoost
    # -------------------------------------------------

    rainfall_mm = latest_sensor_data["rainfall_mm"]

    terrain = get_terrain(
    latest_sensor_data["latitude"],
    latest_sensor_data["longitude"],
    )

    elevation_m = terrain["elevation_m"]
    slope_deg = terrain["slope_deg"]
    aspect_deg = terrain["aspect_deg"]

    probability, ai_risk_score, ai_risk_level, features = predict_risk(
        rainfall_mm=rainfall_mm,
        elevation_m=elevation_m,
        slope_deg=slope_deg,
        aspect_deg=aspect_deg,
    )

    # -------------------------------------------------
    # 3. Combine AI risk + sensor risk
    # -------------------------------------------------

    overall_risk_score = int(
        round(
            (ai_risk_score * 0.70)
            + (sensor_risk_score * 0.30)
        )
    )

    overall_risk_score = min(
        overall_risk_score,
        100,
    )

    overall_risk_level = classify_risk(
        overall_risk_score
    )

    # -------------------------------------------------
    # 4. Return complete risk information
    # -------------------------------------------------

    return {
        "status": "ok",

        "location": {
            "latitude": latest_sensor_data["latitude"],
            "longitude": latest_sensor_data["longitude"],
        },

        "ai": {
            "probability": round(probability, 4),
            "risk_score": ai_risk_score,
            "risk_level": ai_risk_level,
            "features": features,
        },

        "sensor": {
            "risk_score": sensor_risk_score,
            "risk_level": sensor_risk_level,
            "condition": sensor_condition,
            "warnings": latest_sensor_data["warnings"],
        },

        "overall": {
            "risk_score": overall_risk_score,
            "risk_level": overall_risk_level,
        },

        "sensors": {
            "rainfall_mm": latest_sensor_data["rainfall_mm"],
            "soil_moisture": latest_sensor_data["soil_moisture"],
            "tilt_deg": latest_sensor_data["tilt_deg"],
            "vibration": latest_sensor_data["vibration"],
        },
    }

@app.get("/")
def root():
    return {
        "system": "Earth Sentinel",
        "status": "running",
        "ai": "XGBoost model loaded",
    }


@app.get("/api/health")
def health():
    return {
        "status": "healthy",
        "ai": "trained",
        "model": "XGBoost",
        "features": FEATURES,
    }


@app.post(
    "/api/predict",
    response_model=PredictionResponse,
)
def predict(request: PredictionRequest):

    probability, risk_score, risk_level, features = (
        predict_risk(
            rainfall_mm=request.rainfall_mm,
            elevation_m=request.elevation_m,
            slope_deg=request.slope_deg,
            aspect_deg=request.aspect_deg,
        )
    )

    return {
        "probability": round(probability, 4),
        "risk_score": risk_score,
        "risk_level": risk_level,
        "inputs": features,
    }