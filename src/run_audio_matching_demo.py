from __future__ import annotations

from pathlib import Path

import pandas as pd

from fingerprint_matcher import (
    build_reference_index,
    confidence_from_results,
    load_reference_library,
    match_audio_sample,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_LIBRARY = PROJECT_ROOT / "data" / "reference_library.csv"
CLAIM_SAMPLES = PROJECT_ROOT / "data" / "claim_samples.csv"
OUTPUT_FILE = PROJECT_ROOT / "outputs" / "mcid_audio_match_results.xlsx"


def blank_candidate(prefix: str) -> dict[str, object]:
    return {
        f"suggested_mcid_{prefix}": "",
        f"match_title_{prefix}": "",
        f"match_segment_{prefix}": "",
        f"match_language_{prefix}": "",
        f"audio_score_{prefix}": "",
        f"matched_timestamp_{prefix}": "",
    }


def candidate_columns(prefix: str, result) -> dict[str, object]:
    if result is None:
        return blank_candidate(prefix)

    return {
        f"suggested_mcid_{prefix}": result.mcid,
        f"match_title_{prefix}": result.title,
        f"match_segment_{prefix}": result.segment,
        f"match_language_{prefix}": result.language,
        f"audio_score_{prefix}": result.audio_score,
        f"matched_timestamp_{prefix}": result.matched_timestamp_sec,
    }


def main() -> None:
    if not REFERENCE_LIBRARY.exists():
        raise FileNotFoundError(f"Create {REFERENCE_LIBRARY} from the template first.")
    if not CLAIM_SAMPLES.exists():
        raise FileNotFoundError(f"Create {CLAIM_SAMPLES} from the template first.")

    tracks = load_reference_library(REFERENCE_LIBRARY)
    index, track_by_id = build_reference_index(tracks)
    claim_rows = pd.read_csv(CLAIM_SAMPLES).fillna("")

    output_rows: list[dict[str, object]] = []
    for row in claim_rows.to_dict("records"):
        claim_audio_file = PROJECT_ROOT / str(row["claim_audio_file"])
        results = match_audio_sample(claim_audio_file, index, track_by_id, top_n=3)
        confidence, action = confidence_from_results(results)

        output_row = {
            "source_file": row.get("source_file", ""),
            "claim_row": row.get("claim_row", ""),
            "video_title": row.get("video_title", ""),
            "video_duration_sec": row.get("video_duration_sec", ""),
            "existing_mcid": row.get("existing_mcid", ""),
        }

        for index_number in range(3):
            result = results[index_number] if index_number < len(results) else None
            output_row.update(candidate_columns(str(index_number + 1), result))

        output_row["confidence"] = confidence
        output_row["recommended_action"] = action
        output_rows.append(output_row)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(output_rows).to_excel(OUTPUT_FILE, index=False)
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

