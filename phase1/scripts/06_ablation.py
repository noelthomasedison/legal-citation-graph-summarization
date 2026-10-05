"""The ablation ladder: add one component per rung, re-score the dev set.

Rungs (cumulative):
  R1 core grammar only          R4 + FSMR fallback
  R2 + precision guards         R5 + suffix / leaf-ascent
  R3 + alias table              R6 + deepest-container attribution (= full)

Plus the graph-scope view (dissertation A/B): at full config, split predicted
edges into variant A (same-document) vs variant B extras (cross-document) and
score each against the matching gold slice.

Writes reports/step4_ablation.md.
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
from regkg.evaluate import score, build_source_kin        # noqa: E402

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
alias_re = alias_pattern(aliases)
dev_passages = [p for p in corpus.passages if p.doc_id in dev]
dev_gold = [g for g in gold if g.source_doc in dev]
kin = build_source_kin(dev_gold, corpus)
gold_int = [g for g in dev_gold if g.ref_type == "Internal"]
gold_ext = [g for g in dev_gold if g.ref_type == "External"]

RUNGS = [
    ("R1 core grammar",       dict(use_guards=False, use_aliases=False, use_fsmr=False,
                                   use_tolerant=False, use_attribution=False)),
    ("R2 + guards",           dict(use_guards=True,  use_aliases=False, use_fsmr=False,
                                   use_tolerant=False, use_attribution=False)),
    ("R3 + alias table",      dict(use_guards=True,  use_aliases=True,  use_fsmr=False,
                                   use_tolerant=False, use_attribution=False)),
    ("R4 + FSMR fallback",    dict(use_guards=True,  use_aliases=True,  use_fsmr=True,
                                   use_tolerant=False, use_attribution=False)),
    ("R5 + suffix/ascent",    dict(use_guards=True,  use_aliases=True,  use_fsmr=True,
                                   use_tolerant=True,  use_attribution=False)),
    ("R6 + attribution (full)", dict()),                       # all defaults True
]

log("# Step 4 — ablation ladder (dev set, nested + source-nested credit)")
log()
log("| Rung | Pred edges | R all | R int | R ext | Unresolved | Ambiguous |")
log("|---|---|---|---|---|---|---|")
full_preds = None
for name, flags in RUNGS:
    r = Resolver(corpus, aliases, alias_re, **flags)
    preds = r.run(dev_passages)
    uniq = {(p.source_uid, p.target_uid) for p in preds}
    s_all = score(preds, dev_gold, nested=True, source_kin=kin)
    s_int = score(preds, gold_int, nested=True, source_kin=kin)
    s_ext = score(preds, gold_ext, nested=True, source_kin=kin)
    log(f"| {name} | {len(uniq):,} | {s_all.recall:.3f} | {s_int.recall:.3f} "
        f"| {s_ext.recall:.3f} | {r.n_unresolved:,} | {r.n_ambiguous:,} |")
    if name.startswith("R6"):
        full_preds = preds

# ---------- leave-one-out: true marginal contribution of each component ----
# The additive ladder understates components whose value is unlocked by later
# ones (FSMR fallback needs suffix lookup to pay off). LOO = full system minus
# one component, so interactions are already in place.
log()
log("## Leave-one-out (full system minus one component)")
log()
log("| Removed | Pred edges | R all | R int | R ext |")
log("|---|---|---|---|---|")
LOO = [("(nothing — full)", {}),
       ("guards",      dict(use_guards=False)),
       ("alias table", dict(use_aliases=False)),
       ("FSMR fallback", dict(use_fsmr=False)),
       ("suffix/ascent", dict(use_tolerant=False)),
       ("attribution", dict(use_attribution=False))]
for name, flags in LOO:
    r = Resolver(corpus, aliases, alias_re, **flags)
    preds = r.run(dev_passages)
    uniq = {(p.source_uid, p.target_uid) for p in preds}
    s_all = score(preds, dev_gold, nested=True, source_kin=kin)
    s_int = score(preds, gold_int, nested=True, source_kin=kin)
    s_ext = score(preds, gold_ext, nested=True, source_kin=kin)
    log(f"| − {name} | {len(uniq):,} | {s_all.recall:.3f} | {s_int.recall:.3f} "
        f"| {s_ext.recall:.3f} |")

# ---------- graph-scope view (dissertation A/B) ----------
log()
log("## Graph-scope view at full config (variant A vs B)")
doc_of = {p.uid: p.doc_id for p in corpus.passages}
uniq = list({(p.source_uid, p.target_uid): p for p in full_preds}.values())
var_a = [p for p in uniq if doc_of[p.source_uid] == doc_of[p.target_uid]]
var_b_extra = [p for p in uniq if doc_of[p.source_uid] != doc_of[p.target_uid]]
log(f"- Variant A (internal-only KG): {len(var_a):,} edges "
    f"-> recall vs internal gold: {score(var_a, gold_int, True, kin).recall:.3f}")
log(f"- Variant B adds {len(var_b_extra):,} cross-document edges "
    f"-> recall vs external gold: {score(var_b_extra, gold_ext, True, kin).recall:.3f}")
log(f"- B/A edge ratio: {len(var_b_extra)/max(len(var_a),1):.2f} extra edges per internal edge")
log()
log("Reading: rungs 1-2 are, in effect, the internal-only world; rungs 3-5 are")
log("the cross-document machinery. The A/B split above is the same story at the")
log("graph level — it is what Phases 2-3 will consume as variants A and B.")

(ROOT / "reports" / "step4_ablation.md").write_text("\n".join(out) + "\n")
