"""
Earth Sentinel
Step 2: Rainfall preprocessing
"""

from pathlib import Path
import pandas as pd


RAW_DIR = Path("data/raw/rainfall")
OUTPUT_DIR = Path("data/processed")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def main():

    files = list(RAW_DIR.glob("*.csv"))

    if not files:
        print("No rainfall CSV files found.")
        print(f"Put rainfall CSV files inside: {RAW_DIR}")
        return

    frames = []

    for file in files:
        print(f"Reading: {file}")

        try:
            df = pd.read_csv(file)

            df.columns = (
                df.columns
                .str.strip()
                .str.lower()
                .str.replace(" ", "_")
            )

            df["source_file"] = file.name
            frames.append(df)

        except Exception as error:
            print(f"Could not read {file}: {error}")

    if not frames:
        return

    combined = pd.concat(frames, ignore_index=True)

    print()
    print("Rainfall records:", len(combined))
    print("Columns:")
    print(list(combined.columns))

    output_file = OUTPUT_DIR / "rainfall_clean.csv"

    combined.to_csv(output_file, index=False)

    print()
    print(f"Saved: {output_file}")


if __name__ == "__main__":
    main()