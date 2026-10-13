
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone

app = FastAPI(title="LM2596S PCB Fault Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class SensorReadings(BaseModel):
    vin: float
    vout: float
    current: float


latest_readings = {
    "vin": None,
    "vout": None,
    "current": None,
    "updated_at": None,
    "connected": False,
}


@app.get("/")
def home():
    return {"message": "LM2596S API is running"}


@app.post("/api/readings")
def receive_readings(data: SensorReadings):
    latest_readings.update({
        "vin": data.vin,
        "vout": data.vout,
        "current": data.current,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "connected": True,
    })
    return {"message": "Readings received successfully"}


@app.get("/api/readings")
def get_readings():
    data = latest_readings.copy()

    if data["updated_at"] is None:
        data["connected"] = False
    else:
        updated = datetime.fromisoformat(data["updated_at"])
        age = (datetime.now(timezone.utc) - updated).total_seconds()
        data["connected"] = age <= 5

    return data
