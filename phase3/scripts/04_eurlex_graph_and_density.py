"""Phase 3 prerequisites — build the EU graph, then check variant A is viable.

Three questions, none needing an LLM:

  P1  SEGMENTATION  — do EU acts split into sensible Article/paragraph units?
  P2  RESOLUTION    — we measured DETECTION (16.3 mentions/1k words) but never
                      resolution. Without resolved edges there is no graph, so
                      neither variant A (community chunking) nor variant B
                      (citation augmentation) can be built.
  P3  DENSITY       — ADGM has <1 edge/passage. On a graph that sparse,
                      community detection returns mostly singletons and
                      degenerates into linear chunking. This decides whether
                      variant A is viable AT ALL, and it is a go/no-go for
                      hypothesis H2 in SUMMARISER_PLAN.md.

Uses the FROZEN Phase-1 detector/resolver — aliases and FSMR off, since EU acts
cite other instruments by CELEX rather than by informal alias (cross-document
edges come from CELEX matching instead).

Writes reports/eurlex_graph.md.  --limit N for a subset.
"""
import argparse
import json
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from eurlex_ingest import load_eurlexsum, cited_celex   # noqa: E402
from eurlex_resolve import EuResolver                   # noqa: E402
from regkg.textutil import clean                        # noqa: E402
import re                                               # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=200)
args = ap.parse_args()

print(f"loading + segmenting EUR-Lex-Sum (limit {args.limit})...", flush=True)
corpus, id2celex, celex2id = load_eurlexsum(limit=args.limit)
docs = sorted({p.doc_id for p in corpus.passages})
per_doc = Counter(p.doc_id for p in corpus.passages)
depth = Counter(len(p.path) for p in corpus.passages)
print(f"  {len(corpus.passages):,} passages across {len(docs)} acts", flush=True)

# ---- P2 resolution: frozen resolver, aliases/FSMR off ----
# EuResolver restores the "refuse to guess" guard that use_aliases=False
# disabled, and routes named EU acts by CELEX. See phase3/src/eurlex_resolve.py.
never = re.compile(r"(?!x)x")          # matches nothing: no alias routing
res = EuResolver(corpus=corpus, aliases={}, alias_re=never,
                 use_guards=True, use_aliases=False, use_fsmr=False,
                 use_tolerant=True, use_attribution=True,
                 celex2id=celex2id)
print("resolving references (EU guard on)...", flush=True)
edges = res.run(corpus.passages)
uniq = {(e.source_uid, e.target_uid) for e in edges if e.source_uid != e.target_uid}
n_mentions = len(edges) + res.n_unresolved
rate = len(edges) / max(n_mentions, 1)

# ---- cross-document (CELEX) ----
xdoc = 0
for p in corpus.passages:
    xdoc += sum(1 for cx in cited_celex(p.text) if cx in celex2id
                and celex2id[cx] != p.doc_id)

# ---- P3 density + community structure (per document) ----
try:
    import networkx as nx
    HAVE_NX = True
except ImportError:
    HAVE_NX = False

by_doc_edges = {}
for s, t in uniq:
    d = corpus.by_uid[s].doc_id
    if corpus.by_uid[t].doc_id == d:
        by_doc_edges.setdefault(d, []).append((s, t))

edge_per_passage = len(uniq) / max(len(corpus.passages), 1)
comm_stats = None
if HAVE_NX:
    sizes, nontrivial, covered, tot = [], 0, 0, 0
    for d in docs:
        nodes = [p.uid for p in corpus.in_doc(d)]
        G = nx.Graph()
        G.add_nodes_from(nodes)
        G.add_edges_from(by_doc_edges.get(d, []))
        parts = nx.community.louvain_communities(G, seed=41)
        for c in parts:
            sizes.append(len(c))
            if len(c) >= 2:
                nontrivial += 1
                covered += len(c)
        tot += len(nodes)
    comm_stats = {"n": len(sizes), "median": st.median(sizes),
                  "mean": st.mean(sizes), "max": max(sizes),
                  "nontrivial": nontrivial,
                  "pct_in_nontrivial": 100 * covered / max(tot, 1)}

L = ["# Phase 3 prerequisites — EU graph construction and variant-A viability", "",
     f"Frozen Phase-1 detector/resolver, zero retuning; aliases + FSMR off (EU",
     f"acts cite by CELEX, not informal alias). Scope: **{len(docs)} acts**.", "",
     "## P1 — segmentation", "",
     f"- passages: **{len(corpus.passages):,}**",
     f"- per act: median {st.median(per_doc.values()):.0f}, "
     f"mean {st.mean(per_doc.values()):.0f}, max {max(per_doc.values())}",
     f"- depth distribution (1=Article, 2=paragraph, 3=point): "
     f"{dict(sorted(depth.items()))}", "",
     "## P2 — resolution (the number we never had)", "",
     f"- mentions detected: **{n_mentions:,}**",
     f"- resolved to a passage: **{len(edges):,}**",
     f"- unresolved: {res.n_unresolved:,} | ambiguous drops: {res.n_ambiguous:,}",
     f"- **resolution rate: {100*rate:.1f}%**  (ADGM ~ tuned corpus; CUAD 38.9%)",
     f"- unique within-document edges: **{len(uniq):,}**",
     "",
     "**Guard activity** (mentions REFUSED rather than force-resolved — the fix "
     "for the ~37% false-positive rate found in `eurlex_audit_sample.md`):",
     f"- refused: names a third-country instrument (Law/Decree/Treaty/…): "
     f"**{res.n_refused_external:,}**",
     f"- refused: target inside an unmodelled Annex/Appendix/Schedule: "
     f"**{res.n_refused_annex:,}**",
     f"- routed to another EU act we hold, via CELEX: **{res.n_routed_celex:,}**",
     f"- cross-document citations resolvable via CELEX (target in corpus): "
     f"**{xdoc:,}**", "",
     "## P3 — density and community viability (decides variant A)", "",
     f"- edges per passage: **{edge_per_passage:.2f}**  (ADGM ~0.50)"]
if comm_stats:
    c = comm_stats
    L += [f"- Louvain communities (per act, seed 41): {c['n']:,}",
          f"- community size: median {c['median']:.0f}, mean {c['mean']:.1f}, "
          f"max {c['max']}",
          f"- communities of size >= 2: **{c['nontrivial']:,}**",
          f"- **passages inside a non-trivial community: {c['pct_in_nontrivial']:.1f}%**",
          "",
          "**Verdict rule (pre-registered in SUMMARISER_PLAN.md §3.1):** if most",
          "passages fall into singleton communities, community chunking",
          "degenerates into linear chunking and variant A collapses toward base.",
          f"Measured: {c['pct_in_nontrivial']:.1f}% of passages sit in a community",
          f"of size >= 2."]
else:
    L += ["- (networkx not installed — community stats skipped)"]
L += ["", "## What this decides", "",
      "- **P2 gates everything**: no resolved edges, no graph, no variants.",
      "- **P3 gates variant A only.** Variant B (cross-document augmentation)",
      "  depends on CELEX matching, which is independent of within-document",
      "  density — so B remains testable even if A is not viable.",
      ]
(ROOT / "reports").mkdir(exist_ok=True)
(ROOT / "reports" / "eurlex_graph.md").write_text("\n".join(L) + "\n")

# cache edges for the summariser
out = ROOT / "data" / "eurlex_edges.jsonl"
out.parent.mkdir(exist_ok=True)
with open(out, "w") as f:
    for s, t in sorted(uniq):
        f.write(json.dumps({"src": s, "tgt": t}) + "\n")
print("\n".join(L[4:]))
print(f"\nwrote reports/eurlex_graph.md and data/eurlex_edges.jsonl")
