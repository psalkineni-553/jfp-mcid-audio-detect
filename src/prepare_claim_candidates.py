from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CLAIM_FILES = {
    "APR": Path("/Users/pavankumarsalkineni/Documents/Work/JFP/Ben/unprocessed_claims_APR.xlsx"),
    "MAY": Path("/Users/pavankumarsalkineni/Documents/Work/JFP/Ben/unprocessed_claims_MAY.xlsx"),
}

OUTPUT_FILE = PROJECT_ROOT / "data" / "claims" / "yes_claim_candidates.csv"


OUTPUT_COLUMNS = [
    "source_file",
    "excel_row",
    "claim_id",
    "video_id",
    "youtube_url",
    "video_title",
    "video_duration_sec",
    "matching_duration",
    "longest_match",
    "asset_title",
    "existing_mcid",
    "language_name",
    "wess_language_id",
    "reference_title_or_segment",
    "reference_media_component_id",
    "reference_video_length_sec",
]


def first_existing(row: pd.Series, names: list[str]) -> object:
    for name in names:
        if name in row.index and pd.notna(row[name]) and str(row[name]).strip():
            return row[name]
    return ""


def clean_value(value: object) -> object:
    if pd.isna(value):
        return ""
    if isinstance(value, str):
        return value.strip()
    return value


def extract_yes_rows(source_file: str, workbook_path: Path) -> pd.DataFrame:
    df = pd.read_excel(workbook_path)
    verdict = df["Ver-dict"].astype(str).str.strip().str.upper()
    yes_df = df[verdict.eq("Y")].copy()

    rows: list[dict[str, object]] = []
    for zero_based_index, row in yes_df.iterrows():
        video_id = clean_value(first_existing(row, ["video_id", "(LINKED)    Video ID", "   (LINKED)    Video ID"]))
        youtube_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else ""

        rows.append(
            {
                "source_file": source_file,
                "excel_row": zero_based_index + 2,
                "claim_id": clean_value(first_existing(row, ["claim_id", "claimid"])),
                "video_id": video_id,
                "youtube_url": youtube_url,
                "video_title": clean_value(first_existing(row, ["video_title", "Video Title"])),
                "video_duration_sec": clean_value(first_existing(row, ["video_duration_sec", "U-Tube Video Dur. (Sec.)", "U-Tube Video Dur (Sec)"])),
                "matching_duration": clean_value(first_existing(row, ["matching_duration"])),
                "longest_match": clean_value(first_existing(row, ["longest_match"])),
                "asset_title": clean_value(first_existing(row, ["asset_title", "Asset Title"])),
                "existing_mcid": clean_value(first_existing(row, ["Media Component ID", "media_component_id"])),
                "language_name": clean_value(first_existing(row, ["Language Name"])),
                "wess_language_id": clean_value(first_existing(row, ["WESS Language ID", "WESS Language ID  "])),
                "reference_title_or_segment": clean_value(first_existing(row, ["Title Name or Segment", "Title Name or Sequence"])),
                "reference_media_component_id": clean_value(
                    first_existing(
                        row,
                        [
                            "Media Component ID                                  ",
                            "Media Component ID                                ",
                        ],
                    )
                ),
                "reference_video_length_sec": clean_value(first_existing(row, ["    Video Length (Sec)    "])),
            }
        )

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def main() -> None:
    extracted = []
    for source_file, workbook_path in CLAIM_FILES.items():
        if not workbook_path.exists():
            raise FileNotFoundError(workbook_path)
        extracted.append(extract_yes_rows(source_file, workbook_path))

    output = pd.concat(extracted, ignore_index=True)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(OUTPUT_FILE, index=False)

    print(f"Wrote {len(output):,} Yes verdict rows to {OUTPUT_FILE}")
    print(output["source_file"].value_counts().to_string())


if __name__ == "__main__":
    main()

