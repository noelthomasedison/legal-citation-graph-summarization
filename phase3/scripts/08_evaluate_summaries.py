"""Phase 3 — evaluate base / variant A / variant B / oracle summaries.

Four metric families, because no single one can carry this:

  ROUGE-1/2/L   content overlap with the official EU summary. Comparable to the
                EUR-Lex-Sum paper's own baselines. PRECISION also catches
                contamination — variant B importing material about a CITED act
                that does not belong in a summary of the focal act.
  BERTScore     catches paraphrase ROUGE misses. Runs high and compresses
                differences on same-domain legal text, so only the PAIRED
                difference means anything.
  RePASs        faithfulness: entailment support, contradiction, obligation
                coverage. Scored against a source pool held IDENTICAL across
                all four conditions — otherwise base is judged against less
                evidence than B and the comparison is rigged.
  TARGETED      the actual hypothesis test. From the alignment we already know
                which gold-summary sentences the base budget MISSES and which
                variant A or B could supply. Measure coverage of exactly those
                sentences. Aggregate ROUGE would drown a ~2% effect, exactly as
                aggregate RePASs drowned the CUAD effect until the rescue arm
                isolated it.

Paired stats per act: Wilcoxon signed-rank + bootstrap CI resampled by act.
--fast skips RePASs (the slow part) so ROUGE/BERTScore/targeted land first.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from huggingface_hub import hf_hub_download           # noqa: E402
from regkg.textutil import clean                      # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--fast", action="store_true", help="skip RePASs")
ap.add_argument("--thr", type=float, default=0.60)
args = ap.parse_args()

CONDS = ("base", "A", "B", "oracle")
_SENT = re.compile(r"(?<=[.;:])\s+|\n+")
def sentences(t):
    return [s.strip() for s in _SENT.split(t or "") if len(s.strip().split()) >= 8]

# ---------------- load ----------------
gen = defaultdict(dict)
for l in open(ROOT / "data" / f"summaries_{args.split}.jsonl"):
    r = json.loads(l)
    gen[r["celex"]][r["cond"]] = r["summary"]
complete = {c: v for c, v in gen.items() if len(v) == 4}
print(f"complete quadruples: {len(complete)}/{len(gen)}")

align = json.load(open(ROOT / "data" / f"align_{args.split}.json"))
p = hf_hub_download("dennlinger/eur-lex-sum", f"data/english/{args.split}.json",
                    repo_type="dataset")
gold = {}
for line in open(p):
    if line.strip():
        r = json.loads(line)
        gold[r["celex_id"]] = clean(r["summary"])
acts = sorted(c for c in complete if c in gold and c in align)
print(f"scorable acts: {len(acts)}")

per = {c: {} for c in CONDS}          # cond -> celex -> {metric: value}

# ---------------- ROUGE ----------------
from rouge_score import rouge_scorer
rs = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
print("scoring ROUGE...", flush=True)
for cx in acts:
    for cond in CONDS:
        sc = rs.score(gold[cx], complete[cx][cond])
        per[cond][cx] = {f"{k}_f": v.fmeasure for k, v in sc.items()}
        per[cond][cx]["rouge1_p"] = sc["rouge1"].precision   # contamination signal

# ---------------- targeted: rescued-sentence coverage ----------------
print("scoring TARGETED (rescued-sentence coverage)...", flush=True)
from sentence_transformers import SentenceTransformer
_DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
sbert = SentenceTransformer("BAAI/bge-small-en-v1.5", device=_DEVICE)
QP = "Represent this sentence for searching relevant passages: "
for cx in acts:
    a = align[cx]
    gsents = a["summary_sentences"]
    idx_a = set(a["rescue_a_idx"]); idx_b = set(a["rescue_b_idx"])
    tgt = sorted(idx_a | idx_b)
    if not tgt:
        for cond in CONDS:
            per[cond][cx]["targeted"] = np.nan
        continue
    G = sbert.encode([QP + gsents[i] for i in tgt], normalize_embeddings=True,
                     show_progress_bar=False)
    for cond in CONDS:
        gs = sentences(complete[cx][cond])
        if not gs:
            per[cond][cx]["targeted"] = 0.0
            continue
        S = sbert.encode(gs, normalize_embeddings=True, show_progress_bar=False)
        cov = (G @ S.T).max(axis=1)
        per[cond][cx]["targeted"] = float((cov >= args.thr).mean())

# ---------------- BERTScore ----------------
print("scoring BERTScore...", flush=True)
import torch
from bert_score import score as bscore
dev = "mps" if torch.backends.mps.is_available() else "cpu"
for cond in CONDS:
    P, R, F = bscore([complete[cx][cond] for cx in acts], [gold[cx] for cx in acts],
                     lang="en", verbose=False, device=dev, batch_size=8)
    for i, cx in enumerate(acts):
        per[cond][cx]["bertscore_f"] = float(F[i])

# ---------------- RePASs ----------------
if not args.fast:
    print("scoring RePASs (slow)...", flush=True)
    from transformers import (AutoModelForSequenceClassification, AutoTokenizer,
                              pipeline)
    from eurlex_ingest import load_eurlexsum
    corpus, id2celex, celex2id = load_eurlexsum()
    nli_tok = AutoTokenizer.from_pretrained("cross-encoder/nli-deberta-v3-xsmall")
    nli = AutoModelForSequenceClassification.from_pretrained(
        "cross-encoder/nli-deberta-v3-xsmall").to(dev).eval()
    cov_pipe = pipeline("text-classification",
                        model="microsoft/deberta-large-mnli", device=dev)
    obl_dir = str(ROOT.parent / "phase2" / "models" / "obligation-classifier-legalbert")
    obl_tok = AutoTokenizer.from_pretrained(obl_dir)
    obl = AutoModelForSequenceClassification.from_pretrained(obl_dir).to(dev).eval()

    @torch.no_grad()
    def nli_probs(prem, hyp):
        enc = nli_tok(prem, hyp, padding=True, truncation=True, max_length=256,
                      return_tensors="pt").to(dev)
        return torch.softmax(nli(**enc).logits, -1).cpu().numpy()

    @torch.no_grad()
    def is_obl(ss):
        if not ss:
            return []
        enc = obl_tok(ss, padding=True, truncation=True, max_length=128,
                      return_tensors="pt").to(dev)
        return obl(**enc).logits.argmax(-1).cpu().numpy()

    def repass(pool_sents, answer):
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
        covered = 0
        for o in osrc:
            for aa in oans:
                r = cov_pipe(f"{aa} [SEP] {o}", truncation=True)[0]
                if r["label"].lower() == "entailment" and r["score"] > 0.7:
                    covered += 1; break
        oc = covered / len(osrc) if osrc else 0.0
        return dict(repass=round((oc + es - cs + 1) / 3, 5), es=round(es, 5),
                    cs=round(cs, 5), oc=round(oc, 5))

    for n, cx in enumerate(acts):
        a = align[cx]
        # IDENTICAL pool for every condition: base + every passage any variant
        # could have added. Judging base against a smaller pool would rig it.
        pool_uids = (a["base_uids"] + a["a_add_uids"] + a["b_add_uids"]
                     + a["oracle_uids"])
        pool = []
        for u in pool_uids:
            if u in corpus.by_uid:
                pool.extend(sentences(clean(corpus.by_uid[u].text)))
        for cond in CONDS:
            per[cond][cx].update(repass(pool, complete[cx][cond]))
        if (n + 1) % 10 == 0:
            print(f"  RePASs {n+1}/{len(acts)}", flush=True)

# ---------------- aggregate + paired stats ----------------
METRICS = ["rouge1_f", "rouge2_f", "rougeL_f", "rouge1_p", "bertscore_f", "targeted"]
if not args.fast:
    METRICS += ["repass", "es", "cs", "oc"]

def col(cond, m):
    return np.array([per[cond][cx].get(m, np.nan) for cx in acts], dtype=float)

try:
    from scipy.stats import wilcoxon
except ImportError:
    wilcoxon = None

def paired(hi, lo, m):
    a, b = col(hi, m), col(lo, m)
    ok = ~(np.isnan(a) | np.isnan(b))
    d = a[ok] - b[ok]
    if len(d) < 5 or np.allclose(d, 0):
        return None
    rng = np.random.default_rng(41)
    boot = [rng.choice(d, len(d), replace=True).mean() for _ in range(5000)]
    lo_ci, hi_ci = np.percentile(boot, [2.5, 97.5])
    p = wilcoxon(d).pvalue if wilcoxon is not None and np.any(d != 0) else float("nan")
    return dict(n=len(d), mean=float(d.mean()), lo=float(lo_ci), hi=float(hi_ci),
                p=float(p), wins=int((d > 0).sum()), losses=int((d < 0).sum()))

L = ["# Phase 3 — summarisation results (base / variant A / variant B / oracle)", "",
     f"EUR-Lex-Sum `{args.split}` split, **{len(acts)} acts**, equal context",
     "budget across all four conditions, single-pass generation (see",
     "SUMMARISER_PLAN.md §2b for deviations). llama-3.3-70b, temperature 0.", "",
     "## Means", "", "| metric | base | variant A | variant B | oracle |",
     "|---|---|---|---|---|"]
for m in METRICS:
    vals = [np.nanmean(col(c, m)) for c in CONDS]
    L.append(f"| {m} | " + " | ".join(f"{v:.4f}" for v in vals) + " |")

L += ["", "## Paired contrasts", "",
      "`A-base` = value of within-document references · `B-A` = value of",
      "cross-document references (the supervisor's central question) ·",
      "`oracle-B` = remaining headroom.", "",
      "| contrast | metric | n | mean d | 95% CI | Wilcoxon p | win/loss |",
      "|---|---|---|---|---|---|---|"]
for hi, lo in (("A", "base"), ("B", "A"), ("B", "base"), ("oracle", "B"),
               ("oracle", "base")):
    for m in ("targeted", "rougeL_f", "bertscore_f") + (
            () if args.fast else ("repass",)):
        r = paired(hi, lo, m)
        if r:
            L.append(f"| {hi}-{lo} | {m} | {r['n']} | {r['mean']:+.4f} | "
                     f"[{r['lo']:+.4f}, {r['hi']:+.4f}] | {r['p']:.3g} | "
                     f"{r['wins']}/{r['losses']} |")

L += ["", "## How to read", "",
      "**`targeted` is the hypothesis test.** It measures coverage of exactly",
      "the gold-summary sentences the base budget misses and a variant could",
      "supply — the only place a ~2%-of-content effect can show. Aggregate",
      "ROUGE/BERTScore are expected to be NULL (pre-registered as H3); a null",
      "there is a property of the effect size, not a failure of the method.", "",
      "**`rouge1_p` (precision) is the contamination check.** If variant B",
      "imports material about a cited act that does not belong in a summary of",
      "the focal act, precision falls even if recall does not.", "",
      "**RePASs uses a pool identical across conditions** (base + every passage",
      "any variant could add), so no condition is judged against more evidence",
      "than another.",
      ]
(ROOT / "reports").mkdir(exist_ok=True)
name = f"summarisation_results{'_fast' if args.fast else ''}.md"
(ROOT / "reports" / name).write_text("\n".join(L) + "\n")
json.dump({c: per[c] for c in CONDS},
          open(ROOT / "data" / f"eval_{args.split}.json", "w"))
print("\n".join(L[5:]))
print(f"\nwrote reports/{name}")
