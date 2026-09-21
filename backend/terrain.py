import zipfile
from pathlib import Path
import math

import numpy as np


BASE_DIR = Path(__file__).resolve().parents[1]

TERRAIN_DIR = BASE_DIR / "data" / "terrain"


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

        raw = z.read(hgt_files[0])

    data = np.frombuffer(
        raw,
        dtype=">i2"
    )

    expected = 3601 * 3601

    if data.size != expected:
        raise RuntimeError(
            f"Unexpected HGT size: {data.size} values"
        )

    return data.reshape((3601, 3601))


def sample_terrain(
    elevation,
    lat,
    lon,
    tile_lat,
    tile_lon,
):
    resolution = 1.0 / 3600.0

    col = int(
        round(
            (lon - tile_lon) / resolution
        )
    )

    row = int(
        round(
            (tile_lat + 1 - lat) / resolution
        )
    )

    if (
        row < 1
        or row >= 3600
        or col < 1
        or col >= 3600
    ):
        return None

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
        east,
    ]

    if any(value <= -32768 for value in values):
        return None

    lat_m = 111320.0

    lon_m = (
        111320.0
        * math.cos(math.radians(lat))
    )

    dz_dx = (
        (east - west)
        / (2.0 * lon_m * resolution)
    )

    dz_dy = (
        (north - south)
        / (2.0 * lat_m * resolution)
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
            dz_dy,
            -dz_dx
        )
    )

    aspect = (
        90.0 - aspect
    ) % 360.0

    return {
        "elevation_m": center,
        "slope_deg": slope,
        "aspect_deg": aspect,
    }


def get_terrain(lat, lon):

    tile = get_tile_name(
        lat,
        lon,
    )

    zip_filename = (
        tile.replace("_", "")
        + ".SRTMGL1.hgt.zip"
    )

    zip_path = TERRAIN_DIR / zip_filename

    if not zip_path.exists():
        raise FileNotFoundError(
            f"SRTM tile not found: {zip_filename}"
        )

    tile_lat = int(tile[1:3])
    tile_lon = int(tile[5:8])

    elevation = read_hgt(
        zip_path
    )

    result = sample_terrain(
        elevation=elevation,
        lat=lat,
        lon=lon,
        tile_lat=tile_lat,
        tile_lon=tile_lon,
    )

    if result is None:
        raise ValueError(
            "Unable to calculate terrain "
            "for this location"
        )

    result["tile"] = tile

    return result