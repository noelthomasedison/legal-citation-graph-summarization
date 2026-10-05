"""Phase 3 — rebuild a versioned EU citation graph.

v1 UIDs were f"{doc_id}-{idx}-{path}" where `idx` is the ARTICLE index, so every
paragraph and point inside one Article shared it. Two passages sharing both idx
and path collided, and Corpus.by_uid silently kept only the last — meaning some
graph edges pointed at a record that had been overwritten.

The current default is the region-aware v2.2 repair. It keeps annex text in
bounded evidence passages while preventing flattened annex numbering from
masquerading as focal-act provisions. Outputs are version-tagged; the audited
v2 and historical v1 artefacts are never overwritten by the default command.

No LLM calls. Reuses EuResolver unchanged (the guard, CELEX routing and
relative-reference handling are all still correct).
"""
import argparse
import json
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from eurlex_ingest import load_eurlexsum, cited_celex     # noqa: E402
from eurlex_resolve import EuResolver                     # noqa: E402
from context_v2 import sha256_file                        # noqa: E402
from regkg.textutil import clean                          # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=0, help="0 = whole corpus")
ap.add_argument("--seed", type=int, default=41)
ap.add_argument("--artifact-tag", default="v2_2",
                help="suffix used for edge/report filenames")
ap.add_argument("--segmentation-version", choices=("legacy", "region-v2"),
                default="region-v2")
ap.add_argument("--force", action="store_true",
                help="replace an existing artefact with the same tag")
args = ap.parse_args()

if not re.fullmatch(r"[a-zA-Z0-9_]+", args.artifact_tag):
    sys.exit("--artifact-tag may contain only letters, numbers and underscores")
OUT_EDGES = ROOT / "data" / f"eurlex_edges_{args.artifact_tag}.jsonl"
OUT_REPORT = ROOT / "reports" / f"eurlex_graph_{args.artifact_tag}.md"
V1_EDGES = ROOT / "data" / "eurlex_edges.jsonl"
if (OUT_EDGES.exists() or OUT_REPORT.exists()) and not args.force:
    sys.exit(f"refusing to overwrite {args.artifact_tag} artefacts; pass --force "
             "only for an intentional identical-version rebuild")

# ---- v1 collision count, for the record (loads v1 uids, writes nothing) ----
print("loading corpus with v1 uids to count collisions...", flush=True)
c1, _, _ = load_eurlexsum(limit=args.limit or None, seed=args.seed,
                          uid_version="v1", segmentation_version="legacy")
v1_passages, v1_unique = len(c1.passages), len(c1.by_uid)
v1_collisions = getattr(c1, "n_uid_collisions", v1_passages - v1_unique)
print(f"  v1: {v1_passages:,} passages, {v1_unique:,} unique uids, "
      f"{v1_collisions:,} COLLISIONS", flush=True)
del c1

# ---- v2 build ----
print("loading corpus with v2 uids...", flush=True)
corpus, id2celex, celex2id = load_eurlexsum(limit=args.limit or None,
                                            seed=args.seed, uid_version="v2",
                                            segmentation_version=args.segmentation_version)
assert len(corpus.passages) == len(corpus.by_uid), "v2 uids must be unique"
print(f"  v2: {len(corpus.passages):,} passages == {len(corpus.by_uid):,} uids",
      flush=True)

never = re.compile(r"(?!x)x")
res = EuResolver(corpus=corpus, aliases={}, alias_re=never,
                 use_guards=True, use_aliases=False, use_fsmr=False,
                 use_tolerant=True, use_attribution=True,
                 celex2id=celex2id)
print("resolving (EU guard on)...", flush=True)
edges = res.run(corpus.passages)
by_pair = {}
for edge in edges:
    pair = (edge.source_uid, edge.target_uid)
    if pair[0] == pair[1]:
        continue
    meta = by_pair.setdefault(pair, {
        "mentions": [], "methods": [], "keywords": [],
    })
    mention = clean(edge.mention or "")
    if mention and mention not in meta["mentions"]:
        meta["mentions"].append(mention)
    if edge.how and edge.how not in meta["methods"]:
        meta["methods"].append(edge.how)
    keyword = clean(edge.keyword or "")
    if keyword and keyword not in meta["keywords"]:
        meta["keywords"].append(keyword)
uniq = set(by_pair)
n_mentions = len(edges) + res.n_unresolved
rate = len(edges) / max(n_mentions, 1)

within = sum(1 for s, t in uniq
             if corpus.by_uid[s].doc_id == corpus.by_uid[t].doc_id)
cross = len(uniq) - within

OUT_EDGES.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_EDGES, "w") as f:
    for s, t in sorted(uniq):
        f.write(json.dumps({
            "src": s, "tgt": t,
            "same_doc": corpus.by_uid[s].doc_id == corpus.by_uid[t].doc_id,
            **by_pair[(s, t)],
        }) + "\n")

per_doc = Counter(p.doc_id for p in corpus.passages)
n_annex_passages = sum(getattr(p, "region", "main") == "annex"
                        for p in corpus.passages)
L = [f"# Phase 3 {args.artifact_tag} — EU citation graph", "",
     f"Rebuilt with `uid_version=\"v2\"` and segmentation "
     f"`{args.segmentation_version}`. **Earlier artefacts untouched**: this writes",
     f"only `data/{OUT_EDGES.name}`.", "",
     "## UID collisions fixed", "",
     f"- v1: {v1_passages:,} passages but only {v1_unique:,} unique uids "
     f"→ **{v1_collisions:,} passages were silently overwritten** in "
     f"`Corpus.by_uid` ({100*v1_collisions/max(v1_passages,1):.1f}%).",
     f"- v2: {len(corpus.passages):,} passages, {len(corpus.by_uid):,} unique "
     "uids, 0 collisions (asserted at load).", "",
     "v1 uid = `{doc_id}-{article_idx}-{path}` — the article index is shared by",
     "every paragraph and point inside that Article, so a repeated path",
     "collided. v2 uid = `{doc_id}:v2:{ordinal:06d}:{path}` with a",
     "per-document ordinal incremented for every passage actually added.", "",
     "## Graph", "",
     f"- passages: **{len(corpus.passages):,}** across {len(per_doc):,} acts "
     f"(median {st.median(per_doc.values()):.0f}/act)",
     f"- isolated, bounded annex evidence passages: **{n_annex_passages:,}**",
     f"- mentions detected: {n_mentions:,}",
     f"- resolved: {len(edges):,} (**{100*rate:.1f}%**); unresolved "
     f"{res.n_unresolved:,}; ambiguous drops {res.n_ambiguous:,}",
     f"- unique edges: **{len(uniq):,}** — within-document **{within:,}**, "
     f"cross-document **{cross:,}** ({100*cross/max(len(uniq),1):.1f}%)",
     f"- edges per passage: {len(uniq)/max(len(corpus.passages),1):.2f}", "",
     "Guard activity (mentions refused rather than force-resolved):",
     f"- third-country instrument: {res.n_refused_external:,}",
     f"- target inside an unmodelled Annex/Appendix: {res.n_refused_annex:,}",
     f"- routed to another EU act we hold, via CELEX: {res.n_routed_celex:,}",
     f"- relative references resolved within their own Article: "
     f"{getattr(res, 'n_relative', 0):,}",
     f"- bare annex/table numbers refused: "
     f"{getattr(res, 'n_refused_annex_number', 0):,}",
     f"- duplicate same-path edges refused: "
     f"{getattr(res, 'n_refused_duplicate_path', 0):,}",
     f"- unresolved qualified structural references refused: "
     f"{getattr(res, 'n_refused_qualified', 0):,}",
     f"- complete nested point references resolved: "
     f"{getattr(res, 'n_nested_point', 0):,}",
     f"- structural heading echoes refused: "
     f"{getattr(res, 'n_refused_heading', 0):,}",
     f"- amendment-child references routed to the explicitly named amended act: "
     f"{getattr(res, 'n_routed_amendment', 0):,}",
     f"- amendment-child references refused because the amended act was absent: "
     f"{getattr(res, 'n_refused_amendment', 0):,}",
     f"- Official Journal dates refused: "
     f"{getattr(res, 'n_refused_date', 0):,}", "",
     "## Artefacts", "",
     f"- `data/{OUT_EDGES.name}` — sha256 `{sha256_file(OUT_EDGES)[:16]}…`",
     f"- v1 `data/eurlex_edges.jsonl` left unchanged"
     + (f" (sha256 `{sha256_file(V1_EDGES)[:16]}…`)" if V1_EDGES.exists() else ""),
     ]
OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
OUT_REPORT.write_text("\n".join(L) + "\n")
print("\n".join(L[4:]))
print(f"\nwrote {OUT_EDGES.name} and reports/{OUT_REPORT.name}")
