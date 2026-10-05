"""Step 0 audit: what does the gold data actually contain, and does it join?

Stdlib-only so it runs before any environment setup. Writes reports/audit.md.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "GraphRAG4RegGraph"
CSV_PATH = RAW / "CrossReferenceData.csv"
JSON_DIR = RAW / "StructuredDocuments" / "Json"
REPORT = ROOT / "reports" / "audit.md"

out = []
def log(line=""):
    out.append(line)
    print(line)

# ---------- 1. Structured documents ----------
docs = {}          # DocumentID -> list of passage records
uid_index = {}     # passage UID -> (doc_id, passage_id)
pid_index = defaultdict(set)  # (doc_id, passage_id) -> uids
for fp in sorted(JSON_DIR.glob("*.json")):
    try:
        records = json.loads(fp.read_text())
    except Exception as e:  # noqa
        log(f"!! failed to parse {fp.name}: {e}")
        continue
    for r in records:
        doc_id = r.get("DocumentID")
        docs.setdefault(doc_id, []).append(r)
        uid = r.get("ID")
        pid = str(r.get("PassageID", ""))
        if uid:
            uid_index[uid] = (doc_id, pid)
        pid_index[(doc_id, pid)].add(uid)

n_passages = sum(len(v) for v in docs.values())
log("# Phase 1 data audit")
log()
log("## Structured documents")
log(f"- JSON files: {len(list(JSON_DIR.glob('*.json')))}")
log(f"- Distinct DocumentIDs: {len(docs)}")
log(f"- Total passages: {n_passages:,}")
sizes = sorted((len(v), k) for k, v in docs.items())
log(f"- Passages per doc: min={sizes[0][0]} (doc {sizes[0][1]}), "
    f"median={sizes[len(sizes)//2][0]}, max={sizes[-1][0]:,} (doc {sizes[-1][1]})")

# PassageID format inventory
def id_shape(pid: str) -> str:
    s = re.sub(r"\d+", "9", pid)          # digit runs -> 9
    s = re.sub(r"[A-Za-z]+", "A", s)      # letter runs -> A
    return s
shapes = Counter(id_shape(str(r.get("PassageID", ""))) for v in docs.values() for r in v)
log(f"- Distinct PassageID shape patterns: {len(shapes)}")
log("- Top 12 shapes: " + ", ".join(f"`{s}`×{c}" for s, c in shapes.most_common(12)))

# ---------- 2. Cross-reference CSV ----------
rows = []
with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    for row in reader:
        rows.append(row)

log()
log("## CrossReferenceData.csv (gold edges)")
log(f"- Columns: {cols}")
log(f"- Total rows: {len(rows):,}")
nonempty = [r for r in rows if (r.get("SourceID") or "").strip()]
log(f"- Rows with non-empty SourceID: {len(nonempty):,}")
rt = Counter((r.get("ReferenceType") or "").strip() for r in nonempty)
log(f"- ReferenceType distribution: {dict(rt)}")
src_docs = Counter((r.get("SourceDocumentID") or "").strip() for r in nonempty)
log(f"- Distinct source documents: {len(src_docs)}")
same_doc = sum(1 for r in nonempty
               if (r.get("SourceDocumentID") or "").strip() == (r.get("TargetDocumentID") or "").strip())
log(f"- Same-document edges: {same_doc:,} | cross-document: {len(nonempty)-same_doc:,}")
missing_tgt = sum(1 for r in nonempty if not (r.get("TargetID") or "").strip())
log(f"- Rows with empty TargetID: {missing_tgt:,}")

# ---------- 3. Join integrity ----------
log()
log("## Join integrity (CSV ↔ structured JSON)")
src_uid_hit = sum(1 for r in nonempty if r.get("SourceID", "").strip() in uid_index)
tgt_rows = [r for r in nonempty if (r.get("TargetID") or "").strip()]
tgt_uid_hit = sum(1 for r in tgt_rows if r.get("TargetID", "").strip() in uid_index)
log(f"- SourceID found in JSON UIDs: {src_uid_hit:,}/{len(nonempty):,} "
    f"({100*src_uid_hit/max(len(nonempty),1):.1f}%)")
log(f"- TargetID found in JSON UIDs: {tgt_uid_hit:,}/{len(tgt_rows):,} "
    f"({100*tgt_uid_hit/max(len(tgt_rows),1):.1f}%)")

def pid_join(row, which):
    try:
        d = int((row.get(f"{which}DocumentID") or "").strip())
    except ValueError:
        return False
    p = (row.get(f"{which}PassageID") or "").strip()
    return (d, p) in pid_index

src_pid_hit = sum(1 for r in nonempty if pid_join(r, "Source"))
tgt_pid_hit = sum(1 for r in tgt_rows if pid_join(r, "Target"))
log(f"- (SourceDocumentID, SourcePassageID) joins to JSON: {src_pid_hit:,}/{len(nonempty):,} "
    f"({100*src_pid_hit/max(len(nonempty),1):.1f}%)")
log(f"- (TargetDocumentID, TargetPassageID) joins to JSON: {tgt_pid_hit:,}/{len(tgt_rows):,} "
    f"({100*tgt_pid_hit/max(len(tgt_rows),1):.1f}%)")

# ReferenceText presence (needed for detection-level eval)
has_reftext = sum(1 for r in nonempty if (r.get("ReferenceText") or "").strip())
log(f"- Rows with ReferenceText: {has_reftext:,}/{len(nonempty):,}")

# ---------- 4. Verdict ----------
log()
log("## Verdict flags")
if len(nonempty) < 10000:
    log(f"- NOTE: gold edge count is {len(nonempty):,} — update any '10,000+ edges' claim in deck/notes.")
else:
    log(f"- Gold edge count {len(nonempty):,} supports the '10,000+ edges' claim.")
for name, hit, tot in [("SourceID join", src_uid_hit, len(nonempty)),
                       ("TargetID join", tgt_uid_hit, len(tgt_rows))]:
    rate = hit / max(tot, 1)
    log(f"- {name}: {'OK' if rate > 0.95 else 'NEEDS NORMALISATION LAYER' if rate > 0.5 else 'BROKEN — investigate'} ({rate:.1%})")

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text("\n".join(out) + "\n")
print(f"\nwrote {REPORT}", file=sys.stderr)
