"""
Earth Sentinel
Create the ML training dataset.

This script will eventually combine:

    Historical landslides
    Rainfall
    Terrain
    Soil
    Land cover

into one training dataset.
"""

from pathlib import Path
import pandas as pd


PROCESSED_DIR = Path("data/processed")


def main():

    landslide_file = PROCESSED_DIR / "landslides_clean.csv"

    if not landslide_file.exists():
        print("Historical landslide dataset is not available yet.")
        print()
        print("Expected:")
        print(landslide_file)
        print()
        print("We will create this after obtaining the real dataset.")
        return

    landslides = pd.read_csv(landslide_file)

    print("Historical landslide records:", len(landslides))
    print()
    print("Available columns:")
    print(list(landslides.columns))

    print()
    print("Training dataset creation will continue")
    print("after the source-specific fields are mapped.")


if __name__ == "__main__":
    main()