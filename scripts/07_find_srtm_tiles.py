from pathlib import Path
import math
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslide_rainfall_features.csv"
)


df = pd.read_csv(INPUT_FILE)

df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

df = df.dropna(subset=["latitude", "longitude"])


def latitude_tile(lat):
    lat_floor = math.floor(lat)

    if lat_floor >= 0:
        return f"N{lat_floor:02d}"
    else:
        return f"S{abs(lat_floor):02d}"


def longitude_tile(lon):
    lon_floor = math.floor(lon)

    if lon_floor >= 0:
        return f"E{lon_floor:03d}"
    else:
        return f"W{abs(lon_floor):03d}"


df["srtm_tile"] = (
    df["latitude"].apply(latitude_tile)
    + "_"
    + df["longitude"].apply(longitude_tile)
)


tiles = sorted(df["srtm_tile"].unique())


print("=" * 60)
print("SRTM TILE REQUIREMENTS")
print("=" * 60)

print(f"Locations: {len(df)}")
print(f"Unique SRTM tiles: {len(tiles)}")

print()

for tile in tiles:
    count = (df["srtm_tile"] == tile).sum()
    print(f"{tile} : {count} locations")

print("=" * 60)