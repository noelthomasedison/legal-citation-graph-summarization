"""Verify that BATCHING the RePASs obligation-coverage step changes nothing.

The Phase-2 scorer calls deberta-large-mnli one sentence pair at a time inside
a nested Python loop. That was tolerable for short QA answers; on summaries it
costs ~5.5 min/act (~7h for 80 acts). Batching should be ~10-30x faster.

Batching is mathematically identical in principle — each [premise] [SEP]
[hypothesis] pair is classified independently, so one item's logits do not
depend on its batch-mates. But three things can break that: wrong attention
masks letting padding leak in, float noise from different reduction orders
(~1e-6, only matters if a score sits exactly on the 0.7 threshold), and
inconsistent truncation.

So this does not assume; it MEASURES. Same pairs, both code paths, compared.
Run before trusting any batched rescore.
"""
import sys
from pathlib import Path

import numpy as np
import torch
from transformers import pipeline

ROOT = Path(__file__).resolve().parents[1]
DEV = "mps" if torch.backends.mps.is_available() else "cpu"
THR = 0.7                       # the decision threshold the scorer uses

print("loading deberta-large-mnli...", flush=True)
cov = pipeline("text-classification", model="microsoft/deberta-large-mnli",
               device=DEV)

# realistic pairs: obligation-style legal sentences of varied length, because
# padding effects only show up when lengths differ within a batch
ANS = [
    "Member States shall ensure that competent authorities have the necessary "
    "supervisory powers to carry out their duties.",
    "The Commission shall adopt implementing acts.",
    "Providers must publish an annual transparency report describing the "
    "measures taken to detect and remove illegal content, including the "
    "resources allocated and the accuracy of automated tools.",
    "This Regulation applies from 1 January 2024.",
    "Operators are required to notify the competent authority without undue "
    "delay and in any event within 72 hours.",
]
SRC = [
    "Competent authorities shall be granted supervisory and investigatory powers.",
    "The Commission is empowered to adopt delegated acts in accordance with "
    "Article 12 concerning the criteria for assessing systemic risk.",
    "Providers of intermediary services shall make publicly available, at least "
    "once a year, clear and easily comprehensible reports on any content "
    "moderation they engaged in during the relevant period.",
    "Member States shall not impose a general obligation to monitor.",
]
pairs = [f"{a} [SEP] {o}" for a in ANS for o in SRC]
print(f"comparing {len(pairs)} pairs\n")

# ---- path 1: one at a time (what the current scorer does) ----
one = []
for p in pairs:
    r = cov(p, truncation=True)[0]
    one.append((r["label"].lower(), float(r["score"])))

# ---- path 2: batched ----
res = cov(pairs, truncation=True, batch_size=16)
bat = [(r["label"].lower(), float(r["score"])) for r in res]

# ---- compare ----
lab_mismatch = [i for i in range(len(pairs)) if one[i][0] != bat[i][0]]
diffs = np.array([abs(one[i][1] - bat[i][1]) for i in range(len(pairs))])
# the value that actually matters: the scorer's decision
def decide(x):
    return x[0] == "entailment" and x[1] > THR
dec_mismatch = [i for i in range(len(pairs)) if decide(one[i]) != decide(bat[i])]

print(f"label mismatches            : {len(lab_mismatch)}/{len(pairs)}")
print(f"max abs score difference    : {diffs.max():.3e}")
print(f"mean abs score difference   : {diffs.mean():.3e}")
print(f"DECISION mismatches (>{THR}) : {len(dec_mismatch)}/{len(pairs)}")
print()
if not dec_mismatch and diffs.max() < 1e-3:
    print("VERDICT: batching is SAFE — identical decisions, differences at "
          "float-noise level.")
else:
    print("VERDICT: DO NOT BATCH — decisions differ. Investigate padding / "
          "attention masks before rescoring.")
    for i in dec_mismatch[:5]:
        print(f"  pair {i}: single={one[i]} batched={bat[i]}")
