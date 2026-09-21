import math
import random
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]

POSITIVE_FILE = BASE_DIR / "data" / "processed" / "positive_events.csv"
RAIN_DIR = BASE_DIR / "data" / "raw" / "rainfall"
TERRAIN_DIR = BASE_DIR / "data" / "terrain"

OUTPUT_FILE = BASE_DIR / "data" / "processed" / "background_samples.csv"

random.seed(42)

N_BACKGROUND_PER_EVENT = 1
MIN_DISTANCE_KM = 10.0
MAX_DISTANCE_KM = 30.0

HGT_SIZE = 3601
HGT_NODATA = -32768
IMERG_NODATA = 29999


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    )

    return 2 * r * math.asin(math.sqrt(a))


def make_candidate(lat, lon):
    distance_km = random.uniform(
        MIN_DISTANCE_KM,
        MAX_DISTANCE_KM
    )

    bearing = random.uniform(0, 2 * math.pi)

    lat_offset = (
        distance_km * math.cos(bearing) / 111.0
    )

    lon_offset = (
        distance_km * math.sin(bearing)
        / (111.0 * max(math.cos(math.radians(lat)), 0.2))
    )

    return lat + lat_offset, lon + lon_offset


def get_tile_name(lat, lon):
    lat_floor = math.floor(lat)
    lon_floor = math.floor(lon)

    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"

    return (
        f"{ns}{abs(lat_floor):02d}_"
        f"{ew}{abs(lon_floor):03d}"
    )


def read_hgt(zip_path):
    with zipfile.ZipFile(zip_path, "r") as z:
        names = [
            name
            for name in z.namelist()
            if name.lower().endswith(".hgt")
        ]

        if not names:
            return None

        raw = z.read(names[0])

    values = np.frombuffer(
        raw,
        dtype=">i2"
    )

    if values.size != HGT_SIZE * HGT_SIZE:
        return None

    return values.reshape(
        (HGT_SIZE, HGT_SIZE)
    )


def sample_elevation(lat, lon):
    tile = get_tile_name(lat, lon)

    zip_filename = (
        tile.replace("_", "")
        + ".SRTMGL1.hgt.zip"
    )

    zip_path = TERRAIN_DIR / zip_filename

    if not zip_path.exists():
        return np.nan

    elevation = read_hgt(zip_path)

    if elevation is None:
        return np.nan

    tile_lat = math.floor(lat)
    tile_lon = math.floor(lon)

    row_float = (
        (tile_lat + 1 - lat)
        * 3600
    )

    col_float = (
        (lon - tile_lon)
        * 3600
    )

    row = int(round(row_float))
    col = int(round(col_float))

    row = max(0, min(3600, row))
    col = max(0, min(3600, col))

    value = int(elevation[row, col])

    if value == HGT_NODATA:
        return np.nan

    return float(value)


def sample_slope_aspect(lat, lon):
    tile = get_tile_name(lat, lon)

    zip_filename = (
        tile.replace("_", "")
        + ".SRTMGL1.hgt.zip"
    )

    zip_path = TERRAIN_DIR / zip_filename

    if not zip_path.exists():
        return np.nan, np.nan

    elevation = read_hgt(zip_path)

    if elevation is None:
        return np.nan, np.nan

    tile_lat = math.floor(lat)
    tile_lon = math.floor(lon)

    row_float = (
        (tile_lat + 1 - lat)
        * 3600
    )

    col_float = (
        (lon - tile_lon)
        * 3600
    )

    row = int(round(row_float))
    col = int(round(col_float))

    if row < 1 or row > 3599 or col < 1 or col > 3599:
        return np.nan, np.nan

    center = float(elevation[row, col])
    north = float(elevation[row - 1, col])
    south = float(elevation[row + 1, col])
    west = float(elevation[row, col - 1])
    east = float(elevation[row, col + 1])

    values = [
        center,
        north,
        south,
        west,
        east
    ]

    if any(v == HGT_NODATA for v in values):
        return np.nan, np.nan

    cell_size = 30.87

    dz_dx = (
        (east - west)
        / (2 * cell_size)
    )

    dz_dy = (
        (south - north)
        / (2 * cell_size)
    )

    slope = math.degrees(
        math.atan(
            math.sqrt(
                dz_dx ** 2
                + dz_dy ** 2
            )
        )
    )

    aspect = math.degrees(
        math.atan2(
            dz_dx,
            -dz_dy
        )
    )

    if aspect < 0:
        aspect += 360

    return slope, aspect


def rainfall_for_point(event_date, lat, lon):
    date_str = pd.Timestamp(event_date).strftime("%Y%m%d")

    zip_path = (
        RAIN_DIR
        / f"{date_str}_IMERG.zip"
    )

    if not zip_path.exists():
        return np.nan

    with zipfile.ZipFile(zip_path, "r") as z:
        names = [
            name
            for name in z.namelist()
            if name.lower().endswith(
                "total.accum.tif"
            )
        ]

        if not names:
            return np.nan

        tif_name = names[0]
        raw = z.read(tif_name)

    import io
    from PIL import Image

    image = Image.open(
        io.BytesIO(raw)
    )

    raster = np.array(image)

    if raster.ndim != 2:
        return np.nan

    row = int(
        round(
            (90.0 - lat) / 0.1
        )
    )

    col = int(
        round(
            (lon + 180.0) / 0.1
        )
    )

    if (
        row < 0
        or row >= raster.shape[0]
        or col < 0
        or col >= raster.shape[1]
    ):
        return np.nan

    value = int(
        raster[row, col]
    )

    if value == IMERG_NODATA:
        return np.nan

    return value / 10.0


print("=" * 70)
print("Earth Sentinel - Background Sample Generation")
print("=" * 70)

positive = pd.read_csv(
    POSITIVE_FILE
)

positive["event_date"] = pd.to_datetime(
    positive["event_date"]
)

positive_coords = list(
    zip(
        positive["latitude"],
        positive["longitude"]
    )
)

print(
    f"Positive events: {len(positive)}"
)

background = []

for i, row in positive.iterrows():

    accepted = False

    for attempt in range(100):

        lat, lon = make_candidate(
            float(row["latitude"]),
            float(row["longitude"])
        )

        # Keep candidates in the broad Northeast India area.
        if not (
            21.0 <= lat <= 30.0
            and 87.0 <= lon <= 98.0
        ):
            continue

        too_close = False

        for plat, plon in positive_coords:
            if (
                haversine_km(
                    lat,
                    lon,
                    plat,
                    plon
                )
                < MIN_DISTANCE_KM
            ):
                too_close = True
                break

        if too_close:
            continue

        elevation = sample_elevation(
            lat,
            lon
        )

        slope, aspect = sample_slope_aspect(
            lat,
            lon
        )

        rainfall = rainfall_for_point(
            row["event_date"],
            lat,
            lon
        )

        if (
            pd.isna(elevation)
            or pd.isna(slope)
            or pd.isna(aspect)
            or pd.isna(rainfall)
        ):
            continue

        background.append(
            {
                "latitude": lat,
                "longitude": lon,
                "event_date": row["event_date"].date(),
                "rainfall_mm": rainfall,
                "elevation_m": elevation,
                "slope_deg": slope,
                "aspect_deg": aspect,
                "label": 0,
                "sample_type": "background_pseudo_absence"
            }
        )

        accepted = True
        break

    if (i + 1) % 100 == 0:
        print(
            f"Processed {i + 1}/{len(positive)} "
            f"| Background samples: {len(background)}"
        )

    if not accepted:
        print(
            f"WARNING: no background sample "
            f"found for positive event {i}"
        )


background_df = pd.DataFrame(
    background
)

background_df.to_csv(
    OUTPUT_FILE,
    index=False
)

print()
print("=" * 70)
print("BACKGROUND SAMPLE SUMMARY")
print("=" * 70)

print(
    "Requested samples :",
    len(positive)
)

print(
    "Generated samples :",
    len(background_df)
)

if len(background_df) > 0:
    print(
        "Rainfall valid    :",
        background_df["rainfall_mm"].notna().sum()
    )

    print(
        "Elevation valid   :",
        background_df["elevation_m"].notna().sum()
    )

    print(
        "Slope valid       :",
        background_df["slope_deg"].notna().sum()
    )

    print(
        "Aspect valid      :",
        background_df["aspect_deg"].notna().sum()
    )

print()
print("Output:")
print(OUTPUT_FILE)
print("=" * 70)