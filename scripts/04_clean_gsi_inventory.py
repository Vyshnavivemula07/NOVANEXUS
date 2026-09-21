from pathlib import Path
import pandas as pd

INPUT_FILE = Path("data/processed/gsi_landslide_inventory.csv")
OUTPUT_FILE = Path("data/processed/landslides_clean.csv")

def main():
    if not INPUT_FILE.exists():
        print("Input file not found:")
        print(INPUT_FILE)
        return

    df = pd.read_csv(INPUT_FILE)

    print("Original records:", len(df))

    # Standardize column names
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
        .str.replace(".", "", regex=False)
    )

    # Standardize state names
    state_map = {
        "MEGHALAYA": "Meghalaya",
        "MIZORAM": "Mizoram",
        "NAGALAND": "Nagaland",
        "MANIPUR": "Manipur",
        "TRIPURA": "Tripura",
        "ASSAM": "Assam",
        "SIKKIM": "Sikkim",
        "ARUNACHAL PRADESH": "Arunachal Pradesh",
        "KARNATAKA": "Karnataka",
        "KERALA": "Kerala",
        "TAMIL NADU": "Tamil Nadu",
    }

    df["state"] = df["state"].astype("string").str.strip()
    df["state"] = df["state"].replace(state_map)

    # Convert coordinates to numeric
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Remove records without valid coordinates
    before = len(df)

    df = df.dropna(subset=["latitude", "longitude"])

    df = df[
        df["latitude"].between(-90, 90)
        & df["longitude"].between(-180, 180)
    ]

    removed = before - len(df)

    # This is a documented landslide inventory.
    # It is NOT yet the final ML training label.
    df["label"] = 1

    # Save cleaned dataset
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)

    print()
    print("=" * 50)
    print("CLEANING COMPLETE")
    print("=" * 50)
    print("Original records:", before)
    print("Removed invalid-coordinate records:", removed)
    print("Clean records:", len(df))
    print()
    print("Columns:")
    print(list(df.columns))
    print()
    print("Saved:")
    print(OUTPUT_FILE)

if __name__ == "__main__":
    main()