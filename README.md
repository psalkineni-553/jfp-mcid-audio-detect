# Shazam-Style Audio Fingerprint Matching for MCID Suggestion

A prototype that matches short YouTube claim audio samples against JFP reference audio and suggests the correct Media Component ID.

## Goal

Given a short claim audio sample, the project should return:

- Suggested MCID
- Matched JFP title or segment
- Language, if available
- Audio match score
- Matched timestamp
- Confidence
- Recommended action for Ben

## Step-by-Step Plan

### Step 1: Collect the minimum files

Put the April and May claim Excel files here:

```text
data/claims/
```

For this project, the April/May source files currently live at:

```text
/Users/pavankumarsalkineni/Documents/Work/JFP/Ben/unprocessed_claims_APR.xlsx
/Users/pavankumarsalkineni/Documents/Work/JFP/Ben/unprocessed_claims_MAY.xlsx
```

Run this to extract Ben's `Y` verdict rows into a smaller project CSV:

```text
python3 src/prepare_claim_candidates.py
```

That creates:

```text
data/claims/yes_claim_candidates.csv
```

Run this to create a 10-row proof-of-concept sample list for the first public JFP references:

```text
python3 src/select_poc_claim_samples.py
```

That creates:

```text
data/claims/poc_claim_sample_candidates.csv
data/claim_samples.csv
```

Put public or approved JFP reference audio files here:

```text
data/reference_audio/
```

Put short claim audio clips here:

```text
data/claim_audio/
```

For the first proof of concept, start small:

- 3 to 5 reference audio files
- 5 to 10 claim audio samples
- 10 to 15 seconds per claim sample

### Step 2: Fill the reference library

Open:

```text
data/reference_library_template.csv
```

Create a working copy named:

```text
data/reference_library.csv
```

Each row should map one reference audio file to one MCID.

For the first public English JFP demo, you can start from:

```text
data/reference_library_public_jfp_english.csv
```

Copy it to `data/reference_library.csv`, then fill the missing MCID values after checking the JFP reference table.

### Step 3: Fill the claim sample list

Open:

```text
data/claim_samples_template.csv
```

Create a working copy named:

```text
data/claim_samples.csv
```

Each row should describe one claim audio sample you want to test.

### Step 4: Build the first matching notebook

Notebook target:

```text
notebooks/Shazam_Style_MCID_Audio_Matching_POC.ipynb
```

Recommended sections:

1. Purpose
2. Difference from Bryce
3. Inputs
4. Load April/May claim data
5. Build small public JFP reference library
6. Extract or load claim audio samples
7. Create fingerprints
8. Match claim audio to reference audio
9. Return top 3 MCID candidates
10. Graphs
11. Limitations
12. Next steps

### Step 5: Demo output

The first result file should be:

```text
outputs/mcid_audio_match_results.xlsx
```

It should contain one row per claim sample with the top 3 candidate MCIDs.

## Shazam-Style App

Run the local demo app with:

```text
streamlit run app.py
```

The app supports two detection modes:

- Upload a short audio sample and click `Find MCID`
- Select a saved claim sample from `data/claim_samples.csv`

The app returns the suggested MCID, matched title/segment, audio score, timestamp, confidence, and recommended action.

For the app to work, all reference audio files listed in `data/reference_library.csv` must exist in:

```text
data/reference_audio/
```

## Difference From Bryce

Bryce is working on audio-to-text or language detection. This prototype is audio-to-reference matching, like Shazam, where the output is a suggested MCID, not a transcript.

## Confidence Rules

Use this simple first version:

- `Strong`: Top match is high and clearly better than second match
- `Possible`: Top match is decent, but still needs review
- `Weak`: No reliable audio match; do not use the MCID suggestion

## Recommended Actions

- `Quick confirm`: Strong match; Ben can review quickly
- `Review`: Possible match; Ben should inspect
- `Manual`: Weak match; do not trust the suggestion
