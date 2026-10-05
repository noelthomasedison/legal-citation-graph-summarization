"""Manual precision audit: stratified sample of predicted edges for adjudication.

Precision vs the gold CSV is invalid (gold non-exhaustive — PLAN.md amendment 2),
so precision is estimated by human/LLM-advisor adjudication of a random sample,
stratified by resolution risk:

  S1 safe      same-doc, keyworded, exact resolution   (spot-check 15)
  S2 bare      no keyword (any resolution)             (25)
  S3 crossdoc  target doc != source doc                (30)
  S4 nonexact  suffix/ascent/dup/self resolutions      (30)

Weighted overall precision = sum_i (stratum share × stratum precision).
Writes reports/audit_sample.md (for reading) + data/processed/audit_sample.jsonl.
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regkg.ingest import load_corpus                  # noqa: E402
from regkg.docmap import load_aliases, alias_pattern  # noqa: E402
from regkg.resolve import Resolver                    # noqa: E402
from regkg.textutil import clean                      # noqa: E402

RAW = ROOT / "data" / "raw" / "GraphRAG4RegGraph"
SEED = 13
QUOTA = {"S1_safe": 15, "S2_bare": 25, "S3_crossdoc": 30, "S4_nonexact": 30}

corpus = load_corpus(RAW / "StructuredDocuments" / "Json")
aliases = load_aliases(RAW / "DocumentMap.rtf")
resolver = Resolver(corpus, aliases, alias_pattern(aliases))
split = json.loads((ROOT / "data/processed/splits.json").read_text())
dev = set(split["dev_docs"])
preds = resolver.run([p for p in corpus.passages if p.doc_id in dev])

# unique edges with provenance (first occurrence wins)
seen, uniq = set(), []
for p in preds:
    k = (p.source_uid, p.target_uid)
    if k not in seen:
        seen.add(k)
        uniq.append(p)


def stratum(e) -> str:
    src, tgt = corpus.by_uid[e.source_uid], corpus.by_uid[e.target_uid]
    if tgt.doc_id != src.doc_id:
        return "S3_crossdoc"
    if not e.keyword:
        return "S2_bare"
    if e.how == "exact":
        return "S1_safe"
    return "S4_nonexact"


groups: dict[str, list] = {s: [] for s in QUOTA}
for e in uniq:
    groups[stratum(e)].append(e)

rng = random.Random(SEED)
sample = []
for s, quota in QUOTA.items():
    pool = groups[s]
    rng.shuffle(pool)
    sample.extend((s, e) for e in pool[:quota])

# ---------- write adjudication sheet ----------
lines = ["# Precision audit sample (seed=13, dev docs only)", ""]
lines.append("Stratum sizes (population): "
             + ", ".join(f"{s}={len(groups[s])}" for s in QUOTA))
lines.append("")
records = []
for i, (s, e) in enumerate(sample):
    src, tgt = corpus.by_uid[e.source_uid], corpus.by_uid[e.target_uid]
    text = clean(src.text)
    pos = text.find(e.mention)
    lo = max(0, pos - 130)
    ctx = text[lo: pos + len(e.mention) + 130].replace("\n", " ")
    lines += [f"## {i:03d} [{s}] `{e.mention}`  ({e.how or 'exact'})",
              f"- SRC {src.doc_id}:{src.passage_id}  →  TGT {tgt.doc_id}:{tgt.passage_id}",
              f"- CTX: …{ctx}…",
              f"- TGT TEXT: {clean(tgt.text)[:150].replace(chr(10),' ')}", ""]
    records.append({"i": i, "stratum": s, "mention": e.mention, "how": e.how,
                    "keyword": e.keyword, "source_uid": e.source_uid,
                    "target_uid": e.target_uid,
                    "src": f"{src.doc_id}:{src.passage_id}",
                    "tgt": f"{tgt.doc_id}:{tgt.passage_id}", "label": None})

(ROOT / "reports" / "audit_sample.md").write_text("\n".join(lines) + "\n")
with open(ROOT / "data/processed/audit_sample.jsonl", "w") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")

print(f"unique dev edges: {len(uniq):,}")
print("population by stratum:", {s: len(groups[s]) for s in QUOTA})
print("sampled:", Counter(s for s, _ in sample))
print("wrote reports/audit_sample.md and data/processed/audit_sample.jsonl")
