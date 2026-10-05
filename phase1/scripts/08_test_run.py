"""THE ONE-SHOT TEST RUN. Frozen config, 32 sealed documents, single execution.

Thresholds pre-registered in PLAN.md (2026-07-14), judged on the
nested + source-nested credit mode (the mode the dev evidence quoted):
  T1 Internal R >= 0.90 | T2 All R >= 0.80 | T3 External R >= 0.45
  T4 audited precision >= 0.80 (sample generated here, seed=41; adjudicated
     separately, same stratification protocol as dev)

Writes reports/step6_test_run.md, reports/test_audit_sample.md,
data/processed/test_audit_sample.jsonl.
"""
import json
import random
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regkg.ingest import load_corpus                      # noqa: E402
from regkg.gold import load_gold                          # noqa: E402
from regkg.docmap import load_aliases, alias_pattern      # noqa: E402
from regkg.resolve import Resolver                        # noqa: E402
from regkg.evaluate import score, build_source_kin        # noqa: E402
from regkg.textutil import clean                          # noqa: E402

RAW = ROOT / "data" / "raw" / "GraphRAG4RegGraph"
out = []
def log(line=""):
    out.append(line)
    print(line)

corpus = load_corpus(RAW / "StructuredDocuments" / "Json")
gold = load_gold(RAW / "CrossReferenceData.csv", corpus)
split = json.loads((ROOT / "data/processed/splits.json").read_text())
test_docs = set(split["test_docs"])
aliases = load_aliases(RAW / "DocumentMap.rtf")
resolver = Resolver(corpus, aliases, alias_pattern(aliases))   # full config, frozen

test_passages = [p for p in corpus.passages if p.doc_id in test_docs]
test_gold = [g for g in gold if g.source_doc in test_docs]
ev = [g for g in test_gold if g.evaluable]
kin = build_source_kin(test_gold, corpus)

log("# Step 6 — ONE-SHOT TEST RUN (sealed docs, frozen config)")
log()
log(f"- Test documents: {len(test_docs)} | passages: {len(test_passages):,}")
log(f"- Test gold edges (evaluable): {len(ev):,} "
    f"(Internal {sum(1 for g in ev if g.ref_type=='Internal'):,}, "
    f"External {sum(1 for g in ev if g.ref_type=='External'):,})")

preds = resolver.run(test_passages)
uniq = {(p.source_uid, p.target_uid) for p in preds}
log(f"- Predicted edges: {len(uniq):,} | unresolved mentions: "
    f"{resolver.n_unresolved:,} | ambiguous drops: {resolver.n_ambiguous:,}")
log()

gold_int = [g for g in test_gold if g.ref_type == "Internal"]
gold_ext = [g for g in test_gold if g.ref_type == "External"]
log("| Credit mode | All | Internal | External |")
log("|---|---|---|---|")
rows = {}
for name, nested, k in [("Exact", False, None), ("Nested", True, None),
                        ("Nested + source-nested", True, kin)]:
    r_all = score(preds, test_gold, nested, k).recall
    r_int = score(preds, gold_int, nested, k).recall
    r_ext = score(preds, gold_ext, nested, k).recall
    rows[name] = (r_all, r_int, r_ext)
    log(f"| {name} | {r_all:.3f} | {r_int:.3f} | {r_ext:.3f} |")

r_all, r_int, r_ext = rows["Nested + source-nested"]
log()
log("## Threshold verdicts (nested + source-nested, as pre-registered)")
for tid, desc, val, bar in [("T1", "Internal recall", r_int, 0.90),
                            ("T2", "Overall recall", r_all, 0.80),
                            ("T3", "External recall", r_ext, 0.45)]:
    log(f"- {tid} {desc}: {val:.3f} vs >= {bar:.2f}  ->  "
        f"{'PASS' if val >= bar else 'MISS'}")
log("- T4 audited precision >= 0.80: PENDING adjudication of the seed-41 sample below")

# ---------- per-size buckets (does recall fall on big unseen docs?) ----------
sizes = Counter(p.doc_id for p in corpus.passages)
buckets = {"small (<200p)": lambda d: sizes[d] < 200,
           "medium (200-800p)": lambda d: 200 <= sizes[d] < 800,
           "large (>=800p)": lambda d: sizes[d] >= 800}
log()
log("## Recall by document size (nested + source-nested)")
for bname, f in buckets.items():
    sub = [g for g in test_gold if f(g.source_doc)]
    if sub:
        log(f"- {bname}: R={score(preds, sub, True, kin).recall:.3f} "
            f"(gold n={len([g for g in sub if g.evaluable])})")

# ---------- fresh precision-audit sample, seed=41 ----------
SEED, QUOTA = 41, {"S1_safe": 15, "S2_bare": 25, "S3_crossdoc": 30, "S4_nonexact": 30}
seen, uniq_edges = set(), []
for p in preds:
    kk = (p.source_uid, p.target_uid)
    if kk not in seen:
        seen.add(kk)
        uniq_edges.append(p)

def stratum(e):
    src, tgt = corpus.by_uid[e.source_uid], corpus.by_uid[e.target_uid]
    if tgt.doc_id != src.doc_id:
        return "S3_crossdoc"
    if not e.keyword:
        return "S2_bare"
    return "S1_safe" if e.how == "exact" else "S4_nonexact"

groups = {s: [] for s in QUOTA}
for e in uniq_edges:
    groups[stratum(e)].append(e)
rng = random.Random(SEED)
sample = []
for s, q in QUOTA.items():
    pool = groups[s]
    rng.shuffle(pool)
    sample.extend((s, e) for e in pool[:q])

lines = [f"# TEST precision audit sample (seed={SEED})", "",
         "Population: " + ", ".join(f"{s}={len(groups[s])}" for s in QUOTA), ""]
recs = []
for i, (s, e) in enumerate(sample):
    src, tgt = corpus.by_uid[e.source_uid], corpus.by_uid[e.target_uid]
    text = clean(src.text)
    pos = text.find(e.mention)
    ctx = text[max(0, pos - 130): pos + len(e.mention) + 130].replace("\n", " ")
    lines += [f"## {i:03d} [{s}] `{e.mention}`  ({e.how or 'exact'})",
              f"- SRC {src.doc_id}:{src.passage_id}  →  TGT {tgt.doc_id}:{tgt.passage_id}",
              f"- CTX: …{ctx}…",
              f"- TGT TEXT: {clean(tgt.text)[:150].replace(chr(10),' ')}", ""]
    recs.append({"i": i, "stratum": s, "mention": e.mention, "how": e.how,
                 "source_uid": e.source_uid, "target_uid": e.target_uid,
                 "src": f"{src.doc_id}:{src.passage_id}",
                 "tgt": f"{tgt.doc_id}:{tgt.passage_id}", "label": None})

(ROOT / "reports" / "test_audit_sample.md").write_text("\n".join(lines) + "\n")
with open(ROOT / "data/processed/test_audit_sample.jsonl", "w") as f:
    for r in recs:
        f.write(json.dumps(r) + "\n")
log()
log(f"- Audit sample written: {sum(len(v) for v in (groups[s][:QUOTA[s]] for s in QUOTA))} "
    f"edges, population " + ", ".join(f"{s}={len(groups[s])}" for s in QUOTA))

(ROOT / "reports" / "step6_test_run.md").write_text("\n".join(out) + "\n")
