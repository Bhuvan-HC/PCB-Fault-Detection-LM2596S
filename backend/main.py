
from datetime import datetime, timezone
from pathlib import Path
import base64
import logging

import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from ultralytics import YOLO


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="LM2596S PCB Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "image_processing" / "weights" / "best.pt"

MAX_IMAGE_BYTES = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

# Lower confidence helps reveal weak detections, but may add false positives.
CONFIDENCE_THRESHOLD = 0.05
IMAGE_SIZE = 640
IOU_THRESHOLD = 0.5
MAX_DETECTIONS = 300

model = None

try:
    if MODEL_PATH.is_file():
        model = YOLO(str(MODEL_PATH))
        logger.info("YOLO model loaded: %s", MODEL_PATH)
        logger.info("YOLO classes: %s", model.names)
    else:
        logger.error("YOLO weights not found: %s", MODEL_PATH)
except Exception:
    logger.exception("Failed to load YOLO model")


# --------------------------------------------------
# ELECTRICAL SENSOR API
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
        "model_path": str(MODEL_PATH),
        "classes": model.names if model is not None else {},
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
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

    return {"message": "Readings received successfully"}


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
# YOLO PCB IMAGE DETECTION
# --------------------------------------------------

@app.post("/api/process-image")
async def process_image(file: UploadFile = File(...)):
    if model is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "YOLO model could not be loaded. "
                "Check backend/image_processing/weights/best.pt "
                "and the backend startup logs."
            ),
        )

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Upload a JPG, PNG, or WebP image.",
        )

    try:
        image_bytes = await file.read()

        if not image_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded image is empty.",
            )

        if len(image_bytes) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Image size must be less than 10 MB.",
            )

        image_array = np.frombuffer(
            image_bytes,
            dtype=np.uint8,
        )

        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise HTTPException(
                status_code=400,
                detail="Unable to decode the uploaded image.",
            )

        height, width = image.shape[:2]

        logger.info(
            "Processing image %s (%s x %s)",
            file.filename,
            width,
            height,
        )

        # Run the trained model.
        results = model.predict(
            source=image,
            conf=CONFIDENCE_THRESHOLD,
            imgsz=IMAGE_SIZE,
            iou=IOU_THRESHOLD,
            max_det=MAX_DETECTIONS,
            verbose=False,
        )

        result = results[0]
        detections = []

        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                confidence = float(box.conf[0].item())

                coordinates = [
                    round(float(value), 2)
                    for value in box.xyxy[0].tolist()
                ]

                if isinstance(model.names, dict):
                    class_name = model.names.get(
                        class_id,
                        f"class_{class_id}",
                    )
                else:
                    class_name = model.names[class_id]

                detections.append({
                    "class_id": class_id,
                    "class_name": str(class_name),
                    "confidence": round(confidence, 4),
                    "confidence_percent": round(
                        confidence * 100, 2
                    ),
                    "box": coordinates,
                })

        # Draw the detections onto the uploaded image.
        annotated_image = result.plot()

        success, encoded_image = cv2.imencode(
            ".jpg",
            annotated_image,
            [cv2.IMWRITE_JPEG_QUALITY, 90],
        )

        if not success:
            raise RuntimeError("Failed to encode the result image.")

        image_base64 = base64.b64encode(
            encoded_image.tobytes()
        ).decode("utf-8")

        logger.info(
            "Detection completed: %s object(s)",
            len(detections),
        )

        return {
            "success": True,
            "message": (
                "Detection completed."
                if detections
                else (
                    "No objects detected at the current "
                    "confidence threshold. This does not prove "
                    "that the PCB is fault-free."
                )
            ),
            "filename": file.filename,
            "image_width": width,
            "image_height": height,
            "confidence_threshold": CONFIDENCE_THRESHOLD,
            "detected": len(detections) > 0,
            "count": len(detections),
            "detections": detections,
            "image": "data:image/jpeg;base64," + image_base64,
        }

    except HTTPException:
        raise
    except Exception as error:
        logger.exception("YOLO inference failed")
        raise HTTPException(
            status_code=500,
            detail=f"YOLO detection failed: {str(error)}",
        ) from error
    finally:
        await file.close()
