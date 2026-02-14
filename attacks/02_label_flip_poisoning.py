"""
Label-Flip Data Poisoning Attack

Copies the balanced dataset and flips a percentage of training labels
(moves images between receipt/non_receipt folders) to degrade model accuracy.

Usage:
    python 02_label_flip_poisoning.py
    python 02_label_flip_poisoning.py --flip-rate 0.10
"""
import os
import shutil
import random
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
CLASSES = ["receipt", "non_receipt"]
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results", "02_label_flip")


def poison_dataset(source_root, target_root, flip_ratio=0.05, seed=42):
    """
    Copy dataset and flip a percentage of training labels.

    Label flipping works by moving images between class folders:
    - A receipt image moved to non_receipt/ gets a flipped label
    - A non_receipt image moved to receipt/ gets a flipped label

    Only training labels are flipped — the test set stays clean so we can
    measure the true impact of poisoning on model performance.

    Args:
        source_root: Path to clean balanced dataset
        target_root: Path for poisoned dataset output
        flip_ratio: Fraction of training labels to flip (default 0.05 = 5%)
        seed: Random seed for reproducibility
    """
    random.seed(seed)

    # Step 1: Copy the entire clean dataset to target
    if os.path.exists(target_root):
        shutil.rmtree(target_root)
    shutil.copytree(source_root, target_root)

    total_train = 0
    total_flipped = 0

    for cls in CLASSES:
        cls_dir = os.path.join(target_root, "train", cls)
        opposite_cls = "non_receipt" if cls == "receipt" else "receipt"
        opposite_dir = os.path.join(target_root, "train", opposite_cls)

        files = [
            f for f in sorted(os.listdir(cls_dir))
            if os.path.isfile(os.path.join(cls_dir, f))
            and os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
        ]
        total_train += len(files)
        n_flip = int(len(files) * flip_ratio)
        flipped_files = random.sample(files, n_flip)

        for fname in flipped_files:
            src_path = os.path.join(cls_dir, fname)
            dst_name = f"flipped_{cls}_{fname}"
            dst_path = os.path.join(opposite_dir, dst_name)
            shutil.move(src_path, dst_path)
            total_flipped += 1

    actual_flip_rate = total_flipped / total_train if total_train > 0 else 0
    print("=" * 50)
    print("Label Flipping Summary:")
    print(f"Total training images: {total_train}")
    print(f"Number flipped: {total_flipped}")
    print(f"Actual flip rate: {actual_flip_rate:.4f} ({actual_flip_rate * 100:.2f}%)")
    print("-" * 50)
    for split in ["train", "test"]:
        for cls in CLASSES:
            split_dir = os.path.join(target_root, split, cls)
            count = len([
                f for f in os.listdir(split_dir)
                if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS
            ])
            print(f"{split}/{cls}: {count} images")
    print("=" * 50)


def visualize_flip(source_root, target_root, num_images=5, output_dir=RESULTS_DIR, seed=42):
    """Save a grid showing clean labels beside their flipped poisoned labels."""
    flipped_samples = []

    for poisoned_label in CLASSES:
        poisoned_dir = os.path.join(target_root, "train", poisoned_label)
        if not os.path.isdir(poisoned_dir):
            continue

        for filename in os.listdir(poisoned_dir):
            poisoned_path = os.path.join(poisoned_dir, filename)
            if (
                not os.path.isfile(poisoned_path)
                or os.path.splitext(filename)[1].lower() not in IMAGE_EXTENSIONS
            ):
                continue

            original_label = None
            original_filename = None
            for cls in CLASSES:
                prefix = f"flipped_{cls}_"
                if filename.startswith(prefix):
                    original_label = cls
                    original_filename = filename[len(prefix):]
                    break

            if original_label is None:
                continue

            clean_path = os.path.join(
                source_root,
                "train",
                original_label,
                original_filename,
            )
            if os.path.exists(clean_path):
                flipped_samples.append({
                    "clean_path": clean_path,
                    "poisoned_path": poisoned_path,
                    "original_label": original_label,
                    "poisoned_label": poisoned_label,
                    "filename": original_filename,
                })

    if not flipped_samples:
        print("No flipped images found to visualize.")
        return None

    rng = random.Random(seed)
    sample_count = min(num_images, len(flipped_samples))
    samples = rng.sample(flipped_samples, sample_count)

    fig, axes = plt.subplots(sample_count, 2, figsize=(8, 3 * sample_count))
    if sample_count == 1:
        axes = [axes]

    for row, sample in enumerate(samples):
        clean_img = plt.imread(sample["clean_path"])
        poisoned_img = plt.imread(sample["poisoned_path"])

        axes[row][0].imshow(clean_img)
        axes[row][0].set_title(
            f"Clean: {sample['original_label']}\n{sample['filename']}",
            fontsize=9,
        )
        axes[row][0].axis("off")

        axes[row][1].imshow(poisoned_img)
        axes[row][1].set_title(
            f"Flipped label: {sample['poisoned_label']}\n"
            f"from {sample['original_label']}",
            fontsize=9,
        )
        axes[row][1].axis("off")

    fig.suptitle(
        f"Label Flip Poisoning Samples ({sample_count} images)",
        fontsize=12,
    )
    fig.tight_layout()

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"label_flip_results_{sample_count}.png")
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    print(f"Label flip visualization saved to: {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Label-Flip Poisoning Attack")
    parser.add_argument(
        "--source",
        default=os.path.join(os.path.dirname(__file__),
                             "..", "classifier", "balanced_data"),
    )
    parser.add_argument(
        "--target",
        default=os.path.join(os.path.dirname(__file__),
                             "..", "classifier", "poisoned_data"),
    )
    parser.add_argument("--flip-rate", type=float, default=0.05)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--visualize-count", type=int, default=5)
    parser.add_argument("--results-dir", default=RESULTS_DIR)
    args = parser.parse_args()

    poison_dataset(args.source, args.target, args.flip_rate, args.seed)
    visualize_flip(
        args.source,
        args.target,
        num_images=args.visualize_count,
        output_dir=args.results_dir,
        seed=args.seed,
    )
