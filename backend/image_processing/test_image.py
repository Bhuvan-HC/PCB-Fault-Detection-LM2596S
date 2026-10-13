import cv2
from pathlib import Path
from detector import process_pcb_image

BASE_DIR = Path(__file__).resolve().parent

IMAGE_PATH = BASE_DIR / "uploads" / "lm2596_test.jpeg"
OUTPUT_PATH = BASE_DIR / "uploads" / "processed_image.jpeg"
EDGES_PATH = BASE_DIR / "uploads" / "edges.jpeg"


def main():
    try:
        processed_image, edges, contour_count = process_pcb_image(
            IMAGE_PATH
        )

        cv2.imwrite(str(OUTPUT_PATH), processed_image)
        cv2.imwrite(str(EDGES_PATH), edges)

        print("Image processing completed successfully.")
        print(f"Detected contours: {contour_count}")
        print(f"Processed image: {OUTPUT_PATH}")
        print(f"Edge image: {EDGES_PATH}")

    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}")


if __name__ == "__main__":
    main()