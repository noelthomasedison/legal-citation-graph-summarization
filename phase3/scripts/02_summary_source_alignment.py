"""Phase 3 gate G2 — does summary content come from CITED documents?

The decisive question for EUR-Lex-Sum: when the EU writes a summary of a legal
act, does the content come only from that act, or does it genuinely draw on the
other instruments the act cites? If the latter, a summariser that can follow
citations has something to gain — which is the Phase 3 hypothesis.

Measured at DOCUMENT level, not Article level. Justified by the 01 probe: the
summaries engage at the level of whole instruments (184/187 cite another
instrument; only 53/187 name a specific Article), so Article segmentation is
not needed to answer this question.

METHOD, per focal document D with summary S and in-corpus cited documents C:
  1. split S into sentences; chunk D and each C into ~180-word windows
  2. embed everything (bge-small, local MPS)
  3. for each summary sentence, find its best-matching chunk in
       FOCAL   (the act itself)
       CITED   (any act it cites that we hold)
       RANDOM  (control: acts it does NOT cite, same count as CITED)
  4. report how often CITED beats FOCAL — and, crucially, whether CITED beats
     RANDOM

THE CONTROL IS THE POINT. EU legal texts all sound alike, so summary sentences
will match *any* legal document to some degree. A "cited" score only means
something if it beats a random non-cited document of the same corpus. Without
that comparison the number is generic legal-language similarity, not evidence
of citation dependence.

Also reports alignment COVERAGE: EU summaries are written for citizens and
include context with no source in any act. Sentences matching nothing above
threshold are counted, not hidden.

No LLM calls. --pilot N to run on a subset first.
Writes reports/g2_summary_alignment.md.
"""
import argparse
import json
import random
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from huggingface_hub import hf_hub_download          # noqa: E402
import torch  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402
_DEVICE = \"mps\" if torch.backends.mps.is_available() else \"cpu\"
from regkg.textutil import clean                     # noqa: E402

REPO, SPLITS = "dennlinger/eur-lex-sum", ("train", "validation", "test")
CHUNK_WORDS, MIN_SENT_WORDS, SEED = 180, 8, 41
QPREFIX = "Represent this sentence for searching relevant passages: "

ap = argparse.ArgumentParser()
ap.add_argument("--pilot", type=int, default=0, help="run on N focal docs only")
args = ap.parse_args()

# ---------------- load ----------------
def load():
    recs = {}
    for split in SPLITS:
        p = hf_hub_download(REPO, f"data/english/{split}.json", repo_type="dataset")
        for line in open(p):
            if line.strip():
                r = json.loads(line)
                recs[r["celex_id"]] = r
    return recs

CITE = re.compile(r"(Regulation|Directive|Decision)\s+\(?(?:EU|EC|EEC|Euratom)\)?"
                  r"\s*(?:No\s*)?(\d{1,4})/(\d{2,4})")
_T = {"Regulation": "R", "Directive": "L", "Decision": "D"}

def to_celex(kind, a, b):
    a, b = int(a), int(b)
    year, num = (a, b) if a > 1950 else (b, a)
    if year < 100:
        year += 1900 if year > 50 else 2000
    return f"3{year}{_T[kind]}{num:04d}"

def cited_celex(text):
    out = set()
    for kind, a, b in CITE.findall(text):
        try:
            out.add(to_celex(kind, a, b))
        except Exception:
            pass
    return out

_SENT = re.compile(r"(?<=[.;:])\s+|\n+")
def sentences(t):
    return [s.strip() for s in _SENT.split(t or "") if len(s.strip().split()) >= MIN_SENT_WORDS]

def chunks(t):
    w = t.split()
    return [" ".join(w[i:i + CHUNK_WORDS]) for i in range(0, len(w), CHUNK_WORDS)] or [""]

print("loading EUR-Lex-Sum (english)...", flush=True)
recs = load()
docs = {c: clean(r["reference"]) for c, r in recs.items()}
sums = {c: clean(r["summary"]) for c, r in recs.items()}
cites = {c: (cited_celex(t) - {c}) & set(recs) for c, t in docs.items()}
population = sorted([c for c in recs if cites[c]])
print(f"corpus {len(recs)} docs | focal population (>=1 in-corpus citation): "
      f"{len(population)}")

rng = random.Random(SEED)
if args.pilot:
    population = rng.sample(population, min(args.pilot, len(population)))
    print(f"PILOT: {len(population)} focal documents")

# ---------------- embed every needed document once ----------------
needed = set(population) | {c for f in population for c in cites[f]}
print(f"embedding {len(needed)} unique documents...", flush=True)
model = SentenceTransformer("BAAI/bge-small-en-v1.5", device=_DEVICE)

# one flat encode across all documents: throughput is visible, and there is
# a single large batched pass instead of hundreds of small per-doc calls
todo = sorted(needed)
doc_chunks = {c: chunks(docs[c]) for c in todo}
flat = [ch for c in todo for ch in doc_chunks[c]]
print(f"  total chunks: {len(flat):,}", flush=True)
flat_emb = model.encode(flat, normalize_embeddings=True, batch_size=64,
                        show_progress_bar=True)
doc_emb, _pos = {}, 0
for c in todo:
    k = len(doc_chunks[c])
    doc_emb[c] = flat_emb[_pos:_pos + k]
    _pos += k
print("  embedding done", flush=True)

# ---------------- per-focal-document alignment ----------------
def best_sim(qv, celexes):
    """max cosine of each query row against all chunks of the given docs."""
    if not celexes:
        return None
    M = np.vstack([doc_emb[c] for c in celexes])
    return (qv @ M.T).max(axis=1)

BUDGETS = (10, 20, 40)      # chunks a budgeted summariser can actually read

rows = []
noncited_pool = sorted(needed)
for n, f in enumerate(population):
    sents = sentences(sums[f])
    if not sents:
        continue
    qv = model.encode([QPREFIX + s for s in sents], normalize_embeddings=True,
                      batch_size=64, show_progress_bar=False)
    cited = sorted(cites[f])
    # control: same number of documents, sampled from acts this one does NOT cite
    pool = [c for c in noncited_pool if c != f and c not in cites[f]]
    rand = rng.sample(pool, min(len(cited), len(pool)))

    s_focal = best_sim(qv, [f])
    s_cited = best_sim(qv, cited)
    s_rand = best_sim(qv, rand) if rand else np.zeros(len(sents))

    # ---- G2b: what a BUDGETED summariser can actually see ----
    # A real long-document summariser reads a selection, not 13,000 words.
    # Two standard selectors: lead (first B chunks) and centroid (B chunks
    # closest to the document mean). Everything below reuses cached vectors.
    F = doc_emb[f]
    centroid = F.mean(axis=0, keepdims=True)
    order = np.argsort(-(F @ centroid.T).ravel())
    budget_sims = {}
    for B in BUDGETS:
        lead_idx = np.arange(min(B, len(F)))
        cent_idx = order[:B]
        budget_sims[f"lead{B}"] = (qv @ F[lead_idx].T).max(axis=1)
        budget_sims[f"cent{B}"] = (qv @ F[cent_idx].T).max(axis=1)

    for i, s in enumerate(sents):
        r = {"focal": f, "n_cited": len(cited),
             "sim_focal": float(s_focal[i]),
             "sim_cited": float(s_cited[i]),
             "sim_rand": float(s_rand[i])}
        for k, v in budget_sims.items():
            r[f"sim_{k}"] = float(v[i])
        rows.append(r)
    if (n + 1) % 50 == 0:
        print(f"  aligned {n+1}/{len(population)} focal docs", flush=True)

# persist raw rows so any threshold/budget can be re-analysed without re-running
raw = ROOT / "data" / ("g2_rows_pilot.jsonl" if args.pilot else "g2_rows.jsonl")
raw.parent.mkdir(exist_ok=True)
with open(raw, "w") as fh:
    for r in rows:
        fh.write(json.dumps(r) + "\n")
print(f"  wrote raw rows -> {raw}", flush=True)

keys = ["sim_focal", "sim_cited", "sim_rand"] + \
       [f"sim_{s}{B}" for B in BUDGETS for s in ("lead", "cent")]
R = {k: np.array([r[k] for r in rows]) for k in keys}
N = len(rows)
docs_done = len({r["focal"] for r in rows})

# ---------------- headline numbers ----------------
THR = 0.60                       # "aligns to something" threshold
cited_beats_focal = float((R["sim_cited"] > R["sim_focal"]).mean())
cited_beats_rand = float((R["sim_cited"] > R["sim_rand"]).mean())
lift = float((R["sim_cited"] - R["sim_rand"]).mean())
covered = float(((R["sim_focal"] >= THR) | (R["sim_cited"] >= THR)).mean())
only_cited = float(((R["sim_cited"] >= THR) & (R["sim_focal"] < THR)).mean())

def med(k):
    return float(np.median(R[k]))

# ---- threshold sensitivity: the headline must not hinge on one arbitrary cut
def only_cited_at(thr):
    return float(((R["sim_cited"] >= thr) & (R["sim_focal"] < thr)).mean())
def covered_at(thr):
    return float(((R["sim_focal"] >= thr) | (R["sim_cited"] >= thr)).mean())
THRS = (0.60, 0.65, 0.70, 0.75, 0.80)

# ---- G2b: the fair test — what a BUDGETED summariser misses, and whether
# following citations recovers it. Analogue of the CUAD rescue population.
def g2b(sel_key, thr):
    sel = R[sel_key]
    missed = sel < thr                      # budget did not cover this sentence
    if missed.sum() == 0:
        return 0.0, 0.0, 0
    rescued = missed & (R["sim_cited"] >= thr)
    return (float(missed.mean()), float(rescued.sum() / missed.sum()),
            int(missed.sum()))

L = ["# Phase 3 gate G2 — does summary content come from CITED documents?", "",
     "EUR-Lex-Sum (English). For every summary sentence we find its best match",
     "in the act itself (FOCAL), in the acts it cites (CITED), and in an equal",
     "number of acts it does **not** cite (RANDOM control). Semantic matching",
     "with bge-small; document-level (no Article segmentation — justified by",
     "the 01 probe, which showed summaries engage at instrument level).", "",
     f"**Scope:** {docs_done} focal documents, {N:,} summary sentences"
     + (" (PILOT)" if args.pilot else "") + ".", "",
     "## Similarity of a summary sentence to its best match", "",
     "| Source | median similarity |", "|---|---|",
     f"| FOCAL (the act itself) | {med('sim_focal'):.3f} |",
     f"| CITED (acts it cites) | {med('sim_cited'):.3f} |",
     f"| RANDOM (acts it does not cite) | {med('sim_rand'):.3f} |", "",
     "## Headline", "",
     f"- summary sentences whose best match is in a CITED act rather than the "
     f"focal act: **{100*cited_beats_focal:.1f}%**",
     f"- summary sentences matching a CITED act better than a RANDOM act: "
     f"**{100*cited_beats_rand:.1f}%**  (50% = no signal)",
     f"- mean similarity lift of CITED over RANDOM: **{lift:+.4f}**",
     f"- alignment coverage (matches FOCAL or CITED above {THR}): "
     f"{100*covered:.1f}%",
     f"- sentences covered ONLY by a cited act (not by the focal act): "
     f"**{100*only_cited:.1f}%**", "",
     "### Threshold sensitivity (the headline must not hinge on one cut)", "",
     "| threshold | coverage (focal or cited) | ONLY cited |",
     "|---|---|---|"]
L += [f"| {t:.2f} | {100*covered_at(t):.1f}% | **{100*only_cited_at(t):.1f}%** |"
      for t in THRS]
L += ["",
      "## G2b — the fair test: a BUDGETED summariser", "",
      "The figures above assume the summariser can read the **whole** act",
      "(~13,000 words). A real long-document summariser reads a selection.",
      "Here we give it the first B chunks (lead) or the B chunks closest to the",
      "document centroid, then ask: of the summary sentences its selection does",
      "NOT cover, how many are recoverable by following a citation? This is the",
      "direct analogue of the CUAD rescue-arm population.", "",
      "| selector | budget (chunks) | sentences missed | of those, recoverable via citations |",
      "|---|---|---|---|"]
for B in BUDGETS:
    for sel, lab in (("lead", "lead"), ("cent", "centroid")):
        miss, resc, nm = g2b(f"sim_{sel}{B}", THR)
        L.append(f"| {lab} | {B} (~{B*CHUNK_WORDS:,} words) | "
                 f"{100*miss:.1f}% ({nm:,}) | **{100*resc:.1f}%** |")
L += ["",
      "## How to read this", ""]
L += [
     "The RANDOM control is the load-bearing comparison. EU legal texts share",
     "vocabulary and register, so a summary sentence will resemble *any* act to",
     "some degree. Citation dependence is only demonstrated if CITED beats",
     "RANDOM: at 50% the 'linkage' would be generic legal-language similarity",
     "rather than evidence that the summary draws on the cited material.", "",
     "**Which number decides the gate.** The whole-document 'ONLY cited' figure",
     "is the pessimistic bound: it assumes the summariser reads all ~13,000",
     "words, so the focal act gets every chance to cover the summary itself.",
     "The G2b table is the fair test, because real long-document summarisers",
     "work from a selection. If the recoverable-via-citations column is high at",
     "realistic budgets, the graph has a job to do even though the focal act",
     "dominates when fully available.", "",
     "Anchors from Phase 2: ObliQA 0.5% linkage produced a guaranteed null;",
     "CUAD 3.2% rescueable produced a real effect that fired rarely; XRef 90%",
     "produced large gains. A summarisation corpus should sit well above the",
     "CUAD-marginal regime, because Phase 3 has no rescue-arm escape hatch —",
     "there is no way to select only the questions where the graph fires.",
     ]
(ROOT / "reports").mkdir(exist_ok=True)
name = "g2_summary_alignment" + ("_pilot" if args.pilot else "") + ".md"
(ROOT / "reports" / name).write_text("\n".join(L) + "\n")
print("\n".join(L[6:]))
print(f"\nwrote phase3/reports/{name}")
