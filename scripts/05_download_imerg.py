import os
import re
import time
from pathlib import Path

import pandas as pd
import requests
from requests.auth import HTTPBasicAuth


# =========================================================
# Earth Sentinel - NASA IMERG V07B Downloader
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATES_FILE = PROJECT_ROOT / "data" / "processed" / "rainfall_request_points.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "rainfall"

PPS_EMAIL = os.environ.get("PPS_EMAIL")

if not PPS_EMAIL:
    raise RuntimeError(
        "PPS_EMAIL is not loaded in this CMD session."
    )

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# Read event dates
# ---------------------------------------------------------

df = pd.read_csv(DATES_FILE)

df["event_date"] = pd.to_datetime(
    df["event_date"],
    errors="coerce"
)

dates = sorted(
    df["event_date"]
    .dropna()
    .dt.strftime("%Y-%m-%d")
    .unique()
)

# V07B Final eligible dates
dates = [
    d for d in dates
    if d <= "2025-09-30"
]


print("=" * 70)
print("Earth Sentinel - NASA IMERG V07B Downloader")
print("=" * 70)
print(f"Eligible dates : {len(dates)}")
print(f"Output folder  : {OUTPUT_DIR}")
print("=" * 70)


# ---------------------------------------------------------
# NASA PPS session
# ---------------------------------------------------------

session = requests.Session()

session.auth = HTTPBasicAuth(
    PPS_EMAIL,
    PPS_EMAIL
)

session.headers.update({
    "User-Agent": "Earth-Sentinel-Research-Prototype/1.0"
})


# ---------------------------------------------------------
# Statistics
# ---------------------------------------------------------

downloaded = 0
skipped = 0
failed = []


# ---------------------------------------------------------
# Process every date
# ---------------------------------------------------------

for index, date_str in enumerate(dates, start=1):

    year, month, day = date_str.split("-")

    print()
    print(f"[{index}/{len(dates)}] {date_str}")

    output_file = (
        OUTPUT_DIR /
        f"{date_str.replace('-', '')}_IMERG.zip"
    )

    # -----------------------------------------------------
    # Skip existing file
    # -----------------------------------------------------

    if output_file.exists() and output_file.stat().st_size > 0:

        size_mb = output_file.stat().st_size / (1024 * 1024)

        print(
            f"  SKIP - already exists "
            f"({size_mb:.2f} MB)"
        )

        skipped += 1
        continue


    # -----------------------------------------------------
    # NASA directory
    # -----------------------------------------------------

    directory_url = (
        "https://arthurhouhttps.pps.eosdis.nasa.gov/"
        f"gpmdata/{year}/{month}/{day}/gis/"
    )

    try:

        response = session.get(
            directory_url,
            timeout=30
        )

        if response.status_code != 200:

            print(
                f"  DIRECTORY FAILED - "
                f"HTTP {response.status_code}"
            )

            failed.append(
                (date_str, f"directory HTTP {response.status_code}")
            )

            continue


        # -------------------------------------------------
        # Find daily GIS V07B ZIP
        # -------------------------------------------------

        pattern = (
            rf'3B-DAY-GIS\.MS\.MRG\.3IMERG\.'
            rf'{year}{month}{day}'
            rf'-S000000-E235959\.[0-9]+\.V07B\.zip'
        )

        matches = re.findall(
            pattern,
            response.text
        )


        if not matches:

            print(
                "  NO DAILY V07B ZIP FOUND"
            )

            failed.append(
                (date_str, "daily V07B ZIP not found")
            )

            continue


        # There should normally be one matching daily file
        filename = matches[0]

        file_url = directory_url + filename

        print(f"  NASA file: {filename}")
        print("  Downloading...")


        # -------------------------------------------------
        # Download
        # -------------------------------------------------

        with session.get(
            file_url,
            stream=True,
            timeout=(30, 180)
        ) as download_response:

            if download_response.status_code != 200:

                print(
                    f"  FAILED - HTTP "
                    f"{download_response.status_code}"
                )

                failed.append(
                    (
                        date_str,
                        f"file HTTP {download_response.status_code}"
                    )
                )

                continue


            temp_file = output_file.with_suffix(".part")

            with open(temp_file, "wb") as f:

                for chunk in download_response.iter_content(
                    chunk_size=1024 * 1024
                ):

                    if chunk:
                        f.write(chunk)


            temp_file.replace(output_file)


        size_mb = (
            output_file.stat().st_size /
            (1024 * 1024)
        )

        print(
            f"  OK - {size_mb:.2f} MB"
        )

        downloaded += 1


    except Exception as e:

        print(f"  FAILED - {e}")

        failed.append(
            (date_str, str(e))
        )


    # Small delay between requests
    time.sleep(0.5)


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

print()
print("=" * 70)
print("DOWNLOAD SUMMARY")
print("=" * 70)

print(f"Total eligible : {len(dates)}")
print(f"Downloaded     : {downloaded}")
print(f"Skipped        : {skipped}")
print(f"Failed         : {len(failed)}")


if failed:

    print()
    print("Failed dates:")

    for item in failed:
        print(" ", item)


print("=" * 70)