import sys
from pathlib import Path
import secrets

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.app.services.lsb_service import embed_lsb_grayscale


SOURCE_DIR = Path(
    "storage/dataset/bossbase/source/BOSSbase_1.01"
)

CLEAN_DIR = Path(
    "storage/dataset/bossbase/clean"
)

STEGO_ROOT = Path(
    "storage/dataset/bossbase/stego_random_payload"
)


PAYLOAD_LEVELS = {
    "0.01bpp": 2621 // 8,
    "0.05bpp": 13107 // 8,
    "0.10bpp": 26214 // 8,
    "0.20bpp": 52429 // 8,
}


def main():
    CLEAN_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    STEGO_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    source_files = sorted(
        SOURCE_DIR.glob("*.pgm")
    )

    if len(source_files) != 200:
        raise ValueError(
            f"Expected exactly 200 source images, "
            f"found {len(source_files)}."
        )

    for payload_name, payload_bytes in PAYLOAD_LEVELS.items():

        payload_dir = STEGO_ROOT / payload_name

        payload_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        print(
            f"\nGENERATING {payload_name}: "
            f"{payload_bytes} random payload bytes"
        )

        for index, source_path in enumerate(
            source_files,
            start=1,
        ):

            clean_path = (
                CLEAN_DIR / source_path.name
            )

            if not clean_path.exists():
                clean_path.write_bytes(
                    source_path.read_bytes()
                )

            stego_name = (
                f"{source_path.stem}"
                f"_stego_{payload_name}.pgm"
            )

            stego_path = (
                payload_dir / stego_name
            )

            if stego_path.exists():
                continue

            payload = secrets.token_bytes(
                payload_bytes
            )

            embed_lsb_grayscale(
                input_path=str(source_path),
                output_path=str(stego_path),
                payload=payload,
                lsb_bits=1,
            )

            print(
                f"[{payload_name}] "
                f"[{index}/200] "
                f"{source_path.name}"
            )


if __name__ == "__main__":
    main()