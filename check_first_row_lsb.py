from PIL import Image
import numpy as np
from pathlib import Path

base = Path("storage/dataset")

files = sorted(base.glob("clean/*.tiff")) + sorted(base.glob("stego/*.tiff"))

for path in files:
    image = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)

    values = []

    for channel_index, channel_name in enumerate(("r", "g", "b")):
        row = image[0, :, channel_index] & 1
        transition_rate = np.mean(row[1:] != row[:-1])
        values.append(f"{channel_name}={transition_rate:.4f}")

    label = "STEGO" if "stego" in path.parent.name else "CLEAN"

    print(f"{label:5} {path.name:45} " + " ".join(values))
