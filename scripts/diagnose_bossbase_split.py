import pandas as pd
from pathlib import Path


CSV_PATH = Path(
    "storage/dataset/metadata/"
    "bossbase_random_payload_steganalysis_features.csv"
)

PAYLOAD_LEVELS = (
    "0.01bpp",
    "0.05bpp",
    "0.10bpp",
    "0.20bpp",
)


def main():
    df = pd.read_csv(CSV_PATH)

    df["source_group"] = df["file_name"].str.extract(
        r"^(\d+)"
    )[0]

    all_groups = sorted(
        df["source_group"].unique()
    )

    train_groups = set(all_groups[:160])
    test_groups = set(all_groups[160:])

    print("TOTAL SOURCE GROUPS:", len(all_groups))
    print("TRAIN GROUPS:", len(train_groups))
    print("TEST GROUPS:", len(test_groups))

    print("\n" + "=" * 75)
    print("SOURCE-GROUP OVERLAP CHECK")
    print("=" * 75)

    overlap = train_groups & test_groups

    print("OVERLAPPING GROUPS:", len(overlap))

    if overlap:
        print("WARNING: SOURCE-GROUP LEAKAGE DETECTED")
        print(sorted(overlap))
    else:
        print("OK: NO SOURCE-GROUP OVERLAP")

    print("\n" + "=" * 75)
    print("TRAINING DISTRIBUTION")
    print("=" * 75)

    train_df = df[
        df["source_group"].isin(train_groups)
    ]

    print("\nTRAIN LABELS:")
    print(train_df["label"].value_counts())

    for payload in PAYLOAD_LEVELS:
        count = train_df[
            train_df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].shape[0]

        print(
            f"TRAIN {payload}: {count}"
        )

    print("\n" + "=" * 75)
    print("TEST DISTRIBUTION")
    print("=" * 75)

    test_df = df[
        df["source_group"].isin(test_groups)
    ]

    print("\nTEST LABELS:")
    print(test_df["label"].value_counts())

    for payload in PAYLOAD_LEVELS:
        count = test_df[
            test_df["file_name"].str.contains(
                f"_stego_{payload}.pgm",
                regex=False,
            )
        ].shape[0]

        print(
            f"TEST {payload}: {count}"
        )

    print("\n" + "=" * 75)
    print("PER-SOURCE TRAINING COUNTS")
    print("=" * 75)

    train_stego = train_df[
        train_df["label"] == "STEGO"
    ]

    payload_counts = []

    for group in sorted(train_groups):

        group_df = train_stego[
            train_stego["source_group"] == group
        ]

        counts = []

        for payload in PAYLOAD_LEVELS:
            count = group_df[
                group_df["file_name"].str.contains(
                    f"_stego_{payload}.pgm",
                    regex=False,
                )
            ].shape[0]

            counts.append(count)

        payload_counts.append(
            [group, *counts]
        )

    result = pd.DataFrame(
        payload_counts,
        columns=[
            "source_group",
            *PAYLOAD_LEVELS,
        ],
    )

    print(result.head(20).to_string(index=False))

    print("\nTOTAL STEGO PER PAYLOAD:")
    print(
        result[
            list(PAYLOAD_LEVELS)
        ].sum()
    )


if __name__ == "__main__":
    main()