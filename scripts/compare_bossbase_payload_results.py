from pathlib import Path

import pandas as pd


RESULTS = [
    {
        "payload": "0.01bpp",
        "fixed_0xAA_accuracy": 1.000,
        "random_accuracy": 0.600,
    },
    {
        "payload": "0.05bpp",
        "fixed_0xAA_accuracy": 1.000,
        "random_accuracy": 0.575,
    },
    {
        "payload": "0.10bpp",
        "fixed_0xAA_accuracy": 1.000,
        "random_accuracy": 0.725,
    },
    {
        "payload": "0.20bpp",
        "fixed_0xAA_accuracy": 1.000,
        "random_accuracy": 0.8625,
    },
]


def main():
    df = pd.DataFrame(RESULTS)

    df["accuracy_difference"] = (
        df["fixed_0xAA_accuracy"]
        - df["random_accuracy"]
    )

    df["fixed_0xAA_percent"] = (
        df["fixed_0xAA_accuracy"] * 100
    )

    df["random_percent"] = (
        df["random_accuracy"] * 100
    )

    df["difference_percent"] = (
        df["accuracy_difference"] * 100
    )

    print("\n" + "=" * 75)
    print("FIXED 0xAA vs RANDOM PAYLOAD COMPARISON")
    print("=" * 75)

    print(
        df[
            [
                "payload",
                "fixed_0xAA_percent",
                "random_percent",
                "difference_percent",
            ]
        ].to_string(
            index=False,
            formatters={
                "fixed_0xAA_percent": "{:.2f}%".format,
                "random_percent": "{:.2f}%".format,
                "difference_percent": "{:.2f}%".format,
            },
        )
    )

    print("\nINTERPRETATION:")

    print(
        "The fixed 0xAA payload achieved 100% accuracy "
        "at every tested payload level."
    )

    print(
        "Random payload accuracy ranged from "
        "57.5% to 86.25%."
    )

    print(
        "This indicates that the earlier 100% result "
        "was strongly influenced by the controlled "
        "payload pattern and should not be treated as "
        "general detector performance."
    )

    print(
        "The random-payload experiment provides the "
        "more realistic controlled evaluation."
    )


if __name__ == "__main__":
    main()