from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import DefaultDict

import librosa
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ReferenceTrack:
    reference_id: str
    mcid: str
    title: str
    segment: str
    language: str
    audio_file: Path


@dataclass(frozen=True)
class MatchResult:
    mcid: str
    title: str
    segment: str
    language: str
    audio_score: float
    matched_timestamp_sec: float
    raw_match_count: int


def load_reference_library(path: str | Path) -> list[ReferenceTrack]:
    table = pd.read_csv(path).fillna("")
    tracks: list[ReferenceTrack] = []

    for row in table.to_dict("records"):
        tracks.append(
            ReferenceTrack(
                reference_id=str(row["reference_id"]),
                mcid=str(row["mcid"]),
                title=str(row["title"]),
                segment=str(row["segment"]),
                language=str(row["language"]),
                audio_file=Path(str(row["audio_file"])),
            )
        )

    return tracks


def create_fingerprint(
    audio_file: str | Path,
    sample_rate: int = 11025,
    hop_length: int = 512,
    n_fft: int = 2048,
    peaks_per_frame: int = 5,
    fanout: int = 4,
) -> list[tuple[tuple[int, int, int], int]]:
    """Create simple Shazam-style landmark hashes.

    Each hash combines two frequency bins and their time distance. This is a
    small proof-of-concept fingerprint, not a production-grade matching engine.
    """
    y, sr = librosa.load(audio_file, sr=sample_rate, mono=True)
    if len(y) == 0:
        return []

    stft = np.abs(librosa.stft(y, n_fft=n_fft, hop_length=hop_length))
    spectrogram = librosa.amplitude_to_db(stft, ref=np.max)

    peaks_by_frame: list[list[int]] = []
    for frame_index in range(spectrogram.shape[1]):
        frame = spectrogram[:, frame_index]
        strongest_bins = np.argsort(frame)[-peaks_per_frame:]
        strongest_bins = sorted(int(bin_id) for bin_id in strongest_bins)
        peaks_by_frame.append(strongest_bins)

    fingerprints: list[tuple[tuple[int, int, int], int]] = []
    for time_index, anchor_bins in enumerate(peaks_by_frame):
        for anchor_bin in anchor_bins:
            for delta_t in range(1, fanout + 1):
                target_time = time_index + delta_t
                if target_time >= len(peaks_by_frame):
                    continue
                for target_bin in peaks_by_frame[target_time]:
                    hash_key = (anchor_bin, target_bin, delta_t)
                    fingerprints.append((hash_key, time_index))

    return fingerprints


def build_reference_index(
    tracks: list[ReferenceTrack],
) -> tuple[DefaultDict[tuple[int, int, int], list[tuple[str, int]]], dict[str, ReferenceTrack]]:
    index: DefaultDict[tuple[int, int, int], list[tuple[str, int]]] = defaultdict(list)
    track_by_id = {track.reference_id: track for track in tracks}

    for track in tracks:
        fingerprints = create_fingerprint(track.audio_file)
        for hash_key, time_index in fingerprints:
            index[hash_key].append((track.reference_id, time_index))

    return index, track_by_id


def match_audio_sample(
    claim_audio_file: str | Path,
    index: DefaultDict[tuple[int, int, int], list[tuple[str, int]]],
    track_by_id: dict[str, ReferenceTrack],
    top_n: int = 3,
    sample_rate: int = 11025,
    hop_length: int = 512,
) -> list[MatchResult]:
    query_fingerprints = create_fingerprint(claim_audio_file, sample_rate=sample_rate, hop_length=hop_length)
    if not query_fingerprints:
        return []

    offset_votes: Counter[tuple[str, int]] = Counter()
    for hash_key, query_time in query_fingerprints:
        for reference_id, reference_time in index.get(hash_key, []):
            offset_votes[(reference_id, reference_time - query_time)] += 1

    best_by_reference: dict[str, tuple[int, int]] = {}
    for (reference_id, offset), count in offset_votes.items():
        previous = best_by_reference.get(reference_id)
        if previous is None or count > previous[0]:
            best_by_reference[reference_id] = (count, offset)

    ranked = sorted(best_by_reference.items(), key=lambda item: item[1][0], reverse=True)
    results: list[MatchResult] = []

    for reference_id, (raw_count, offset) in ranked[:top_n]:
        track = track_by_id[reference_id]
        score = min(100.0, round((raw_count / max(len(query_fingerprints), 1)) * 1000, 2))
        timestamp = max(0.0, round((offset * hop_length) / sample_rate, 2))
        results.append(
            MatchResult(
                mcid=track.mcid,
                title=track.title,
                segment=track.segment,
                language=track.language,
                audio_score=score,
                matched_timestamp_sec=timestamp,
                raw_match_count=raw_count,
            )
        )

    return results


def confidence_from_results(results: list[MatchResult]) -> tuple[str, str]:
    if not results:
        return "Weak", "Manual"

    top_score = results[0].audio_score
    second_score = results[1].audio_score if len(results) > 1 else 0.0
    score_gap = top_score - second_score

    if top_score >= 30 and score_gap >= 10:
        return "Strong", "Quick confirm"
    if top_score >= 12:
        return "Possible", "Review"
    return "Weak", "Manual"

