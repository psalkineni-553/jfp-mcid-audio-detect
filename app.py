from __future__ import annotations

import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from src.fingerprint_matcher import (
    ReferenceTrack,
    build_reference_index,
    confidence_from_results,
    load_reference_library,
    match_audio_sample,
)


PROJECT_ROOT = Path(__file__).resolve().parent
REFERENCE_LIBRARY = PROJECT_ROOT / "data" / "reference_library.csv"
CLAIM_SAMPLES = PROJECT_ROOT / "data" / "claim_samples.csv"
APP_VERSION = "Strict matching v3"
MIN_REVIEW_SCORE = 45.0


st.set_page_config(page_title="MCID Audio Detect", page_icon="🎧", layout="wide")


def resolve_project_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


@st.cache_data(show_spinner=False)
def load_reference_table() -> pd.DataFrame:
    if not REFERENCE_LIBRARY.exists():
        return pd.DataFrame()
    return pd.read_csv(REFERENCE_LIBRARY).fillna("")


@st.cache_resource(show_spinner=False)
def load_reference_index(reference_library_mtime: float):
    del reference_library_mtime
    tracks = load_reference_library(REFERENCE_LIBRARY)
    resolved_tracks = []
    for track in tracks:
        resolved_tracks.append(
            type(track)(
                reference_id=track.reference_id,
                mcid=track.mcid,
                title=track.title,
                segment=track.segment,
                language=track.language,
                audio_file=resolve_project_path(str(track.audio_file)),
            )
        )
    return build_reference_index(resolved_tracks)


def missing_reference_files(reference_df: pd.DataFrame) -> list[Path]:
    missing = []
    for audio_file in reference_df.get("audio_file", []):
        audio_path = resolve_project_path(str(audio_file))
        if not audio_path.exists():
            missing.append(audio_path)
    return missing


def save_uploaded_audio(uploaded_audio) -> Path:
    suffix = Path(uploaded_audio.name).suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(uploaded_audio.getbuffer())
        return Path(temp_file.name)


def render_results(results) -> None:
    confidence, action = confidence_from_results(results)
    top = results[0] if results else None
    if top and top.audio_score < MIN_REVIEW_SCORE:
        confidence, action = "Weak", "Manual"
    suggested_mcid = top.mcid if top and confidence != "Weak" else "No reliable match"

    metric_cols = st.columns(4)
    metric_cols[0].metric("Suggested MCID", suggested_mcid)
    metric_cols[1].metric("Confidence", confidence)
    metric_cols[2].metric("Audio Score", top.audio_score if top else 0)
    metric_cols[3].metric("Action", action)

    if not results:
        st.warning("No clear match found. Try a longer or cleaner 10-15 second sample.")
        return

    if confidence == "Weak":
        st.warning("The audio does not have enough evidence for a reliable MCID suggestion.")

    result_rows = []
    for rank, result in enumerate(results, start=1):
        result_rows.append(
            {
                "rank": rank,
                "suggested_mcid": result.mcid,
                "matched_title": result.title,
                "segment": result.segment,
                "language": result.language,
                "audio_score": result.audio_score,
                "matched_timestamp_sec": result.matched_timestamp_sec,
                "raw_match_count": result.raw_match_count,
            }
        )

    st.dataframe(pd.DataFrame(result_rows), hide_index=True, use_container_width=True)


st.title("Shazam-Style MCID Audio Detect")
st.caption(f"Short audio sample in. Suggested JFP Media Component ID out. {APP_VERSION}")

reference_df = load_reference_table()
missing_files = missing_reference_files(reference_df) if not reference_df.empty else []

with st.sidebar:
    st.header("Reference Library")
    st.write(f"{len(reference_df)} saved reference items")

    if not reference_df.empty:
        st.dataframe(
            reference_df[["mcid", "title", "segment", "language", "audio_file"]],
            hide_index=True,
            use_container_width=True,
        )

    if missing_files:
        st.warning("Saved-library mode needs these files.")
        for path in missing_files:
            st.code(str(path))

tab_quick, tab_library, tab_existing = st.tabs(
    ["Quick Shazam Test", "Saved Reference Library", "Saved Claim Samples"]
)

with tab_quick:
    st.subheader("Upload one known audio and one audio to check")

    left_col, right_col = st.columns(2)
    with left_col:
        reference_audio = st.file_uploader(
            "Known reference audio",
            type=["wav", "mp3", "m4a", "mp4", "aac", "flac", "ogg"],
            key="quick_reference_audio",
        )
        mcid = st.text_input("Reference MCID", value="1_jf6102-0-0")
        title = st.text_input("Reference title", value="Birth of Jesus")
        segment = st.text_input("Reference segment", value="Birth of Jesus")
        language = st.text_input("Reference language", value="English")
        if reference_audio is not None:
            st.audio(reference_audio)

    with right_col:
        check_audio = st.file_uploader(
            "Audio to check",
            type=["wav", "mp3", "m4a", "mp4", "aac", "flac", "ogg"],
            key="quick_check_audio",
        )
        if check_audio is not None:
            st.audio(check_audio)

    if st.button("Find MCID", type="primary", disabled=not reference_audio or not check_audio):
        reference_path = save_uploaded_audio(reference_audio)
        check_path = save_uploaded_audio(check_audio)
        track = ReferenceTrack(
            reference_id="uploaded_reference",
            mcid=mcid,
            title=title,
            segment=segment,
            language=language,
            audio_file=reference_path,
        )

        with st.spinner("Listening and matching..."):
            quick_index, quick_track_by_id = build_reference_index([track])
            results = match_audio_sample(check_path, quick_index, quick_track_by_id, top_n=3)
        render_results(results)

with tab_library:
    if reference_df.empty:
        st.info("Add data/reference_library.csv to use saved reference-library mode.")
    elif missing_files:
        st.warning("Saved reference-library mode needs the missing audio files shown in the sidebar.")
    else:
        with st.spinner("Preparing saved audio fingerprints..."):
            index, track_by_id = load_reference_index(REFERENCE_LIBRARY.stat().st_mtime)

        uploaded_audio = st.file_uploader(
            "Audio sample",
            type=["wav", "mp3", "m4a", "mp4", "aac", "flac", "ogg"],
            key="library_check_audio",
            label_visibility="collapsed",
        )

        if uploaded_audio is not None:
            st.audio(uploaded_audio)
            if st.button("Find MCID from Saved Library", type="primary"):
                temp_path = save_uploaded_audio(uploaded_audio)

                with st.spinner("Listening and matching..."):
                    results = match_audio_sample(temp_path, index, track_by_id, top_n=3)
                render_results(results)

with tab_existing:
    if reference_df.empty:
        st.info("Add data/reference_library.csv to use saved claim samples.")
    elif missing_files:
        st.warning("Saved claim mode needs the missing reference audio files shown in the sidebar.")
    elif not CLAIM_SAMPLES.exists():
        st.info("Add data/claim_samples.csv to use saved claim samples.")
    else:
        with st.spinner("Preparing saved audio fingerprints..."):
            index, track_by_id = load_reference_index(REFERENCE_LIBRARY.stat().st_mtime)

        claim_df = pd.read_csv(CLAIM_SAMPLES).fillna("")
        claim_df["label"] = claim_df.apply(
            lambda row: f"{row['source_file']} row {row['claim_row']} | {row['video_title']}",
            axis=1,
        )

        selected_label = st.selectbox("Claim sample", claim_df["label"])
        selected = claim_df[claim_df["label"].eq(selected_label)].iloc[0]
        selected_audio = resolve_project_path(str(selected["claim_audio_file"]))

        st.write(f"Existing MCID: `{selected['existing_mcid']}`")
        st.write(f"YouTube: {selected['youtube_url']}")

        if selected_audio.exists():
            st.audio(str(selected_audio))
            if st.button("Find MCID for Saved Sample", type="primary"):
                with st.spinner("Listening and matching..."):
                    results = match_audio_sample(selected_audio, index, track_by_id, top_n=3)
                render_results(results)
        else:
            st.warning("This claim audio file is not in the project yet.")
            st.code(str(selected_audio))
