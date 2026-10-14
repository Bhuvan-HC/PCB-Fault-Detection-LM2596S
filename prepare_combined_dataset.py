
from pathlib import Path
import math
import shutil
import sys

# ============================================================
# Configuration
# ============================================================

ROOT = Path("backend/image_processing")
SOURCE = ROOT / "dataset"
OUTPUT = ROOT / "dataset_combined"

SPLITS = ("train", "val")

FAULT_CLASSES = [
    "burnt_capacitor",      # 0
    "missing_capacitor",    # 1
    "broken_component",    # 2
    "broken_track",        # 3
    "darker_area",         # 4
    "hole_in_track",       # 5
    "broken_wire",         # 6
]

COMPONENT_CLASSES = [
    "Cap1",         # 7
    "Cap2",         # 8
    "Cap3",         # 9
    "Cap4",         # 10
    "MOSFET",       # 11
    "Mov",          # 12
    "Resestor",     # 13
    "Resistor",     # 14
    "Transformer",  # 15
]

CLASS_NAMES = FAULT_CLASSES + COMPONENT_CLASSES
COMPONENT_ID_OFFSET = len(FAULT_CLASSES)

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"
}

# Class IDs are based on the fault described by each filename.
# A listed file may exist in train OR val, not necessarily both.
FAULT_FILE_IDS = {
    "back_01_hole_in_track.txt": 5,
    "back_02_broken_track.txt": 3,
    "back_03_broken_wire.txt": 6,
    "back_04_darker_area.txt": 4,
    "back_05_broken_component.txt": 2,
    "front_01_burnt_capacitor.txt": 0,
    "front_02_missing_capacitor.txt": 1,
    "front_03_broken_component.txt": 2,
    "front_04_broken_track.txt": 3,
    "front_05_darker_area.txt": 4,
}


# ============================================================
# Label validation and clipping
# ============================================================

def read_and_validate_label(label_path, allowed_ids):
    """
    Read YOLO labels, validate values, and clip bounding boxes
    to [0, 1] normalized image boundaries.

    Only output labels are changed. Source labels remain untouched.
    Returns (rows, number_of_clipped_boxes).
    """
    rows = []
    clipped_count = 0

    for line_number, line in enumerate(
        label_path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue

        parts = line.split()

        if len(parts) != 5:
            raise ValueError(
                f"{label_path}:{line_number}: expected 5 values, "
                f"got {len(parts)}"
            )

        try:
            class_value = float(parts[0])
            x, y, w, h = map(float, parts[1:])
        except ValueError as exc:
            raise ValueError(
                f"{label_path}:{line_number}: invalid numeric value"
            ) from exc

        if not math.isfinite(class_value) or not class_value.is_integer():
            raise ValueError(
                f"{label_path}:{line_number}: class ID must be an integer"
            )

        class_id = int(class_value)

        if class_id not in allowed_ids:
            raise ValueError(
                f"{label_path}:{line_number}: invalid class ID {class_id}; "
                f"allowed IDs: {sorted(allowed_ids)}"
            )

        if not all(math.isfinite(v) for v in (x, y, w, h)):
            raise ValueError(
                f"{label_path}:{line_number}: coordinates must be finite"
            )

        if w <= 0 or h <= 0:
            raise ValueError(
                f"{label_path}:{line_number}: width and height must be positive"
            )

        # Convert center/size format into box edges.
        left = x - w / 2
        right = x + w / 2
        top = y - h / 2
        bottom = y + h / 2

        # Clip edges to the normalized image boundary.
        new_left = max(0.0, left)
        new_right = min(1.0, right)
        new_top = max(0.0, top)
        new_bottom = min(1.0, bottom)

        if new_right <= new_left or new_bottom <= new_top:
            raise ValueError(
                f"{label_path}:{line_number}: box has no area inside image"
            )

        if (
            new_left != left
            or new_right != right
            or new_top != top
            or new_bottom != bottom
        ):
            clipped_count += 1

        # Convert the clipped edges back to YOLO center/size format.
        new_x = (new_left + new_right) / 2
        new_y = (new_top + new_bottom) / 2
        new_w = new_right - new_left
        new_h = new_bottom - new_top

        rows.append(
            f"{class_id} {new_x:.8f} {new_y:.8f} "
            f"{new_w:.8f} {new_h:.8f}"
        )

    return rows, clipped_count


# ============================================================
# Image lookup
# ============================================================

def find_image(image_dir, stem):
    """Find an image matching a label filename stem."""
    matches = [
        path
        for path in image_dir.glob(stem + ".*")
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
    ]

    if len(matches) > 1:
        raise ValueError(
            f"Multiple images match '{stem}' in '{image_dir}': "
            + ", ".join(p.name for p in matches)
        )

    return matches[0] if matches else None


# ============================================================
# Process one split
# ============================================================

def prepare_split(split):
    source_images = SOURCE / "images" / split
    source_labels = SOURCE / "labels" / split
    output_images = OUTPUT / "images" / split
    output_labels = OUTPUT / "labels" / split

    if not source_images.is_dir():
        raise FileNotFoundError(f"Missing image directory: {source_images}")

    if not source_labels.is_dir():
        raise FileNotFoundError(f"Missing label directory: {source_labels}")

    output_images.mkdir(parents=True, exist_ok=True)
    output_labels.mkdir(parents=True, exist_ok=True)

    copied_images = 0
    clipped_total = 0
    processed_fault_files = set()
    labeled_stems = set()

    label_files = sorted(source_labels.glob("*.txt"))

    for label_path in label_files:
        filename = label_path.name
        stem = label_path.stem

        image_path = find_image(source_images, stem)

        if image_path is None:
            raise FileNotFoundError(
                f"No matching image for label '{label_path}'"
            )

        # Fault labels: map their class IDs from the filename.
        if filename in FAULT_FILE_IDS:
            target_id = FAULT_FILE_IDS[filename]
            target_name = FAULT_CLASSES[target_id]

            print(
                f"Remapping {split}/{filename} to "
                f"class {target_id} ({target_name})"
            )

            rows, clipped = read_and_validate_label(
                label_path, set(range(len(FAULT_CLASSES)))
            )

            # All boxes in this single-fault image receive the
            # class indicated by the filename.
            rows = [
                f"{target_id} " + " ".join(row.split()[1:])
                for row in rows
            ]

            processed_fault_files.add(filename)

        # Component dataset labels have IDs 0 through 8.
        elif stem.startswith("VID"):
            rows, clipped = read_and_validate_label(
                label_path, set(range(len(COMPONENT_CLASSES)))
            )

            shifted_rows = []

            for row in rows:
                parts = row.split()
                old_id = int(parts[0])
                parts[0] = str(old_id + COMPONENT_ID_OFFSET)
                shifted_rows.append(" ".join(parts))

            rows = shifted_rows

        else:
            raise ValueError(
                f"Unexpected label file in split '{split}': {filename}\n"
                "Review this file and add its explicit mapping if it is "
                "a fault label."
            )

        output_image = output_images / image_path.name
        output_label = output_labels / f"{stem}.txt"

        shutil.copy2(image_path, output_image)
        output_label.write_text(
            "\n".join(rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )

        copied_images += 1
        clipped_total += clipped
        labeled_stems.add(stem)

    # Unlabeled images are skipped until confirmed to be valid negatives.
    unlabeled_count = 0

    for image_path in source_images.iterdir():
        if (
            image_path.is_file()
            and image_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
            and image_path.stem not in labeled_stems
        ):
            unlabeled_count += 1

    print(f"\n{split.upper()} summary")
    print(f"  Images copied: {copied_images}")
    print(f"  Label files written: {copied_images}")
    print(f"  Bounding boxes clipped: {clipped_total}")
    print(f"  Unlabeled images skipped: {unlabeled_count}")
    print(
        "  Fault files found: "
        + str(len(processed_fault_files))
    )

    return copied_images, processed_fault_files


# ============================================================
# Create data.yaml
# ============================================================

def write_data_yaml():
    absolute_path = OUTPUT.resolve().as_posix()

    lines = [
        f"path: {absolute_path}",
        "train: images/train",
        "val: images/val",
        "",
        f"nc: {len(CLASS_NAMES)}",
        "names:",
    ]

    for class_id, name in enumerate(CLASS_NAMES):
        lines.append(f"  {class_id}: {name}")

    yaml_path = OUTPUT / "data.yaml"
    yaml_path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print(f"\nCreated YAML: {yaml_path}")
    print(f"Number of classes: {len(CLASS_NAMES)}")


# ============================================================
# Main
# ============================================================

def main():
    if not SOURCE.is_dir():
        raise FileNotFoundError(
            f"Source dataset does not exist: {SOURCE.resolve()}"
        )

    if OUTPUT.exists():
        raise FileExistsError(
            f"Output directory already exists: {OUTPUT.resolve()}\n"
            "If this is only the partial output from a failed run and you "
            "do not need it, remove that directory and rerun the script."
        )

    for split in SPLITS:
        if not (SOURCE / "images" / split).is_dir():
            raise FileNotFoundError(
                f"Missing directory: {SOURCE / 'images' / split}"
            )

        if not (SOURCE / "labels" / split).is_dir():
            raise FileNotFoundError(
                f"Missing directory: {SOURCE / 'labels' / split}"
            )

    # Check that every expected fault label appears in at least one split.
    found_fault_files = set()

    for split in SPLITS:
        label_dir = SOURCE / "labels" / split

        for filename in FAULT_FILE_IDS:
            if (label_dir / filename).is_file():
                found_fault_files.add(filename)

    missing_fault_files = set(FAULT_FILE_IDS) - found_fault_files

    if missing_fault_files:
        raise FileNotFoundError(
            "Expected fault label files were not found in train or val: "
            + ", ".join(sorted(missing_fault_files))
        )

    # Create output only after the initial checks have passed.
    OUTPUT.mkdir(parents=True, exist_ok=False)

    try:
        total_images = 0
        all_processed_fault_files = set()

        for split in SPLITS:
            image_count, fault_files = prepare_split(split)
            total_images += image_count
            all_processed_fault_files.update(fault_files)

        if total_images == 0:
            raise RuntimeError("No labeled images were copied.")

        missing_after_processing = (
            set(FAULT_FILE_IDS) - all_processed_fault_files
        )

        if missing_after_processing:
            raise RuntimeError(
                "These fault labels were not processed: "
                + ", ".join(sorted(missing_after_processing))
            )

        write_data_yaml()

        print("\n" + "=" * 55)
        print("DATASET PREPARATION COMPLETED SUCCESSFULLY")
        print("=" * 55)
        print(f"Output directory: {OUTPUT.resolve()}")
        print(f"Total images copied: {total_images}")
        print(f"Fault label files processed: {len(all_processed_fault_files)}")
        print(f"Classes configured: {len(CLASS_NAMES)}")
        print("Original dataset was not modified.")

    except Exception:
        print(
            "\nPreparation failed. The original dataset was not modified.",
            file=sys.stderr,
        )
        print(
            f"Partial output may remain at: {OUTPUT.resolve()}",
            file=sys.stderr,
        )
        raise


if __name__ == "__main__":
    main()
