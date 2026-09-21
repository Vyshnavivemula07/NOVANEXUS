"""
Earth Sentinel
Step 1: Clean historical landslide data

Input:
    data/raw/landslides/

Output:
    data/processed/landslides_clean.csv
"""

from pathlib import Path
import pandas as pd


RAW_DIR = Path("data/raw/landslides")
OUTPUT_DIR = Path("data/processed")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def find_csv_files():
    return list(RAW_DIR.glob("*.csv"))


def clean_dataframe(df):
    # Normalize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    return df


def main():

    files = find_csv_files()

    if not files:
        print("No CSV files found.")
        print(f"Put historical landslide CSV files inside: {RAW_DIR}")
        return

    frames = []

    for file in files:
        print(f"Reading: {file}")

        try:
            df = pd.read_csv(file)
            df = clean_dataframe(df)
            df["source_file"] = file.name
            frames.append(df)

        except Exception as error:
            print(f"Could not read {file}: {error}")

    if not frames:
        print("No valid datasets were loaded.")
        return

    combined = pd.concat(frames, ignore_index=True)

    print()
    print("Total records:", len(combined))
    print("Columns:")
    print(list(combined.columns))

    output_file = OUTPUT_DIR / "landslides_clean.csv"

    combined.to_csv(output_file, index=False)

    print()
    print(f"Saved cleaned dataset to: {output_file}")


if __name__ == "__main__":
    main()