"""End-to-end check: does BATCHING change the RePASs numbers we would report?

09_verify_batching proved the deberta classifier gives identical DECISIONS
when batched. That is a component test. This is the end-to-end one: run the
FULL RePASs computation on real acts, both ways, and compare the actual
reported values (repass, es, cs, oc) condition by condition.

Only the obligation-coverage loop differs between the two paths; entailment /
contradiction NLI is already batched and shared, so any discrepancy isolates
to the change under test.

Proceed with batching ONLY if every value matches to <1e-4.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import torch
from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                          pipeline)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from eurlex_ingest import load_eurlexsum          # noqa: E402
from regkg.textutil import clean                  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--acts", type=int, default=3)
ap.add_argument("--split", default="test")
args = ap.parse_args()

DEV = "mps" if torch.backends.mps.is_available() else "cpu"
CONDS = ("base", "A", "B", "oracle")
THR = 0.7
_SENT = re.compile(r"(?<=[.;:])\s+|\n+")
def sentences(t):
    return [s.strip() for s in _SENT.split(t or "") if len(s.strip().split()) >= 8]

print("loading models...", flush=True)
nli_tok = AutoTokenizer.from_pretrained("cross-encoder/nli-deberta-v3-xsmall")
nli = AutoModelForSequenceClassification.from_pretrained(
    "cross-encoder/nli-deberta-v3-xsmall").to(DEV).eval()
cov = pipeline("text-classification", model="microsoft/deberta-large-mnli",
               device=DEV)
obl_dir = str(ROOT.parent / "phase2" / "models" / "obligation-classifier-legalbert")
obl_tok = AutoTokenizer.from_pretrained(obl_dir)
obl = AutoModelForSequenceClassification.from_pretrained(obl_dir).to(DEV).eval()

@torch.no_grad()
def nli_probs(prem, hyp):
    enc = nli_tok(prem, hyp, padding=True, truncation=True, max_length=256,
                  return_tensors="pt").to(DEV)
    return torch.softmax(nli(**enc).logits, -1).cpu().numpy()

@torch.no_grad()
def is_obl(ss):
    if not ss:
        return []
    enc = obl_tok(ss, padding=True, truncation=True, max_length=128,
                  return_tensors="pt").to(DEV)
    return obl(**enc).logits.argmax(-1).cpu().numpy()

def coverage_single(osrc, oans):
    """ORIGINAL: one classifier call per pair, break on first match."""
    covered = 0
    for o in osrc:
        for a in oans:
            r = cov(f"{a} [SEP] {o}", truncation=True)[0]
            if r["label"].lower() == "entailment" and r["score"] > THR:
                covered += 1
                break
    return covered / len(osrc) if osrc else 0.0

def coverage_batched(osrc, oans):
    """BATCHED: same decisions, computed in one pass.

    The original breaks out of the inner loop on the first match, so it may
    evaluate FEWER pairs. Batching evaluates the full cross-product and then
    applies the same 'any match' rule — identical result, more pairs scored.
    """
    if not osrc or not oans:
        return 0.0
    pairs = [f"{a} [SEP] {o}" for o in osrc for a in oans]
    res = cov(pairs, truncation=True, batch_size=32)
    hit = np.array([r["label"].lower() == "entailment" and r["score"] > THR
                    for r in res]).reshape(len(osrc), len(oans))
    return float(hit.any(axis=1).mean())

def repass(pool_sents, answer, batched):
    ps = pool_sents[:60]
    as_ = sentences(answer)[:20]
    if not ps or not as_:
        return dict(repass=1/3, es=0.0, cs=0.0, oc=0.0)
    E = np.zeros((len(ps), len(as_))); C = np.zeros((len(ps), len(as_)))
    for i, pp in enumerate(ps):
        pr = nli_probs([pp] * len(as_), as_)
        C[i], E[i] = pr[:, 0], pr[:, 1]
    es = float(np.mean(np.max(E, 0))); cs = float(np.mean(np.max(C, 0)))
    osrc = [s for s, l in zip(ps, is_obl(ps)) if l == 1]
    oans = [s for s, l in zip(as_, is_obl(as_)) if l == 1]
    oc = coverage_batched(osrc, oans) if batched else coverage_single(osrc, oans)
    return dict(repass=round((oc + es - cs + 1) / 3, 5), es=round(es, 5),
                cs=round(cs, 5), oc=round(oc, 5))

# ---- data ----
gen = {}
for l in open(ROOT / "data" / f"summaries_{args.split}.jsonl"):
    r = json.loads(l)
    gen.setdefault(r["celex"], {})[r["cond"]] = r["summary"]
align = json.load(open(ROOT / "data" / f"align_{args.split}.json"))
acts = [c for c in sorted(gen) if len(gen[c]) == 4 and c in align][: args.acts]
print(f"checking {len(acts)} acts x {len(CONDS)} conditions\n", flush=True)

corpus, id2celex, celex2id = load_eurlexsum()

import time
rows, t_single, t_batch = [], 0.0, 0.0
for cx in acts:
    a = align[cx]
    pool = []
    for u in (a["base_uids"] + a["a_add_uids"] + a["b_add_uids"] + a["oracle_uids"]):
        if u in corpus.by_uid:
            pool.extend(sentences(clean(corpus.by_uid[u].text)))
    for cond in CONDS:
        t0 = time.time(); s = repass(pool, gen[cx][cond], batched=False)
        t_single += time.time() - t0
        t0 = time.time(); b = repass(pool, gen[cx][cond], batched=True)
        t_batch += time.time() - t0
        rows.append((cx, cond, s, b))
        print(f"  {cx} {cond:<7} single repass={s['repass']:.5f}  "
              f"batched={b['repass']:.5f}  diff={abs(s['repass']-b['repass']):.2e}",
              flush=True)

print("\n=== comparison ===")
worst = 0.0
bad = []
for cx, cond, s, b in rows:
    for k in ("repass", "es", "cs", "oc"):
        d = abs(s[k] - b[k])
        worst = max(worst, d)
        if d > 1e-4:
            bad.append((cx, cond, k, s[k], b[k], d))
print(f"comparisons: {len(rows)*4} values across {len(rows)} act-condition pairs")
print(f"max abs difference: {worst:.3e}")
print(f"speedup: {t_single/max(t_batch,1e-9):.1f}x  "
      f"(single {t_single/60:.1f} min, batched {t_batch/60:.1f} min)")
if not bad:
    print("\nVERDICT: SAFE — every reported value matches to <1e-4. "
          "Batched rescore will reproduce the unbatched numbers.")
else:
    print(f"\nVERDICT: DO NOT BATCH — {len(bad)} values differ:")
    for r in bad[:10]:
        print("  ", r)
