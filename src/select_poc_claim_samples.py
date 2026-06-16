from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLAIM_CANDIDATES = PROJECT_ROOT / "data" / "claims" / "yes_claim_candidates.csv"
OUTPUT_FILE = PROJECT_ROOT / "data" / "claims" / "poc_claim_sample_candidates.csv"
CLAIM_SAMPLES_FILE = PROJECT_ROOT / "data" / "claim_samples.csv"

POC_MCIDS = {
    "1_jf-0-0",
    "1_jf6101-0-0",
    "1_jf6102-0-0",
    "1_jf6103-0-0",
    "1_jf6104-0-0",
}


def main() -> None:
    df = pd.read_csv(CLAIM_CANDIDATES).fillna("")
    mask = df["reference_media_component_id"].isin(POC_MCIDS)
    selected = df[mask].copy()

    selected["claim_audio_file"] = selected.apply(
        lambda row: f"data/claim_audio/{str(row['source_file']).lower()}_{row['excel_row']}_{row['video_id']}.wav",
        axis=1,
    )

    output_columns = [
        "source_file",
        "excel_row",
        "video_title",
        "video_duration_sec",
        "existing_mcid",
        "claim_audio_file",
        "youtube_url",
        "asset_title",
        "language_name",
        "reference_title_or_segment",
        "reference_media_component_id",
    ]

    selected = selected[output_columns].sort_values(["source_file", "excel_row"])
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    selected.to_csv(OUTPUT_FILE, index=False)

    claim_samples = selected.rename(columns={"excel_row": "claim_row"})
    claim_samples = claim_samples[
        [
            "source_file",
            "claim_row",
            "video_title",
            "video_duration_sec",
            "existing_mcid",
            "claim_audio_file",
            "youtube_url",
        ]
    ]
    claim_samples["notes"] = ""
    claim_samples.to_csv(CLAIM_SAMPLES_FILE, index=False)

    print(f"Wrote {len(selected):,} POC claim candidates to {OUTPUT_FILE}")
    print(f"Wrote matcher input file to {CLAIM_SAMPLES_FILE}")
    print(selected["reference_media_component_id"].value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
