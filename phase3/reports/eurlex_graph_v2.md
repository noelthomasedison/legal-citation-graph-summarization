# Phase 3 v2 — EU citation graph (collision-free UIDs)

Rebuilt with `uid_version="v2"`. **v1 artefacts untouched**: this writes
only `data/eurlex_edges_v2.jsonl`.

## UID collisions fixed

- v1: 258,907 passages but only 218,923 unique uids → **39,984 passages were silently overwritten** in `Corpus.by_uid` (15.4%).
- v2: 258,907 passages, 258,907 unique uids, 0 collisions (asserted at load).

v1 uid = `{doc_id}-{article_idx}-{path}` — the article index is shared by
every paragraph and point inside that Article, so a repeated path
collided. v2 uid = `{doc_id}:v2:{ordinal:06d}:{path}` with a
per-document ordinal incremented for every passage actually added.

## Graph

- passages: **258,907** across 1,504 acts (median 71/act)
- mentions detected: 312,359
- resolved: 191,692 (**61.4%**); unresolved 120,667; ambiguous drops 4,139
- unique edges: **144,138** — within-document **137,385**, cross-document **6,753** (4.7%)
- edges per passage: 0.56

Guard activity (mentions refused rather than force-resolved):
- third-country instrument: 7,068
- target inside an unmodelled Annex/Appendix: 3,988
- routed to another EU act we hold, via CELEX: 6,165
- relative references resolved within their own Article: 23,137

## Artefacts

- `data/eurlex_edges_v2.jsonl` — sha256 `3ab76ecc8bc424ad…`
- v1 `data/eurlex_edges.jsonl` left unchanged (sha256 `f3a6c7d881c94140…`)
