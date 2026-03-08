# ElephantPaperReading

Elephant helps your paper reading, but the repository is optimized for one specific asset:

- one paper -> one JSON record
- writing-first analysis rather than method-only summaries
- batch processing of large PDF folders

## Repository Layout

```text
ElephantPaperReading/
  analyses/
    cvpr2025_first10/
      *.json
    cvpr2025_diffusion/
      *.json
    cvpr2025_diffusion_transformer_video/
      *.json
  schemas/
    paper_analysis.schema.json
  scripts/
    analyze_papers.py
    build_site_index.py
```

## What Each JSON Contains

Each paper record stores:

- source metadata
- core research story
- introduction structure
- method organization
- experiment narrative structure
- reusable writing templates
- notable sentences
- raw extracted sections

The canonical schema is [schemas/paper_analysis.schema.json](/Users/gulucaptain/Documents/Codex/ElephantPaperReading/schemas/paper_analysis.schema.json).

## Batch Run

Example for the CVPR 2025 PDF folder:

```bash
python3 scripts/analyze_papers.py \
  --pdf-dir /Users/gulucaptain/Downloads/cvpr2025 \
  --output-dir analyses/cvpr2025 \
  --failures analyses/cvpr2025/_failures.json \
  --overwrite
```

For a quick smoke test:

```bash
python3 scripts/analyze_papers.py \
  --pdf-dir /Users/gulucaptain/Downloads/cvpr2025 \
  --output-dir analyses/cvpr2025 \
  --failures analyses/cvpr2025/_failures.json \
  --limit 3 \
  --overwrite
```

## Current Collections

- `cvpr2025_first10`: initial showcase set for the public-facing site
- `cvpr2025_diffusion`: papers whose titles explicitly contain `diffusion`
- `cvpr2025_diffusion_transformer_video`: narrower title-matched subset for `diffusion transformer`, `DiT`, or `video diffusion`

The site index in `data/index.json` merges papers across collections by `paper_id`, so overlapping papers appear once with multiple collection tags.

## Notes

- Extraction currently uses `pypdf`, so image-only PDFs may fail or produce sparse text.
- The analysis is heuristic but deterministic, which makes it suitable for large-scale first-pass indexing.
- Higher-quality narrative interpretation can be layered on top later without breaking the per-paper JSON format.
