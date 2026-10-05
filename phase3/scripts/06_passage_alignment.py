"""Phase 3 — passage-level alignment: oracle targets + rescueable sentences.

The G2 gate asked a DOCUMENT-level question ("does this summary sentence match
the focal act or a cited act"). The experiment needs PASSAGE-level answers:

  ORACLE      which specific passages of the act does the gold summary draw on?
              -> the oracle condition's context
  RESCUEABLE  which gold-summary sentences does a BUDGETED base selection miss,
              but a reference-closure step (variant A or B) would supply?
              -> the targeted metric, where a 5-9% effect can actually show
              (aggregate ROUGE would drown it, exactly as aggregate RePASs
              drowned the CUAD effect until the rescue arm isolated it)

Selection depends only on retrieval ranks and graph structure, both fixed
BEFORE any generation — never on model output.

No LLM calls. Writes data/align_<split>.json + reports/passage_alignment.md.
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

import torch  # noqa: E402
from sentence_transformers import SentenceTransformer   # noqa: E402
_DEVICE = \"mps\" if torch.backends.mps.is_available() else \"cpu\"
from huggingface_hub import hf_hub_download             # noqa: E402
from eurlex_ingest import load_eurlexsum                # noqa: E402
from regkg.textutil import clean                        # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--n", type=int, default=80, help="acts to prepare")
ap.add_argument("--budget", type=int, default=12, help="passages base may read")
ap.add_argument("--frontier", type=int, default=50,
                help="passages whose citations we FOLLOW (>= budget). Following "
                     "citations only from the 12 passages in context found "
                     "cross-document material in just 16/80 acts; widening the "
                     "frontier is the CUAD rescue-arm fix — selection still "
                     "conditions only on ranks and graph structure.")
ap.add_argument("--thr", type=float, default=0.60)
ap.add_argument("--seed", type=int, default=41)
args = ap.parse_args()

QPREFIX = "Represent this sentence for searching relevant passages: "
_SENT = re.compile(r"(?<=[.;:])\s+|\n+")
def sentences(t):
    return [s.strip() for s in _SENT.split(t or "") if len(s.strip().split()) >= 8]

# ---- corpus (whole thing: variant B needs cited acts present) ----
print("loading corpus + graph...", flush=True)
corpus, id2celex, celex2id = load_eurlexsum()
edges = [json.loads(l) for l in open(ROOT / "data" / "eurlex_edges.jsonl")]
outn = defaultdict(list)
for e in edges:
    if e["src"] != e["tgt"]:
        outn[e["src"]].append(e["tgt"])
print(f"  {len(corpus.passages):,} passages | {len(edges):,} edges", flush=True)

# ---- summaries for the chosen split ----
p = hf_hub_download("dennlinger/eur-lex-sum", f"data/english/{args.split}.json",
                    repo_type="dataset")
summaries = {}
for line in open(p):
    if line.strip():
        r = json.loads(line)
        summaries[r["celex_id"]] = clean(r["summary"])

# acts that exist in the corpus AND have within-doc structure to work with
cands = [c for c in summaries if c in celex2id
         and len(corpus.in_doc(celex2id[c])) >= 15]
import random
cands = sorted(random.Random(args.seed).sample(cands, min(args.n, len(cands))))
print(f"  preparing {len(cands)} acts from split '{args.split}'", flush=True)

model = SentenceTransformer("BAAI/bge-small-en-v1.5", device=_DEVICE)

out = {}
stats = {"rescue_A": [], "rescue_B": [], "missed": [], "n_pass": []}
for k, cx in enumerate(cands):
    d = celex2id[cx]
    ps = corpus.in_doc(d)
    sents = sentences(summaries[cx])
    if not sents or len(ps) < 15:
        continue
    P = model.encode([clean(x.text)[:1500] for x in ps],
                     normalize_embeddings=True, batch_size=64, show_progress_bar=False)
    S = model.encode([QPREFIX + s for s in sents],
                     normalize_embeddings=True, batch_size=64, show_progress_bar=False)
    sim = S @ P.T                                   # sentences x passages

    # ORACLE: passages the gold summary actually draws on (best match per sentence)
    oracle_idx = sorted({int(i) for i in sim.argmax(axis=1)})

    # BASE selection: budget passages closest to the document centroid
    centroid = P.mean(axis=0, keepdims=True)
    order = np.argsort(-(P @ centroid.T).ravel())
    base_idx = sorted(order[: args.budget].tolist())

    # closure sets: passages referenced by the selection.
    # Within-doc closure (variant A) follows citations from the passages
    # actually IN context. Cross-doc closure (variant B) follows them from a
    # wider frontier, because cross-document edges are only ~4.5% of the graph
    # and almost never hang off a 12-passage window.
    base_uids = {ps[i].uid for i in base_idx}
    uid2i = {x.uid: i for i, x in enumerate(ps)}
    frontier_idx = order[: max(args.frontier, args.budget)].tolist()
    a_add, b_add = [], []
    for i in base_idx:
        for t in outn.get(ps[i].uid, []):
            if t in uid2i and t not in base_uids:            # same act -> variant A
                a_add.append(uid2i[t])
    for i in frontier_idx:
        for t in outn.get(ps[i].uid, []):
            if t not in uid2i:                                # other act -> variant B
                b_add.append(t)
    a_add = sorted(set(a_add))
    b_add = sorted(set(b_add))

    # which summary sentences does BASE fail to cover, and who rescues them?
    cov_base = sim[:, base_idx].max(axis=1) if base_idx else np.zeros(len(sents))
    missed = cov_base < args.thr
    cov_a = (sim[:, a_add].max(axis=1) if a_add else np.zeros(len(sents)))
    resc_a = missed & (cov_a >= args.thr)
    # variant B's additions live in OTHER acts: score against those passages
    resc_b = resc_a.copy()
    if b_add:
        Bp = [corpus.by_uid[u] for u in b_add if u in corpus.by_uid]
        if Bp:
            BE = model.encode([clean(x.text)[:1500] for x in Bp],
                              normalize_embeddings=True, batch_size=64,
                              show_progress_bar=False)
            cov_b = (S @ BE.T).max(axis=1)
            resc_b = missed & ((cov_a >= args.thr) | (cov_b >= args.thr))

    out[cx] = {
        "doc_id": d,
        "n_passages": len(ps),
        "summary_sentences": sents,
        "base_uids": [ps[i].uid for i in base_idx],
        "oracle_uids": [ps[i].uid for i in oracle_idx],
        "a_add_uids": [ps[i].uid for i in a_add],
        "b_add_uids": b_add,
        "missed_idx": [int(i) for i in np.where(missed)[0]],
        "rescue_a_idx": [int(i) for i in np.where(resc_a)[0]],
        "rescue_b_idx": [int(i) for i in np.where(resc_b)[0]],
    }
    stats["missed"].append(missed.mean())
    stats["rescue_A"].append(resc_a.sum() / max(missed.sum(), 1))
    stats["rescue_B"].append(resc_b.sum() / max(missed.sum(), 1))
    stats["n_pass"].append(len(ps))
    if (k + 1) % 20 == 0:
        print(f"  aligned {k+1}/{len(cands)}", flush=True)

(ROOT / "data").mkdir(exist_ok=True)
fp = ROOT / "data" / f"align_{args.split}.json"
json.dump(out, open(fp, "w"))

m = lambda v: float(np.mean(v)) if v else 0.0
L = ["# Phase 3 — passage-level alignment (oracle targets + rescueable sentences)",
     "", f"Split `{args.split}`, {len(out)} acts, base budget **{args.budget} "
     f"passages**, coverage threshold {args.thr}. Seeded random sample "
     f"(seed {args.seed}). No LLM calls.", "",
     "Selection conditions only on centroid ranks and graph structure, both",
     "fixed before generation — never on model output.", "",
     "| quantity | value |", "|---|---|",
     f"| acts prepared | {len(out)} |",
     f"| passages per act (mean) | {m(stats['n_pass']):.0f} |",
     f"| summary sentences MISSED by the base budget | **{100*m(stats['missed']):.1f}%** |",
     f"| of those, rescued by **variant A** (within-doc closure) | **{100*m(stats['rescue_A']):.1f}%** |",
     f"| of those, rescued by **variant B** (+ cross-doc closure) | **{100*m(stats['rescue_B']):.1f}%** |",
     f"| acts with >=1 cross-doc passage available (B CAN differ from A) | "
     f"**{sum(1 for v in out.values() if v['b_add_uids'])}/{len(out)}** |",
     "", "## Reading", "",
     "The last row is a PRECONDITION, not a result: variant B can only differ",
     "from variant A on acts where cross-document material exists at all. On",
     "2026-08-10 this was 16/80 and B was byte-identical to A for 47/80 acts",
     "(the 4-slot cap was consumed by within-document additions listed first).",
     "Generating under those conditions would have compared A with itself.", "",
     "The MISSED row is the headroom: content the base condition cannot",
     "produce. The A and B rows are how much of that headroom each variant",
     "could in principle supply — the ceiling on any generation gain, computed",
     "before a single token is generated. If B ~ A here, the cross-document",
     "arm has little room to differ and H1 (B > A) is unlikely to show.", "",
     f"Written: `data/align_{args.split}.json` (contexts + per-sentence labels",
     "for the targeted metric).",
     ]
(ROOT / "reports").mkdir(exist_ok=True)
(ROOT / "reports" / "passage_alignment.md").write_text("\n".join(L) + "\n")
print("\n".join(L[3:]))
print(f"\nwrote {fp}")
