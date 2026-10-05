"""Step 3: run the rule-based extractor on DEV docs and score against dev gold.

Writes reports/step3_rules_dev.md. Test docs are not touched.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from regkg.ingest import load_corpus                      # noqa: E402
from regkg.gold import load_gold                          # noqa: E402
from regkg.docmap import load_aliases, alias_pattern      # noqa: E402
from regkg.resolve import Resolver                        # noqa: E402
from regkg.evaluate import (score, unmatched_gold, false_positives,  # noqa: E402
                            build_source_kin)

RAW = ROOT / "data" / "raw" / "GraphRAG4RegGraph"
out = []
def log(line=""):
    out.append(line)
    print(line)

corpus = load_corpus(RAW / "StructuredDocuments" / "Json")
gold = load_gold(RAW / "CrossReferenceData.csv", corpus)
split = json.loads((ROOT / "data/processed/splits.json").read_text())
dev = set(split["dev_docs"])

aliases = load_aliases(RAW / "DocumentMap.rtf")
resolver = Resolver(corpus, aliases, alias_pattern(aliases))

dev_passages = [p for p in corpus.passages if p.doc_id in dev]
preds = resolver.run(dev_passages)
dev_gold = [g for g in gold if g.source_doc in dev]

log("# Step 3 — rule extractor, DEV scores")
log()
log(f"- Dev passages: {len(dev_passages):,} | predicted edges: "
    f"{len({(p.source_uid,p.target_uid) for p in preds}):,}")
log(f"- Resolver: unresolved mentions={resolver.n_unresolved:,}, "
    f"ambiguous-suffix drops={resolver.n_ambiguous:,}")
log()
kin = build_source_kin(dev_gold, corpus)
for name, nested, k in [("NESTED credit", True, None),
                        ("EXACT only", False, None),
                        ("NESTED + source-nested credit", True, kin)]:
    log(f"## {name}")
    log(f"- ALL:      {score(preds, dev_gold, nested, k).row()}")
    for rt in ("Internal", "External"):
        sub = [g for g in dev_gold if g.ref_type == rt]
        log(f"- {rt:9s} {score(preds, sub, nested, k).row()}   (recall-oriented)")
    log()

# ---------- error pools ----------
fns = unmatched_gold(preds, dev_gold)
fps = false_positives(preds, dev_gold)
log(f"## Error pools (dev)")
log(f"- False negatives (gold not covered): {len(fns)}")
for g in fns[:12]:
    log(f"    - [{g.ref_type}] src doc {g.source_doc}, ref `{g.ref_text[:60]}` "
        f"-> {g.target_doc}:{'.'.join(g.target_path or ())}")
log(f"- False positives (no gold match — may include gold-curation misses): {len(fps)}")
for p in fps[:12]:
    src = corpus.by_uid[p.source_uid]
    tgt = corpus.by_uid[p.target_uid]
    log(f"    - doc {src.doc_id} `{p.mention[:40]}` -> "
        f"{tgt.doc_id}:{tgt.passage_id[:30]}")

(ROOT / "reports" / "step3_rules_dev.md").write_text("\n".join(out) + "\n")
