from pathlib import Path
from pyexpat import features

import numpy as np
from PIL import Image
import time
from backend.app.services.steganalysis_ml_service import (
    predict_steganography,
)

def extract_statistical_features(image_path: str) -> dict:
    """
    Extract basic statistical and LSB-related features
    from an RGB image.
    """

    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = Image.open(path).convert("RGB")

    image_array = np.asarray(
        image,
        dtype=np.uint8,
    )

    features = {}

    # Basic image information
    features["width"] = image.width
    features["height"] = image.height
    features["channels"] = 3

    channel_names = ["r", "g", "b"]

    # Channel statistics
    for index, channel_name in enumerate(channel_names):
        channel = image_array[:, :, index]

        features[f"{channel_name}_mean"] = float(
            np.mean(channel)
        )

        features[f"{channel_name}_std"] = float(
            np.std(channel)
        )

        features[f"{channel_name}_min"] = int(
            np.min(channel)
        )

        features[f"{channel_name}_max"] = int(
            np.max(channel)
        )

        # LSB ratio
        lsb = channel & 1

        features[f"{channel_name}_lsb_ones_ratio"] = float(
            np.mean(lsb)
        )

    # Global statistics
    features["global_mean"] = float(
        np.mean(image_array)
    )

    features["global_std"] = float(
        np.std(image_array)
    )

    # Overall LSB ratio
    all_lsb = image_array & 1

    features["global_lsb_ones_ratio"] = float(
        np.mean(all_lsb)
    )

    transition_features = calculate_lsb_transition_rate(
        image_path
    )

    features.update(transition_features)

    pair_features = calculate_lsb_pair_frequency(image_path)
    features.update(pair_features)

    rs_features = calculate_rs_analysis(image_path)
    features.update(rs_features)

    sequential_lsb_features = calculate_sequential_lsb_statistics(image_path)
    features.update(sequential_lsb_features)

    return features

def calculate_lsb_transition_rate(image_path: str) -> dict:
    """
    Calculate how frequently adjacent LSB values change
    within each RGB channel.
    """

    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = Image.open(path).convert("RGB")
    image_array = np.asarray(
        image,
        dtype=np.uint8,
    )

    features = {}

    channel_names = ["r", "g", "b"]

    for index, channel_name in enumerate(channel_names):
        channel = image_array[:, :, index]

        lsb = channel & 1

        horizontal_changes = np.mean(
            lsb[:, 1:] != lsb[:, :-1]
        )

        vertical_changes = np.mean(
            lsb[1:, :] != lsb[:-1, :]
        )

        features[
            f"{channel_name}_lsb_horizontal_transition_rate"
        ] = float(horizontal_changes)

        features[
            f"{channel_name}_lsb_vertical_transition_rate"
        ] = float(vertical_changes)

    return features

def calculate_lsb_pair_frequency(image_path: str) -> dict:
    """
    Calculate pair-frequency statistics for LSB steganalysis.

    For each RGB channel, counts how often adjacent pixel values
    form pairs where the values differ by 1. LSB replacement can
    disturb these pair relationships.
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = np.asarray(Image.open(image_path).convert("RGB"), dtype=np.uint8)

    features = {}

    for channel_index, channel_name in enumerate(("r", "g", "b")):
        channel = image[:, :, channel_index]

        # Horizontal adjacent pixel pairs
        left = channel[:, :-1].astype(np.int16)
        right = channel[:, 1:].astype(np.int16)

        horizontal_diff_one = np.abs(left - right) == 1
        horizontal_pair_rate = float(np.mean(horizontal_diff_one))

        # Vertical adjacent pixel pairs
        top = channel[:-1, :].astype(np.int16)
        bottom = channel[1:, :].astype(np.int16)

        vertical_diff_one = np.abs(top - bottom) == 1
        vertical_pair_rate = float(np.mean(vertical_diff_one))

        features[f"{channel_name}_horizontal_pair_rate"] = horizontal_pair_rate
        features[f"{channel_name}_vertical_pair_rate"] = vertical_pair_rate

    return features

def calculate_block_lsb_statistics(image_path: str, block_size: int = 64) -> dict:
    """
    Calculate local LSB statistics for image blocks.

    The image is divided into blocks and the LSB-one ratio
    is calculated for each RGB channel. The mean and standard
    deviation of these block ratios are returned.
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = np.asarray(
        Image.open(image_path).convert("RGB"),
        dtype=np.uint8,
    )

    height, width, _ = image.shape

    features = {}

    for channel_index, channel_name in enumerate(("r", "g", "b")):
        channel = image[:, :, channel_index]

        block_ratios = []

        for y in range(0, height, block_size):
            for x in range(0, width, block_size):
                block = channel[
                    y:min(y + block_size, height),
                    x:min(x + block_size, width),
                ]

                lsb_ratio = float(np.mean(block & 1))
                block_ratios.append(lsb_ratio)

        block_ratios = np.asarray(block_ratios, dtype=np.float64)

        features[f"{channel_name}_block_lsb_mean"] = float(
            np.mean(block_ratios)
        )

        features[f"{channel_name}_block_lsb_std"] = float(
            np.std(block_ratios)
        )

        features[f"{channel_name}_block_lsb_min"] = float(
            np.min(block_ratios)
        )

        features[f"{channel_name}_block_lsb_max"] = float(
            np.max(block_ratios)
        )

    return features

def calculate_sequential_lsb_statistics(image_path: str) -> dict:
    """
    Calculate LSB statistics for the beginning and remainder
    of the image.

    This is designed for sequential LSB embedding, where
    embedding starts from the first pixel and proceeds forward.
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = np.asarray(
        Image.open(image_path).convert("RGB"),
        dtype=np.uint8,
    )

    height, width, _ = image.shape
    total_pixels = height * width

    # Use the first 1% of pixels as the early region.
    early_pixel_count = max(1, int(total_pixels * 0.01))

    flat_image = image.reshape(-1, 3)

    early_region = flat_image[:early_pixel_count]
    remaining_region = flat_image[early_pixel_count:]

    features = {}

    for channel_index, channel_name in enumerate(("r", "g", "b")):
        early_lsb = early_region[:, channel_index] & 1

        features[
            f"{channel_name}_early_lsb_one_ratio"
        ] = float(np.mean(early_lsb))

        if len(remaining_region) > 0:
            remaining_lsb = remaining_region[:, channel_index] & 1

            features[
                f"{channel_name}_remaining_lsb_one_ratio"
            ] = float(np.mean(remaining_lsb))

            features[
                f"{channel_name}_sequential_lsb_difference"
            ] = float(
                abs(
                    features[f"{channel_name}_early_lsb_one_ratio"]
                    - features[f"{channel_name}_remaining_lsb_one_ratio"]
                )
            )
        else:
            features[
                f"{channel_name}_remaining_lsb_one_ratio"
            ] = features[
                f"{channel_name}_early_lsb_one_ratio"
            ]

            features[
                f"{channel_name}_sequential_lsb_difference"
            ] = 0.0

    return features

def calculate_local_residual_statistics(image_path: str) -> dict:
    """
    Calculate local pixel-residual statistics for grayscale images.

    These features measure absolute differences between neighboring
    pixels. LSB embedding can slightly alter these local residuals.
    """

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = np.asarray(
        Image.open(image_path).convert("L"),
        dtype=np.float64,
    )

    horizontal_difference = np.abs(
        image[:, 1:] - image[:, :-1]
    )

    vertical_difference = np.abs(
        image[1:, :] - image[:-1, :]
    )

    features = {
        "residual_horizontal_mean": float(
            np.mean(horizontal_difference)
        ),
        "residual_horizontal_std": float(
            np.std(horizontal_difference)
        ),
        "residual_horizontal_zero_ratio": float(
            np.mean(horizontal_difference == 0)
        ),
        "residual_vertical_mean": float(
            np.mean(vertical_difference)
        ),
        "residual_vertical_std": float(
            np.std(vertical_difference)
        ),
        "residual_vertical_zero_ratio": float(
            np.mean(vertical_difference == 0)
        ),
    }

    return features

def calculate_lsb_neighborhood_statistics(image_path: str) -> dict:
    """
    Calculate neighborhood statistics on the LSB plane.

    These features measure how neighboring LSB values are arranged
    horizontally and vertically.
    """

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = np.asarray(
        Image.open(image_path).convert("L"),
        dtype=np.uint8,
    )

    lsb = image & 1

    horizontal_left = lsb[:, :-1]
    horizontal_right = lsb[:, 1:]

    vertical_top = lsb[:-1, :]
    vertical_bottom = lsb[1:, :]

    horizontal_same = (
        horizontal_left == horizontal_right
    )

    vertical_same = (
        vertical_top == vertical_bottom
    )

    features = {
        "lsb_horizontal_same_ratio": float(
            np.mean(horizontal_same)
        ),
        "lsb_horizontal_transition_ratio": float(
            np.mean(~horizontal_same)
        ),
        "lsb_vertical_same_ratio": float(
            np.mean(vertical_same)
        ),
        "lsb_vertical_transition_ratio": float(
            np.mean(~vertical_same)
        ),
    }

    return features

def calculate_lsb_pair_statistics(image_path: str) -> dict:
    """
    Calculate horizontal and vertical LSB pair frequencies.

    The four possible neighboring LSB pairs are:
    00, 01, 10, and 11.

    These features capture how LSB values are distributed
    between neighboring pixels.
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = np.asarray(
        Image.open(image_path).convert("L"),
        dtype=np.uint8,
    )

    lsb = image & 1

    horizontal_left = lsb[:, :-1]
    horizontal_right = lsb[:, 1:]

    vertical_top = lsb[:-1, :]
    vertical_bottom = lsb[1:, :]

    horizontal_pairs = (
        horizontal_left * 2
        + horizontal_right
    )

    vertical_pairs = (
        vertical_top * 2
        + vertical_bottom
    )

    features = {}

    for pair_value, pair_name in (
        (0, "00"),
        (1, "01"),
        (2, "10"),
        (3, "11"),
    ):
        features[
            f"lsb_horizontal_pair_{pair_name}_ratio"
        ] = float(
            np.mean(
                horizontal_pairs == pair_value
            )
        )

        features[
            f"lsb_vertical_pair_{pair_name}_ratio"
        ] = float(
            np.mean(
                vertical_pairs == pair_value
            )
        )

    return features

def detect_suspicious_regions(
    image_path: str,
    block_size: int = 64,
    top_k: int = 5,
) -> list[dict]:
    """
    Detect suspicious image regions using local LSB statistics.

    The image is divided into blocks. Each block receives a
    suspicion score based on how close its average RGB LSB ratio
    is to 0.5.
    """

    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(
            f"Image not found: {image_path}"
        )

    image = np.asarray(
        Image.open(image_path).convert("RGB"),
        dtype=np.uint8,
    )

    height, width, _ = image.shape

    blocks = []
    suspicious_regions = []

    for y in range(0, height, block_size):
        for x in range(0, width, block_size):

            block = image[
                y:min(y + block_size, height),
                x:min(x + block_size, width),
            ]

            block_lsb = block & 1

            channel_ratios = np.mean(
                block_lsb,
                axis=(0, 1),
            )

            average_lsb_ratio = float(
                np.mean(channel_ratios)
            )

            # Calculate local LSB transition rate.
            gray_lsb = np.mean(block_lsb, axis=2)

            horizontal_transitions = np.mean(
                gray_lsb[:, 1:] != gray_lsb[:, :-1]
            ) if gray_lsb.shape[1] > 1 else 0.0

            vertical_transitions = np.mean(
                gray_lsb[1:, :] != gray_lsb[:-1, :]
            ) if gray_lsb.shape[0] > 1 else 0.0

            transition_rate = float(
                (horizontal_transitions + vertical_transitions) / 2
            )

            blocks.append(
                {
                    "x": int(x),
                    "y": int(y),
                    "width": int(block.shape[1]),
                    "height": int(block.shape[0]),
                    "average_lsb_ratio": average_lsb_ratio,
                    "transition_rate": transition_rate,
                    "channel_ratios": channel_ratios,
                }
            )

            

            
    # baseline starts HERE, outside both loops
    image_average_lsb_ratio = float(
        np.mean(
            [block["average_lsb_ratio"] for block in blocks]
        )
    )

    image_average_transition_rate = float(
        np.mean(
            [block["transition_rate"] for block in blocks]
        )
    )

    image_std_lsb_ratio = float(
        np.std(
            [block["average_lsb_ratio"] for block in blocks]
        )
    )

    image_std_transition_rate = float(
        np.std(
            [block["transition_rate"] for block in blocks]
        )
    )

    print(
        "Image baseline:",
        image_average_lsb_ratio,
        image_average_transition_rate,
    )
    for block in blocks:
        lsb_deviation = abs(
            block["average_lsb_ratio"] - image_average_lsb_ratio
        )

        transition_deviation = abs(
            block["transition_rate"] - image_average_transition_rate
        )

        if image_std_lsb_ratio > 0:
            lsb_anomaly = (
                lsb_deviation / image_std_lsb_ratio
            )
        else:
            lsb_anomaly = 0.0

        if image_std_transition_rate > 0:
            transition_anomaly = (
                transition_deviation / image_std_transition_rate
            )
        else:
            transition_anomaly = 0.0

        anomaly_score = (
            (lsb_anomaly * 0.5)
            + (transition_anomaly * 0.5)
        )

        suspicion_score = float(
            min(
                1.0,
                anomaly_score / 3.0,
            )
        )

        
        channel_ratios = block["channel_ratios"]

        suspicious_regions.append(
                {
                    "x": block["x"],
                    "y": block["y"],
                    "width": block["width"],
                    "height": block["height"],
                    "suspicion_score": suspicion_score,
                    "region_type": "LSB_CANDIDATE",
                    "metadata": {
                        "interpretation": "Candidate region ranked by local LSB anomaly; not a confirmed embedding location.",
                        "block_size": block_size,
                        "average_lsb_ratio": block["average_lsb_ratio"],
                        "transition_rate": block["transition_rate"],
                        "r_lsb_ratio": float(channel_ratios[0]),
                        "g_lsb_ratio": float(channel_ratios[1]),
                        "b_lsb_ratio": float(channel_ratios[2]),
                        "lsb_anomaly": float(lsb_anomaly),
                        "transition_anomaly": float(transition_anomaly),
                    },
                }
            )
    suspicious_regions.sort(
        key=lambda region: region["suspicion_score"],
        reverse=True,
    )

    return suspicious_regions[:top_k]

def calculate_rs_analysis(image_path: str, block_size: int = 2) -> dict:
    """
    Calculate a simplified RS-style steganalysis statistic.

    The image is divided into small blocks. Local variation is
    measured before and after flipping the LSBs.
    """
    image_path = Path(image_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = np.asarray(
        Image.open(image_path).convert("RGB"),
        dtype=np.uint8,
    )

    if block_size != 2:
        raise ValueError("This RS implementation currently requires block_size=2.")

    height, width, _ = image.shape

    # Ignore incomplete edge pixels so every block is exactly 2x2.
    usable_height = (height // 2) * 2
    usable_width = (width // 2) * 2

    image = image[:usable_height, :usable_width]

    features = {}

    for channel_index, channel_name in enumerate(("r", "g", "b")):
        channel = image[:, :, channel_index]

        # Convert image into 2x2 blocks:
        # [a b]
        # [c d]
        blocks = channel.reshape(
            usable_height // 2,
            2,
            usable_width // 2,
            2,
        ).transpose(0, 2, 1, 3)

        a = blocks[:, :, 0, 0].astype(np.int16)
        b = blocks[:, :, 0, 1].astype(np.int16)
        c = blocks[:, :, 1, 0].astype(np.int16)
        d = blocks[:, :, 1, 1].astype(np.int16)

        # Local variation of each block.
        original_score = (
            np.abs(a - b)
            + np.abs(b - c)
            + np.abs(c - d)
        )

        # Flip the LSB of every pixel.
        flipped = channel ^ 1

        flipped_blocks = flipped.reshape(
            usable_height // 2,
            2,
            usable_width // 2,
            2,
        ).transpose(0, 2, 1, 3)

        fa = flipped_blocks[:, :, 0, 0].astype(np.int16)
        fb = flipped_blocks[:, :, 0, 1].astype(np.int16)
        fc = flipped_blocks[:, :, 1, 0].astype(np.int16)
        fd = flipped_blocks[:, :, 1, 1].astype(np.int16)

        flipped_score = (
            np.abs(fa - fb)
            + np.abs(fb - fc)
            + np.abs(fc - fd)
        )

        regular_count = int(np.sum(flipped_score > original_score))
        singular_count = int(np.sum(flipped_score < original_score))

        usable_blocks = original_score.size

        features[f"{channel_name}_rs_regular_ratio"] = (
            regular_count / usable_blocks
        )

        features[f"{channel_name}_rs_singular_ratio"] = (
            singular_count / usable_blocks
        )

        features[f"{channel_name}_rs_difference"] = (
            (regular_count - singular_count) / usable_blocks
        )

    return features

def calculate_steganalysis_score(features: dict) -> dict:
    """
    Calculate a basic statistical steganalysis score.

    The score is based on how close LSB statistics are
    to patterns commonly associated with random LSB data.
    """

    lsb_ratios = [
        features["r_lsb_ones_ratio"],
        features["g_lsb_ones_ratio"],
        features["b_lsb_ones_ratio"],
    ]

    average_lsb_ratio = float(
        np.mean(lsb_ratios)
    )

    deviation_from_half = abs(
        average_lsb_ratio - 0.5
    )

    # Convert deviation into a 0-1 suspicion score.
    suspicion_score = float(
        max(0.0, min(1.0, 1.0 - (deviation_from_half * 2)))
    )

    if suspicion_score >= 0.75:
        predicted_class = "SUSPICIOUS"
    else:
        predicted_class = "LIKELY_CLEAN"

    return {
        "predicted_class": predicted_class,
        "suspicion_score": suspicion_score,
        "average_lsb_ratio": average_lsb_ratio,
    }

def analyze_image(image_path: str) -> dict:
    """
    Run the complete baseline steganalysis pipeline
    for one image.
    """

    start_time = time.perf_counter()

    features = extract_statistical_features(
        image_path
    )

    detection = calculate_steganalysis_score(
        features
    )

    processing_time_ms = (
        time.perf_counter() - start_time
    ) * 1000

    return {
        "features": features,
        "detection": detection,
        "processing_time_ms": float(processing_time_ms),
    }

def analyze_image_with_ml(image_path: str) -> dict:
    """
    Extract statistical features and classify the image
    using the trained Random Forest steganalysis model.
    """

    analysis = analyze_image(image_path)

    # Load the active model's required feature names.
    from backend.app.services.steganalysis_ml_service import load_random_forest

    _, model_features = load_random_forest()

    # Keep only the features actually used by the trained model.
    model_input_features = {
        feature_name: analysis["features"][feature_name]
        for feature_name in model_features
    }

    prediction = predict_steganography(
        analysis["features"]
    )

    suspicious_regions = detect_suspicious_regions(
        image_path
    )

    return {
        "features": model_input_features,
        "processing_time_ms": analysis["processing_time_ms"],
        "predicted_class": prediction["predicted_class"],
        "confidence": prediction["confidence"],
        "probabilities": prediction["probabilities"],
        "suspicious_regions": suspicious_regions,
    }