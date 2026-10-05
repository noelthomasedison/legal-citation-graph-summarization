"""Phase 3 — EUR-Lex extraction audit: precision sample + unresolved diagnostics.

We know the EU resolution RATE (51.9%) but not the PRECISION: of the edges we
built, how many point at the right passage? Phase 1 established that this
question can only be answered by manual adjudication (PLAN.md amendment 2), so
this mirrors that protocol exactly — stratified sample by resolution
provenance, fixed seed recorded before adjudication.

Produces TWO artefacts:

  A. RESOLVED sample (precision)  — N edges stratified by how they resolved:
       S1_exact     exact path match, keyworded  (safest)
       S2_bare      no keyword (bare number)     (riskiest)
       S3_suffix    matched on a path suffix
       S4_ascent    required leaf-ascent
     Each row shows the mention in context + the target text, so it can be
     judged without opening the corpus.

  B. UNRESOLVED diagnostics — the ~200k mentions that resolved to nothing.
     Grouped by surface shape, because WHY they failed tells us whether an
     EU-specific rule gap exists (Annex/roman-numeral Chapters are the
     suspected classes) and is free diagnostic data.

Fill the "label" field in the JSONL with TRUE / FALSE / UNSURE, then run
06_eurlex_audit_results.py. No LLM calls anywhere.
"""
import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from eurlex_ingest import load_eurlexsum          # noqa: E402
from eurlex_resolve import EuResolver             # noqa: E402
from regkg.textutil import clean                  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--limit", type=int, default=200, help="acts to sample from")
ap.add_argument("--n", type=int, default=100, help="edges to audit")
ap.add_argument("--seed", type=int, default=41)
args = ap.parse_args()

QUOTA = {"S1_exact": 25, "S2_bare": 25, "S3_suffix": 25, "S4_ascent": 25}

# NB: load_eurlexsum(limit=...) now draws a SEEDED RANDOM sample. Taking
# sorted(celex)[:N] returned all 150 international agreements before any
# legislation, which made the 2026-08-10 audit unrepresentative (agreements are
# 11% of the corpus but were 75% of that sample).
print(f"loading {args.limit} acts (random sample, seed {args.seed})...", flush=True)
corpus, id2celex, celex2id = load_eurlexsum(limit=args.limit, seed=args.seed)
never = re.compile(r"(?!x)x")
res = EuResolver(corpus=corpus, aliases={}, alias_re=never,
                 use_guards=True, use_aliases=False, use_fsmr=False,
                 use_tolerant=True, use_attribution=True,
                 celex2id=celex2id)
print("resolving (EU guard on)...", flush=True)
edges = res.run(corpus.passages)
print(f"  {len(edges):,} edges | {res.n_unresolved:,} unresolved", flush=True)

# ---------------- A. resolved sample ----------------
def stratum(e):
    how = e.how or "exact"
    if "ascent" in how:
        return "S4_ascent"
    if "suffix" in how:
        return "S3_suffix"
    if not e.keyword:
        return "S2_bare"
    return "S1_exact"

seen, uniq = set(), []
for e in edges:
    k = (e.source_uid, e.target_uid)
    if k not in seen and e.source_uid != e.target_uid:
        seen.add(k)
        uniq.append(e)

groups = {s: [] for s in QUOTA}
for e in uniq:
    groups[stratum(e)].append(e)
rng = random.Random(args.seed)
sample = []
for s, q in QUOTA.items():
    pool = groups[s]
    rng.shuffle(pool)
    sample.extend((s, e) for e in pool[:q])

lines = [f"# EUR-Lex extraction audit sample (seed={args.seed})", "",
         f"Population by stratum: "
         + ", ".join(f"{s}={len(groups[s])}" for s in QUOTA), "",
         "Judge each: does the reference in CTX genuinely point at TGT TEXT?",
         "Mark TRUE / FALSE / UNSURE in the matching row of the .jsonl.", ""]
recs = []
for i, (s, e) in enumerate(sample):
    src, tgt = corpus.by_uid[e.source_uid], corpus.by_uid[e.target_uid]
    text = clean(src.text)
    pos = text.find(e.mention)
    ctx = text[max(0, pos - 150): pos + len(e.mention) + 150].replace("\n", " ")
    lines += [f"## {i:03d} [{s}] `{e.mention}`  ({e.how or 'exact'})",
              f"- ACT {id2celex[src.doc_id]}",
              f"- SRC Article-path {src.passage_id}  ->  TGT {tgt.passage_id}",
              f"- CTX: ...{ctx}...",
              f"- TGT TEXT: {clean(tgt.text)[:220].replace(chr(10),' ')}", ""]
    recs.append({"i": i, "stratum": s, "mention": e.mention,
                 "how": e.how or "exact", "celex": id2celex[src.doc_id],
                 "src": src.passage_id, "tgt": tgt.passage_id,
                 "source_uid": e.source_uid, "target_uid": e.target_uid,
                 "label": None})

(ROOT / "reports").mkdir(exist_ok=True)
(ROOT / "reports" / "eurlex_audit_sample.md").write_text("\n".join(lines) + "\n")
(ROOT / "data").mkdir(exist_ok=True)
with open(ROOT / "data" / "eurlex_audit_sample.jsonl", "w") as f:
    for r in recs:
        f.write(json.dumps(r) + "\n")

# ---------------- B. unresolved diagnostics ----------------
def shape(m):
    """Collapse a mention to its surface shape so failures group together."""
    t = m.strip()
    t = re.sub(r"\d+", "N", t)
    t = re.sub(r"\b[ivxlIVXL]{2,}\b", "ROMAN", t)
    t = re.sub(r"\s+", " ", t)
    return t[:60]

shapes = Counter(shape(m.split("`")[1] if "`" in m else m)
                 for m in res.unresolved_samples)
D = ["# EUR-Lex unresolved-mention diagnostics", "",
     f"Of {len(edges)+res.n_unresolved:,} detected mentions, "
     f"**{res.n_unresolved:,} resolved to nothing** "
     f"({100*res.n_unresolved/max(len(edges)+res.n_unresolved,1):.1f}%).",
     "",
     f"Sample of {len(res.unresolved_samples)} failures, grouped by surface "
     "shape. A shape appearing often is a candidate RULE GAP; a shape that is "
     "genuinely out-of-corpus (citing an act we do not hold) is correct "
     "behaviour, not a defect.", "",
     "| count | mention shape |", "|---|---|"]
for sh, n in shapes.most_common(40):
    D.append(f"| {n} | `{sh}` |")
D += ["", "## How to read", "",
      "- **Correct failures:** references to acts outside the corpus, or to",
      "  Annexes/instruments we deliberately do not model. Leaving these",
      "  unresolved is the precision-preserving choice (the resolver refuses",
      "  to guess), exactly as designed in Phase 1.",
      "- **Rule gaps:** recurring EU-specific forms the ADGM grammar never",
      "  saw. Suspected classes: `Annex ROMAN`, `Chapter ROMAN`, nested",
      "  inverted forms. These are the only ones worth adapting rules for.",
      "- Decide adaptation ONLY from this table plus the precision audit —",
      "  not from the resolution rate alone.",
      ]
(ROOT / "reports" / "eurlex_unresolved.md").write_text("\n".join(D) + "\n")

print(f"\nwrote reports/eurlex_audit_sample.md ({len(recs)} edges to judge)")
print(f"      data/eurlex_audit_sample.jsonl  <- put TRUE/FALSE/UNSURE here")
print(f"      reports/eurlex_unresolved.md")
print("\nPopulation by stratum: "
      + ", ".join(f"{s}={len(groups[s])}" for s in QUOTA))
