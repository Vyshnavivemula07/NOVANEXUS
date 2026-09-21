import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.io import MemoryFile


# =========================================================
# Earth Sentinel
# Extract NASA IMERG rainfall at GSI landslide locations
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

EVENT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "northeast_landslides_dated.csv"
)

RAIN_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "rainfall"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "landslide_rainfall_features.csv"
)


print("=" * 70)
print("Earth Sentinel - NASA IMERG Rainfall Extraction")
print("=" * 70)


# ---------------------------------------------------------
# Load GSI dated landslide events
# ---------------------------------------------------------

df = pd.read_csv(EVENT_FILE)

df["event_date"] = pd.to_datetime(
    df["event_date"],
    errors="coerce"
)

df["latitude"] = pd.to_numeric(
    df["latitude"],
    errors="coerce"
)

df["longitude"] = pd.to_numeric(
    df["longitude"],
    errors="coerce"
)

df = df.dropna(
    subset=[
        "event_date",
        "latitude",
        "longitude"
    ]
).copy()


print(f"GSI dated events : {len(df)}")


# ---------------------------------------------------------
# V07B Final cutoff
# ---------------------------------------------------------

V07B_CUTOFF = pd.Timestamp("2025-09-30")

df["rainfall_eligible"] = (
    df["event_date"] <= V07B_CUTOFF
)


print(
    "Rainfall eligible:",
    int(df["rainfall_eligible"].sum())
)

print(
    "After V07B cutoff:",
    int((~df["rainfall_eligible"]).sum())
)


# ---------------------------------------------------------
# Output columns
# ---------------------------------------------------------

df["rainfall_mm"] = np.nan
df["rainfall_raw"] = np.nan
df["rainfall_status"] = "not_processed"


# ---------------------------------------------------------
# Process each event date
# ---------------------------------------------------------

eligible_df = df[df["rainfall_eligible"]].copy()

unique_dates = sorted(
    eligible_df["event_date"].dt.strftime("%Y%m%d").unique()
)

print(
    f"Unique rainfall dates to process: {len(unique_dates)}"
)

print()


for index, date_str in enumerate(
    unique_dates,
    start=1
):

    zip_file = (
        RAIN_DIR
        / f"{date_str}_IMERG.zip"
    )

    print(
        f"[{index}/{len(unique_dates)}] "
        f"{date_str}"
    )

    if not zip_file.exists():

        print(
            "  ERROR - ZIP file not found"
        )

        mask = (
            df["event_date"]
            .dt.strftime("%Y%m%d")
            == date_str
        )

        df.loc[
            mask,
            "rainfall_status"
        ] = "zip_missing"

        continue


    # -----------------------------------------------------
    # Events for this date
    # -----------------------------------------------------

    mask = (
        df["event_date"]
        .dt.strftime("%Y%m%d")
        == date_str
    )

    date_events = df.loc[
        mask
        & df["rainfall_eligible"]
    ].copy()


    # -----------------------------------------------------
    # Find total.accum.tif inside ZIP
    # -----------------------------------------------------

    with zipfile.ZipFile(
        zip_file,
        "r"
    ) as z:

        tif_files = [
            name
            for name in z.namelist()
            if (
                name.lower().endswith(
                    "total.accum.tif"
                )
                and not name.endswith("/")
            )
        ]

        if not tif_files:

            print(
                "  ERROR - total.accum.tif not found"
            )

            df.loc[
                mask,
                "rainfall_status"
            ] = "raster_missing"

            continue


        tif_name = tif_files[0]

        raster_bytes = z.read(
            tif_name
        )


    # -----------------------------------------------------
    # Open GeoTIFF directly from memory
    # -----------------------------------------------------

    with MemoryFile(
        raster_bytes
    ) as memfile:

        with memfile.open() as src:

            coordinates = list(
                zip(
                    date_events["longitude"],
                    date_events["latitude"]
                )
            )

            samples = list(
                src.sample(coordinates)
            )


            for row_index, sample in zip(
                date_events.index,
                samples
            ):

                raw_value = float(
                    sample[0]
                )

                df.loc[
                    row_index,
                    "rainfall_raw"
                ] = raw_value


                # NASA IMERG GIS accumulation:
                # stored in 0.1 mm units.
                #
                # 475 -> 47.5 mm
                #
                # 29999 = missing value.

                if raw_value == 29999:

                    df.loc[
                        row_index,
                        "rainfall_mm"
                    ] = np.nan

                    df.loc[
                        row_index,
                        "rainfall_status"
                    ] = "nodata"

                else:

                    rainfall_mm = (
                        raw_value / 10.0
                    )

                    df.loc[
                        row_index,
                        "rainfall_mm"
                    ] = rainfall_mm

                    df.loc[
                        row_index,
                        "rainfall_status"
                    ] = "ok"


    valid_count = int(
        (
            df.loc[
                date_events.index,
                "rainfall_status"
            ]
            == "ok"
        ).sum()
    )

    print(
        f"  Events: {len(date_events)}, "
        f"valid rainfall: {valid_count}"
    )


# ---------------------------------------------------------
# Post-cutoff events
# ---------------------------------------------------------

df.loc[
    ~df["rainfall_eligible"],
    "rainfall_status"
] = "after_v07b_cutoff"


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ---------------------------------------------------------
# Final summary
# ---------------------------------------------------------

print()
print("=" * 70)
print("RAINFALL EXTRACTION SUMMARY")
print("=" * 70)

print(
    f"Total GSI events       : {len(df)}"
)

print(
    "Rainfall values OK     :",
    int(
        (df["rainfall_status"] == "ok").sum()
    )
)

print(
    "NoData rainfall        :",
    int(
        (df["rainfall_status"] == "nodata").sum()
    )
)

print(
    "After V07B cutoff      :",
    int(
        (
            df["rainfall_status"]
            == "after_v07b_cutoff"
        ).sum()
    )
)

print(
    "ZIP missing            :",
    int(
        (
            df["rainfall_status"]
            == "zip_missing"
        ).sum()
    )
)

print()
print(
    "Output:"
)
print(OUTPUT_FILE)

print("=" * 70)