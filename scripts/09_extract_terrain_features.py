import zipfile
from pathlib import Path
import math

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_origin


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslide_rainfall_features.csv"
)

TERRAIN_DIR = (
    PROJECT_ROOT
    / "data"
    / "terrain"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslide_terrain_features.csv"
)


# =========================================================
# Load landslide locations
# =========================================================

df = pd.read_csv(INPUT_FILE)

df["latitude"] = pd.to_numeric(
    df["latitude"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["longitude"],
    errors="coerce"
)

df = df.dropna(
    subset=["latitude", "longitude"]
).copy()


# =========================================================
# Tile helpers
# =========================================================

def get_tile_name(lat, lon):

    lat_floor = math.floor(lat)
    lon_floor = math.floor(lon)

    lat_name = (
        f"N{lat_floor:02d}"
        if lat_floor >= 0
        else f"S{abs(lat_floor):02d}"
    )

    lon_name = (
        f"E{lon_floor:03d}"
        if lon_floor >= 0
        else f"W{abs(lon_floor):03d}"
    )

    return f"{lat_name}_{lon_name}"


# =========================================================
# HGT reader
# =========================================================

def read_hgt(zip_path):

    with zipfile.ZipFile(zip_path, "r") as z:

        hgt_files = [
            name
            for name in z.namelist()
            if name.lower().endswith(".hgt")
        ]

        if not hgt_files:
            raise RuntimeError(
                f"No HGT file found in {zip_path.name}"
            )

        hgt_name = hgt_files[0]

        raw = z.read(hgt_name)


    # SRTMGL1 = 3601 x 3601 signed 16-bit elevation
    data = np.frombuffer(
        raw,
        dtype=">i2"
    )

    expected = 3601 * 3601

    if data.size != expected:

        raise RuntimeError(
            f"Unexpected HGT size: "
            f"{data.size} values"
        )

    return data.reshape(
        (3601, 3601)
    )


# =========================================================
# Terrain calculation
# =========================================================

def sample_terrain(
    elevation,
    lat,
    lon,
    tile_lat,
    tile_lon
):

    # SRTMGL1 pixel spacing
    resolution = 1.0 / 3600.0

    # Convert coordinate to raster row/column
    col = int(
        round(
            (lon - tile_lon)
            / resolution
        )
    )

    row = int(
        round(
            (tile_lat + 1 - lat)
            / resolution
        )
    )


    # Keep a 1-pixel border for gradient calculation
    if (
        row < 1
        or row >= 3600
        or col < 1
        or col >= 3600
    ):

        return np.nan, np.nan, np.nan


    center = float(
        elevation[row, col]
    )

    north = float(
        elevation[row - 1, col]
    )

    south = float(
        elevation[row + 1, col]
    )

    west = float(
        elevation[row, col - 1]
    )

    east = float(
        elevation[row, col + 1]
    )


    # SRTM missing-data marker
    if any(
        value <= -32768
        for value in [
            center,
            north,
            south,
            west,
            east
        ]
    ):

        return np.nan, np.nan, np.nan


    # Approximate ground spacing in metres
    lat_m = 111320.0

    lon_m = (
        111320.0
        * math.cos(
            math.radians(lat)
        )
    )


    # Elevation gradient
    dz_dx = (
        (east - west)
        / (2.0 * lon_m * resolution)
    )

    dz_dy = (
        (north - south)
        / (2.0 * lat_m * resolution)
    )


    # Slope in degrees
    slope = math.degrees(
        math.atan(
            math.sqrt(
                dz_dx ** 2
                + dz_dy ** 2
            )
        )
    )


    # Aspect
    aspect = math.degrees(
        math.atan2(
            dz_dy,
            -dz_dx
        )
    )

    aspect = (
        90.0 - aspect
    ) % 360.0


    return center, slope, aspect


# =========================================================
# Process tiles
# =========================================================

df["srtm_tile"] = [
    get_tile_name(lat, lon)
    for lat, lon in zip(
        df["latitude"],
        df["longitude"]
    )
]


df["elevation_m"] = np.nan
df["slope_deg"] = np.nan
df["aspect_deg"] = np.nan


tiles = sorted(
    df["srtm_tile"].unique()
)


print("=" * 70)
print("Earth Sentinel - SRTM Terrain Extraction")
print("=" * 70)

print(
    f"Locations : {len(df)}"
)

print(
    f"Tiles     : {len(tiles)}"
)

print()


for index, tile in enumerate(
    tiles,
    start=1
):

    zip_filename = tile.replace("_", "") + ".SRTMGL1.hgt.zip"
    zip_path = TERRAIN_DIR / zip_filename

    print(
        f"[{index}/{len(tiles)}] {tile}"
    )


    if not zip_path.exists():

        print(
            "  ERROR - tile ZIP missing"
        )

        continue


    tile_lat = int(
        tile[1:3]
    )

    tile_lon = int(
        tile[5:8]
    )


    elevation = read_hgt(
        zip_path
    )


    tile_mask = (
        df["srtm_tile"] == tile
    )

    tile_indices = df.index[
        tile_mask
    ]


    valid_count = 0


    for idx in tile_indices:

        lat = float(
            df.loc[idx, "latitude"]
        )

        lon = float(
            df.loc[idx, "longitude"]
        )


        elev, slope, aspect = sample_terrain(
            elevation,
            lat,
            lon,
            tile_lat,
            tile_lon
        )


        df.loc[
            idx,
            "elevation_m"
        ] = elev

        df.loc[
            idx,
            "slope_deg"
        ] = slope

        df.loc[
            idx,
            "aspect_deg"
        ] = aspect


        if not np.isnan(elev):
            valid_count += 1


    print(
        f"  Locations: {len(tile_indices)}, "
        f"valid terrain: {valid_count}"
    )


# =========================================================
# Save
# =========================================================

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# =========================================================
# Summary
# =========================================================

print()
print("=" * 70)
print("TERRAIN EXTRACTION SUMMARY")
print("=" * 70)

print(
    f"Total locations : {len(df)}"
)

print(
    "Elevation valid :",
    int(df["elevation_m"].notna().sum())
)

print(
    "Slope valid     :",
    int(df["slope_deg"].notna().sum())
)

print(
    "Aspect valid    :",
    int(df["aspect_deg"].notna().sum())
)

print()
print(
    "Output:"
)

print(
    OUTPUT_FILE
)

print("=" * 70)