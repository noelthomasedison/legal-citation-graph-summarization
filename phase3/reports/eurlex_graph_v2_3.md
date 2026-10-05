# Phase 3 v2_3 — EU citation graph

Rebuilt with `uid_version="v2"` and segmentation `region-v2`. **Earlier artefacts untouched**: this writes
only `data/eurlex_edges_v2_3.jsonl`.

## UID collisions fixed

- v1: 258,907 passages but only 218,923 unique uids → **39,984 passages were silently overwritten** in `Corpus.by_uid` (15.4%).
- v2: 232,756 passages, 232,756 unique uids, 0 collisions (asserted at load).

v1 uid = `{doc_id}-{article_idx}-{path}` — the article index is shared by
every paragraph and point inside that Article, so a repeated path
collided. v2 uid = `{doc_id}:v2:{ordinal:06d}:{path}` with a
per-document ordinal incremented for every passage actually added.

## Graph

- passages: **232,756** across 1,504 acts (median 75/act)
- isolated, bounded annex evidence passages: **10,156**
- mentions detected: 143,350
- resolved: 102,805 (**71.7%**); unresolved 40,545; ambiguous drops 173
- unique edges: **97,178** — within-document **86,719**, cross-document **10,459** (10.8%)
- edges per passage: 0.42

Guard activity (mentions refused rather than force-resolved):
- third-country instrument: 19,128
- target inside an unmodelled Annex/Appendix: 38,864
- routed to another EU act we hold, via CELEX: 10,987
- relative references resolved within their own Article: 30,190
- bare annex/table numbers refused: 40,727
- duplicate same-path edges refused: 207
- unresolved qualified structural references refused: 2,303
- complete nested point references resolved: 1,001
- structural heading echoes refused: 4,112
- amendment-child references routed to the explicitly named amended act: 319
- amendment-child references refused because the amended act was absent: 95
- Official Journal dates refused: 20,565

## Artefacts

- `data/eurlex_edges_v2_3.jsonl` — sha256 `dd20dbfe073eb544…`
- v1 `data/eurlex_edges.jsonl` left unchanged (sha256 `f3a6c7d881c94140…`)
