"""
Earth Sentinel
Step 0: Extract GSI Landslide Inventory from PDF

Input:
    data/raw/landslides/landslide_report.csv.pdf

Output:
    data/processed/gsi_landslide_inventory.csv
"""

from pathlib import Path
import csv
import pdfplumber


PDF_FILE = Path("data/raw/landslides/landslide_report.csv.pdf")
OUTPUT_DIR = Path("data/processed")
OUTPUT_FILE = OUTPUT_DIR / "gsi_landslide_inventory.csv"

EXPECTED_HEADERS = [
    "Sl.No.",
    "Slide_No",
    "State",
    "District",
    "Slide_Name",
    "NH_SH_Location",
    "Latitude",
    "Longitude",
    "Material Involved",
    "Movement Type",
    "History",
]


def clean_cell(value):
    if value is None:
        return ""

    value = str(value)

    # Replace line breaks created by PDF layout
    value = value.replace("\n", " ")
    value = value.replace("\r", " ")

    # Remove repeated spaces
    value = " ".join(value.split())

    return value.strip()


def is_header(row):
    if not row:
        return False

    text = " ".join(clean_cell(cell) for cell in row if cell)

    return (
        "Sl.No." in text
        and "Slide_No" in text
        and "State" in text
        and "District" in text
    )


def is_title(row):
    if not row:
        return False

    text = " ".join(clean_cell(cell) for cell in row if cell)

    return "LANDSLIDE INVENTORY" in text.upper()


def main():

    if not PDF_FILE.exists():
        print("PDF file not found:")
        print(PDF_FILE)
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_records = []
    total_pages = 0
    pages_with_tables = 0

    print("Opening PDF...")
    print(PDF_FILE)
    print()

    with pdfplumber.open(PDF_FILE) as pdf:

        total_pages = len(pdf.pages)

        print("Total PDF pages:", total_pages)
        print()
        print("Extracting tables...")
        print()

        for page_number, page in enumerate(pdf.pages, start=1):

            try:
                tables = page.extract_tables()

                if tables:
                    pages_with_tables += 1

                for table in tables:

                    if not table:
                        continue

                    header_found = False

                    for row in table:

                        cleaned = [
                            clean_cell(cell)
                            for cell in row
                        ]

                        if is_title(cleaned):
                            continue

                        if is_header(cleaned):
                            header_found = True
                            continue

                        if not header_found:
                            continue

                        # Ignore completely empty rows
                        if not any(cleaned):
                            continue

                        # Ignore accidental repeated headers
                        if is_header(cleaned):
                            continue

                        # Make exactly 11 columns
                        if len(cleaned) < len(EXPECTED_HEADERS):
                            cleaned += [""] * (
                                len(EXPECTED_HEADERS) - len(cleaned)
                            )

                        elif len(cleaned) > len(EXPECTED_HEADERS):
                            cleaned = cleaned[:len(EXPECTED_HEADERS)]

                        # First column should normally contain Sl.No.
                        # Skip obvious non-data rows.
                        if not cleaned[0]:
                            continue

                        all_records.append(cleaned)

            except Exception as error:
                print(
                    f"Warning: page {page_number} could not be processed:"
                )
                print(error)

            if page_number % 25 == 0:
                print(
                    f"Processed {page_number}/{total_pages} pages | "
                    f"Records collected: {len(all_records)}"
                )

    # Remove exact duplicate rows
    unique_records = []
    seen = set()

    for record in all_records:

        key = tuple(record)

        if key not in seen:
            seen.add(key)
            unique_records.append(record)

    print()
    print("=" * 60)
    print("EXTRACTION COMPLETE")
    print("=" * 60)
    print("PDF pages:", total_pages)
    print("Pages containing tables:", pages_with_tables)
    print("Records extracted:", len(all_records))
    print("Unique records:", len(unique_records))
    print()

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:

        writer = csv.writer(file)

        writer.writerow(EXPECTED_HEADERS)
        writer.writerows(unique_records)

    print("CSV created:")
    print(OUTPUT_FILE)
    print()


if __name__ == "__main__":
    main()