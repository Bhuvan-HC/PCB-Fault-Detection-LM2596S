import cv2
from pathlib import Path


def process_pcb_image(image_path):
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError("Unable to read the image.")

    height, width = image.shape[:2]

    max_dimension = 1200

    if max(height, width) > max_dimension:
        scale = max_dimension / max(height, width)

        image = cv2.resize(
            image,
            (int(width * scale), int(height * scale))
        )

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    blurred = cv2.GaussianBlur(
        gray,
        (5, 5),
        0
    )

    edges = cv2.Canny(
        blurred,
        50,
        150
    )

    contours, _ = cv2.findContours(
        edges,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    output = image.copy()

    cv2.drawContours(
        output,
        contours,
        -1,
        (0, 255, 0),
        2
    )

    return output, edges, len(contours)