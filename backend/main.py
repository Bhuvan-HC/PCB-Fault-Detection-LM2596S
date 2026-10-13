from datetime import datetime, timezone
from pathlib import Path
import base64

import cv2
import numpy as np

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ultralytics import YOLO


# --------------------------------------------------
# APP CONFIGURATION
# --------------------------------------------------

app = FastAPI(title="LM2596S PCB Fault Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --------------------------------------------------
# YOLO MODEL
# --------------------------------------------------

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
    print(f"WARNING: YOLO model not found: {MODEL_PATH}")


# --------------------------------------------------
# ELECTRICAL SENSOR API - PRESERVED
# --------------------------------------------------

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
    return {
        "message": "LM2596S API is running",
        "yolo_loaded": model is not None,
    }


@app.post("/api/readings")
def receive_readings(data: SensorReadings):
    latest_readings.update({
        "vin": data.vin,
        "vout": data.vout,
        "current": data.current,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "connected": True,
    })

    return {
        "message": "Readings received successfully"
    }


@app.get("/api/readings")
def get_readings():
    data = latest_readings.copy()

    if data["updated_at"] is None:
        data["connected"] = False
    else:
        updated = datetime.fromisoformat(data["updated_at"])

        age = (
            datetime.now(timezone.utc) - updated
        ).total_seconds()

        data["connected"] = age <= 5

    return data


# --------------------------------------------------
# YOLO PCB IMAGE DETECTION API
# --------------------------------------------------

@app.post("/api/process-image")
async def process_image(file: UploadFile = File(...)):

    if model is None:
        raise HTTPException(
            status_code=503,
            detail="YOLO model not found. Check the best.pt path."
        )

    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Upload a JPG, PNG, or WebP image."
        )

    image_bytes = await file.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded image is empty."
        )

    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image size must be less than 10 MB."
        )

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8
    )

    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if image is None:
        raise HTTPException(
            status_code=400,
            detail="Unable to read the uploaded image."
        )

    try:
        # Run YOLO
        results = model.predict(
            source=image,
            conf=0.15,
            verbose=False,
        )

        result = results[0]

        detections = []

        for box in result.boxes:

            class_id = int(box.cls[0].item())

            confidence = float(
                box.conf[0].item()
            )

            coordinates = [
                round(float(value), 2)
                for value in box.xyxy[0].tolist()
            ]

            detections.append({
                "class_id": class_id,
                "class_name": model.names[class_id],
                "confidence": round(confidence, 4),
                "box": coordinates,
            })

        # Create the annotated image
        annotated_image = result.plot()

        success, encoded_image = cv2.imencode(
            ".jpg",
            annotated_image
        )

        if not success:
            raise RuntimeError(
                "Could not encode the processed image."
            )

        image_base64 = base64.b64encode(
            encoded_image.tobytes()
        ).decode("utf-8")

        return {
            "success": True,
            "message": "YOLO detection completed.",
            "filename": file.filename,
            "detected": len(detections) > 0,
            "detections": detections,
            "image": (
                "data:image/jpeg;base64,"
                + image_base64
            ),
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"YOLO detection failed: {str(error)}"
        )