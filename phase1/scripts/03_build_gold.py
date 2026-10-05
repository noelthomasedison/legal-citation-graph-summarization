"""Step 2: build the gold oracle (flat + nested-expanded) and freeze the dev/test split.

Writes data/processed/gold.jsonl, data/processed/splits.json, reports/step2_gold.md.
"""
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regkg.ingest import load_corpus   # noqa: E402
from regkg.gold import load_gold       # noqa: E402
from regkg.splits import make_split, save_split  # noqa: E402

RAW = ROOT / "data" / "raw" / "GraphRAG4RegGraph"
PROC = ROOT / "data" / "processed"
out = []
def log(line=""):
    out.append(line)
    print(line)

corpus = load_corpus(RAW / "StructuredDocuments" / "Json")
gold = load_gold(RAW / "CrossReferenceData.csv", corpus)

log("# Step 2 — gold oracle + frozen split")
log()
log("## Gold edges")
log(f"- Rows after exact-duplicate removal: {len(gold):,}")
by_reason = Counter(e.exclusion_reason or "evaluable" for e in gold)
for k, v in by_reason.most_common():
    log(f"    - {k}: {v:,}")
ev = [e for e in gold if e.evaluable]
log(f"- Evaluable edges: {len(ev):,} "
    f"(Internal {sum(1 for e in ev if e.ref_type=='Internal'):,}, "
    f"External {sum(1 for e in ev if e.ref_type=='External'):,})")

# ---------- nested expansion ----------
log()
log("## Nested expansion (target 6.1 => all of 6.1.x)")
fanout = [len(e.expanded_target_uids) for e in ev]
exp = [n for n in fanout if n > 1]
log(f"- Targets that expand beyond themselves: {len(exp):,}/{len(ev):,} "
    f"({100*len(exp)/len(ev):.0f}%)")
log(f"- Expansion fan-out: median={int(statistics.median(fanout))}, "
    f"mean={statistics.mean(fanout):.1f}, max={max(fanout):,}")
log(f"- Total (source, expanded-target) pairs: {sum(fanout):,} "
    f"(vs {len(ev):,} flat)")

# ---------- split ----------
split = make_split(corpus, gold)
save_split(split, PROC / "splits.json")
sizes = Counter(p.doc_id for p in corpus.passages)
log()
log("## Frozen dev/test split (document level, by source doc)")
log(f"- Dev docs ({len(split['dev_docs'])}): "
    + ", ".join(f"{d}({sizes[d]}p)" for d in split["dev_docs"]))
log(f"- Dev edges: {split['dev_edges']:,} | Test edges: {split['test_edges']:,}")

# ---------- persist ----------
with open(PROC / "gold.jsonl", "w") as f:
    for e in gold:
        f.write(json.dumps({
            "source_uid": e.source_uid, "source_doc": e.source_doc,
            "ref_text": e.ref_text, "ref_type": e.ref_type,
            "target_uid": e.target_uid, "target_doc": e.target_doc,
            "target_path": list(e.target_path) if e.target_path else None,
            "evaluable": e.evaluable, "exclusion_reason": e.exclusion_reason,
            "expanded_target_uids": sorted(e.expanded_target_uids),
        }) + "\n")
log()
log(f"- Wrote {PROC/'gold.jsonl'} and {PROC/'splits.json'}")

(ROOT / "reports" / "step2_gold.md").write_text("\n".join(out) + "\n")
