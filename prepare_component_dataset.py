from pathlib import Path
import math
import shutil

ROOT = Path("backend/image_processing")
SOURCE = ROOT / "dataset"
OUTPUT = ROOT / "dataset_components"

CLASS_NAMES = [
    "Cap1", "Cap2", "Cap3", "Cap4", "MOSFET",
    "Mov", "Resestor", "Resistor", "Transformer",
]

IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"
}


def main():
    if not SOURCE.is_dir():
        raise FileNotFoundError(f"Dataset not found: {SOURCE.resolve()}")

    if OUTPUT.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT.resolve()}. "
            "Inspect it before removing it."
        )

    for split in ("train", "val"):
        for kind in ("images", "labels"):
            folder = SOURCE / kind / split
            if not folder.is_dir():
                raise FileNotFoundError(f"Missing directory: {folder}")

    OUTPUT.mkdir(parents=True)

    try:
        for split in ("train", "val"):
            src_images = SOURCE / "images" / split
            src_labels = SOURCE / "labels" / split
            dst_images = OUTPUT / "images" / split
            dst_labels = OUTPUT / "labels" / split

            dst_images.mkdir(parents=True)
            dst_labels.mkdir(parents=True)

            copied = 0
            clipped_count = 0

            for label_path in sorted(src_labels.glob("*.txt")):
                # Only VID-prefixed files belong to the component dataset.
                if not label_path.stem.startswith("VID"):
                    continue

                matches = [
                    p for p in src_images.glob(label_path.stem + ".*")
                    if p.is_file()
                    and p.suffix.lower() in IMAGE_EXTENSIONS
                ]

                if len(matches) != 1:
                    raise ValueError(
                        f"{label_path}: expected one matching image, "
                        f"found {len(matches)}"
                    )

                output_rows = []

                for line_no, line in enumerate(
                    label_path.read_text(encoding="utf-8").splitlines(), 1
                ):
                    if not line.strip():
                        continue

                    parts = line.split()
                    if len(parts) != 5:
                        raise ValueError(
                            f"{label_path}:{line_no}: expected 5 values"
                        )

                    try:
                        class_value = float(parts[0])
                        x, y, w, h = map(float, parts[1:])
                    except ValueError as exc:
                        raise ValueError(
                            f"{label_path}:{line_no}: invalid numeric value"
                        ) from exc

                    if (
                        not math.isfinite(class_value)
                        or not class_value.is_integer()
                    ):
                        raise ValueError(
                            f"{label_path}:{line_no}: invalid class ID"
                        )

                    class_id = int(class_value)
                    if not 0 <= class_id < len(CLASS_NAMES):
                        raise ValueError(
                            f"{label_path}:{line_no}: class ID {class_id} "
                            "is outside 0-8"
                        )

                    if not all(math.isfinite(v) for v in (x, y, w, h)):
                        raise ValueError(
                            f"{label_path}:{line_no}: non-finite coordinates"
                        )

                    if w <= 0 or h <= 0:
                        raise ValueError(
                            f"{label_path}:{line_no}: width/height must be positive"
                        )

                    left = x - w / 2
                    right = x + w / 2
                    top = y - h / 2
                    bottom = y + h / 2

                    new_left = max(0.0, left)
                    new_right = min(1.0, right)
                    new_top = max(0.0, top)
                    new_bottom = min(1.0, bottom)

                    if new_right <= new_left or new_bottom <= new_top:
                        raise ValueError(
                            f"{label_path}:{line_no}: box has no area "
                            "inside image"
                        )

                    if (
                        new_left != left or new_right != right
                        or new_top != top or new_bottom != bottom
                    ):
                        clipped_count += 1

                    new_x = (new_left + new_right) / 2
                    new_y = (new_top + new_bottom) / 2
                    new_w = new_right - new_left
                    new_h = new_bottom - new_top

                    output_rows.append(
                        f"{class_id} {new_x:.8f} {new_y:.8f} "
                        f"{new_w:.8f} {new_h:.8f}"
                    )

                image_path = matches[0]
                shutil.copy2(image_path, dst_images / image_path.name)

                (dst_labels / label_path.name).write_text(
                    "\n".join(output_rows)
                    + ("\n" if output_rows else ""),
                    encoding="utf-8",
                )

                copied += 1

            print(
                f"{split.upper()}: copied {copied} component images; "
                f"clipped boxes: {clipped_count}"
            )

        yaml_lines = [
            f"path: {OUTPUT.resolve().as_posix()}",
            "train: images/train",
            "val: images/val",
            "",
            f"nc: {len(CLASS_NAMES)}",
            "names:",
        ]

        yaml_lines.extend(
            f"  {i}: {name}" for i, name in enumerate(CLASS_NAMES)
        )

        (OUTPUT / "data.yaml").write_text(
            "\n".join(yaml_lines) + "\n",
            encoding="utf-8",
        )

        print("\nComponent dataset prepared successfully.")
        print(f"Output: {OUTPUT.resolve()}")
        print(f"Classes: {len(CLASS_NAMES)}")
        print("Original dataset was not modified.")

    except Exception:
        print(
            "\nPreparation failed. Partial output may remain at:",
            OUTPUT.resolve(),
        )
        raise


if __name__ == "__main__":
    main()
