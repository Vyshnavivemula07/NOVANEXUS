from pathlib import Path
import requests
import pandas as pd
import math
import time


PROJECT_ROOT = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslide_rainfall_features.csv"
)

OUTPUT_DIR = (
    PROJECT_ROOT
    / "data"
    / "terrain"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# ---------------------------------------------------------
# Load coordinates
# ---------------------------------------------------------

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
)


# ---------------------------------------------------------
# Generate SRTM tile names
# ---------------------------------------------------------

def lat_tile(lat):
    value = math.floor(lat)

    if value >= 0:
        return f"N{value:02d}"

    return f"S{abs(value):02d}"


def lon_tile(lon):
    value = math.floor(lon)

    if value >= 0:
        return f"E{value:03d}"

    return f"W{abs(value):03d}"


df["tile"] = (
    df["latitude"].apply(lat_tile)
    + df["longitude"].apply(lon_tile)
)


tiles = sorted(
    df["tile"].unique()
)


print("=" * 70)
print("Earth Sentinel - SRTM DEM Downloader")
print("=" * 70)

print(
    f"Locations : {len(df)}"
)

print(
    f"Tiles     : {len(tiles)}"
)

print()


# ---------------------------------------------------------
# Download tiles
# ---------------------------------------------------------

downloaded = 0
skipped = 0
failed = []


for index, tile in enumerate(
    tiles,
    start=1
):

    filename = (
        f"{tile}.SRTMGL1.hgt.zip"
    )

    output_file = (
        OUTPUT_DIR / filename
    )

    url = (
        "https://step.esa.int/"
        "auxdata/dem/SRTMGL1/"
        + filename
    )

    print(
        f"[{index}/{len(tiles)}] {tile}"
    )

    # -----------------------------------------------------
    # Skip existing files
    # -----------------------------------------------------

    if (
        output_file.exists()
        and output_file.stat().st_size > 0
    ):

        size_mb = (
            output_file.stat().st_size
            / 1024
            / 1024
        )

        print(
            f"  SKIP - already exists "
            f"({size_mb:.2f} MB)"
        )

        skipped += 1
        continue


    # -----------------------------------------------------
    # Download
    # -----------------------------------------------------

    print("  Downloading...")

    try:

        response = requests.get(
            url,
            stream=True,
            timeout=(30, 180)
        )

        if response.status_code != 200:

            print(
                f"  FAILED - HTTP "
                f"{response.status_code}"
            )

            failed.append(
                (tile, response.status_code)
            )

            continue


        temp_file = output_file.with_suffix(
            ".part"
        )

        with open(
            temp_file,
            "wb"
        ) as f:

            for chunk in response.iter_content(
                chunk_size=1024 * 1024
            ):

                if chunk:
                    f.write(chunk)


        temp_file.replace(
            output_file
        )


        size_mb = (
            output_file.stat().st_size
            / 1024
            / 1024
        )

        print(
            f"  OK - {size_mb:.2f} MB"
        )

        downloaded += 1


    except Exception as e:

        print(
            f"  FAILED - {e}"
        )

        failed.append(
            (tile, str(e))
        )


    time.sleep(0.5)


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

print()
print("=" * 70)
print("SRTM DOWNLOAD SUMMARY")
print("=" * 70)

print(
    f"Total tiles : {len(tiles)}"
)

print(
    f"Downloaded  : {downloaded}"
)

print(
    f"Skipped     : {skipped}"
)

print(
    f"Failed      : {len(failed)}"
)


if failed:

    print()
    print("Failed tiles:")

    for item in failed:
        print(" ", item)


print("=" * 70)