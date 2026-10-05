"""Step 1 build: corpus -> canonical passages + hierarchy; validate against gold joins.

Writes data/processed/passages.jsonl and reports/step1_ingest.md.
"""
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regkg.ingest import load_corpus          # noqa: E402
from regkg.hierarchy import build_edges, parent_of  # noqa: E402
from regkg.ids import canon                   # noqa: E402

RAW = ROOT / "data" / "raw" / "GraphRAG4RegGraph"
out = []
def log(line=""):
    out.append(line)
    print(line)

corpus = load_corpus(RAW / "StructuredDocuments" / "Json")
log("# Step 1 — ingest + hierarchy report")
log()
log(f"- Passages loaded: {len(corpus.passages):,} across {len(corpus.doc_ids())} documents")
frags = sum(1 for p in corpus.passages if p.fragment)
log(f"- Fragment passages (path from doc order): {frags:,}")

# duplicate canonical paths within a document (same path, >1 passage)
dupes = {k: v for k, v in corpus.by_path.items() if len(v) > 1}
log(f"- Duplicate (doc, path) keys: {len(dupes):,} "
    f"({sum(len(v) for v in dupes.values()):,} passages involved)")

# ---------- hierarchy coverage ----------
edges = build_edges(corpus)
non_root = [p for p in corpus.passages if len(p.path) > 1]
with_parent = sum(1 for p in non_root if parent_of(corpus, p) is not None)
log()
log("## Hierarchy")
log(f"- PARENT_OF edges: {len(edges):,}")
log(f"- Non-root passages with a resolvable parent: {with_parent:,}/{len(non_root):,} "
    f"({100*with_parent/max(len(non_root),1):.1f}%)")
depth = Counter(len(p.path) for p in corpus.passages)
log(f"- Depth distribution: {dict(sorted(depth.items()))}")

# ---------- gold join via canonical paths ----------
log()
log("## Gold CSV join via canonical paths")
rows = list(csv.DictReader(open(RAW / "CrossReferenceData.csv", encoding="utf-8-sig")))
rows = [r for r in rows if (r.get("SourceID") or "").strip()]

def join(row, which):
    try:
        d = int((row.get(f"{which}DocumentID") or "").strip())
    except ValueError:
        return None
    path = canon((row.get(f"{which}PassageID") or "").strip())
    return corpus.by_path.get((d, path))

in_corpus = [r for r in rows if (r.get("ReferenceType") or "").strip() != "Outsource"]
src_hit = sum(1 for r in rows if join(r, "Source"))
tgt_hit = sum(1 for r in in_corpus if join(r, "Target"))
log(f"- Source (doc, canonical path) join: {src_hit:,}/{len(rows):,} "
    f"({100*src_hit/len(rows):.1f}%)  [raw-string join was 99.7%]")
log(f"- Target (doc, canonical path) join: {tgt_hit:,}/{len(in_corpus):,} "
    f"({100*tgt_hit/len(in_corpus):.1f}%)  [raw-string join was 95.6%]")

misses = [r for r in in_corpus if not join(r, "Target")]
log(f"- Remaining target misses: {len(misses)}")
for r in misses[:10]:
    log(f"    - doc {r['TargetDocumentID']}: `{r['TargetPassageID']}` "
        f"(canon: {canon(r['TargetPassageID'])})")

# ---------- write processed ----------
import json  # noqa: E402
proc = ROOT / "data" / "processed"
proc.mkdir(parents=True, exist_ok=True)
with open(proc / "passages.jsonl", "w") as f:
    for p in corpus.passages:
        f.write(json.dumps(p.to_json()) + "\n")
log()
log(f"- Wrote {proc / 'passages.jsonl'}")

(ROOT / "reports" / "step1_ingest.md").write_text("\n".join(out) + "\n")
