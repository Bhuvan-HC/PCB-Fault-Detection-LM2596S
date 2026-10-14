
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
import base64
import math

import cv2
import numpy as np
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ultralytics import YOLO

app = FastAPI(title="PCB Fault Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- YOLO MODEL ----------------
MODEL_PATH = (
    Path(__file__).parent
    / "image_processing"
    / "weights"
    / "best.pt"
)

model = None

if MODEL_PATH.exists():
    model = YOLO(str(MODEL_PATH))
    print(f"YOLO model loaded: {MODEL_PATH}")
else:
    print(f"YOLO weights not found: {MODEL_PATH}")

# ---------------- SENSOR DATA ----------------
data_lock = Lock()

latest_readings = {
    "vin": None,
    "vout": None,
    "current": None,
    "temperature": None,
    "updated_at": None,
    "connected": False,
}


class SensorReadings(BaseModel):
    vin: float
    vout: float
    current: float
    temperature: float | None = None


@app.get("/")
def home():
    return {"message": "PCB Fault Detection API is running"}


@app.post("/api/readings")
def receive_readings(readings: SensorReadings):
    values = {
        "vin": readings.vin,
        "vout": readings.vout,
        "current": readings.current,
        "temperature": readings.temperature,
    }

    for name, value in values.items():
        if value is not None and not math.isfinite(value):
            raise HTTPException(
                status_code=422,
                detail=f"Invalid sensor value: {name}",
            )

    with data_lock:
        latest_readings.update(values)
        latest_readings["updated_at"] = (
            datetime.now(timezone.utc).isoformat()
        )
        latest_readings["connected"] = True

    return {"success": True}


@app.get("/api/readings")
def get_readings():
    with data_lock:
        result = latest_readings.copy()

    updated_at = result["updated_at"]

    if updated_at:
        last_update = datetime.fromisoformat(updated_at)
        age = (
            datetime.now(timezone.utc) - last_update
        ).total_seconds()

        result["connected"] = age <= 6
    else:
        result["connected"] = False

    return result


# ---------------- YOLO IMAGE DETECTION ----------------
@app.post("/api/process-image")
async def process_image(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "YOLO model is unavailable. "
                "Check backend/image_processing/weights/best.pt"
            ),
        )

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Upload a JPG, PNG, or WEBP image.",
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty.",
        )

    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Maximum image size is 10 MB.",
        )

    image_array = np.frombuffer(contents, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise HTTPException(
            status_code=400,
            detail="Could not decode the uploaded image.",
        )

    try:
        results = model.predict(
            source=image,
            conf=0.15,
            verbose=False,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"YOLO prediction failed: {exc}",
        ) from exc

    result = results[0]
    detections = []

    if result.boxes is not None:
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            x1, y1, x2, y2 = [
                int(value)
                for value in box.xyxy[0].tolist()
            ]

            names = result.names
            class_name = (
                names.get(class_id, str(class_id))
                if isinstance(names, dict)
                else names[class_id]
            )

            detections.append({
                "class_id": class_id,
                "class_name": class_name,
                "confidence": round(confidence, 4),
                "box": {
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                },
            })

    annotated = result.plot()
    success, encoded = cv2.imencode(".jpg", annotated)

    if not success:
        raise HTTPException(
            status_code=500,
            detail="Could not encode the annotated image.",
        )

    image_base64 = base64.b64encode(
        encoded.tobytes()
    ).decode("utf-8")

    return {
        "success": True,
        "detections": detections,
        "image": f"data:image/jpeg;base64,{image_base64}",
    }
