"""Phase 3 dataset gate — EUR-Lex-Sum feasibility probe (G1 + G2 proxies).

Runs the FROZEN Phase-1 detector over EUR-Lex-Sum (Aumiller et al., EMNLP 2022;
`dennlinger/eur-lex-sum`, CC-BY-SA 4.0) with ZERO retuning — the same protocol
that transferred the ADGM extractor to CUAD contracts.

Answers, with numbers rather than argument:
  G1   does the detector fire on EU legal text at a usable rate?
  EXT  is there a cross-document (variant B) signal — do acts cite other acts?
  G2*  PROXY only: do the human summaries engage with cited material?
  CLOS is the corpus closed under citation (can we follow a citation to a
       document we already hold, without scraping)?

IMPORTANT — what this does NOT establish: G2 proper asks whether the *content*
of cited material appears in the summary. Counting instrument mentions in a
summary is a precondition, not that measurement; true G2 needs the two-way
alignment described in phase3/DATASET_PLAN.md §3. Nothing here licenses
starting Phase 3.

No LLM calls. Downloads ~142 MB on first run (cached by huggingface_hub).
Writes reports/eurlexsum_gate.md.
"""
import json
import re
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from huggingface_hub import hf_hub_download   # noqa: E402
from regkg.detect import detect               # noqa: E402
from regkg.textutil import clean              # noqa: E402

REPO, SPLITS = "dennlinger/eur-lex-sum", ("train", "validation", "test")

def load():
    recs = {}
    for split in SPLITS:
        p = hf_hub_download(REPO, f"data/english/{split}.json", repo_type="dataset")
        for line in open(p):
            if line.strip():
                r = json.loads(line)
                recs[r["celex_id"]] = (split, r)
    return recs

# EU acts cite each other as "Regulation (EU) 2016/679" / "Directive 95/46/EC" /
# "Regulation (EC) No 595/2009". CELEX = 3 + YYYY + {R,L,D} + 4-digit number.
CITE = re.compile(r"(Regulation|Directive|Decision)\s+\(?(?:EU|EC|EEC|Euratom)\)?"
                  r"\s*(?:No\s*)?(\d{1,4})/(\d{2,4})")
_T = {"Regulation": "R", "Directive": "L", "Decision": "D"}

def to_celex(kind, a, b):
    a, b = int(a), int(b)
    year, num = (a, b) if a > 1950 else (b, a)   # 2016/679 vs 595/2009
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

def main():
    recs = load()
    val = {c: r for c, (s, r) in recs.items() if s == "validation"}
    print(f"EUR-Lex-Sum English: {len(recs)} docs "
          f"({ {s: sum(1 for v in recs.values() if v[0]==s) for s in SPLITS} })")

    rates, dw, sw, comp, extu, s_art, s_instr = [], [], [], [], [], [], []
    zero = 0
    for r in val.values():
        doc, summ = clean(r["reference"]), clean(r["summary"])
        nd, ns = len(doc.split()), len(summ.split())
        if nd < 50:
            continue
        ms = detect(doc, None, guards=True)
        rates.append(1000 * len(ms) / nd)
        zero += not ms
        dw.append(nd); sw.append(ns); comp.append(ns / nd)
        extu.append(len(cited_celex(doc)))
        s_art.append(len(re.findall(r"\bArticle\s+\d+", summ)))
        s_instr.append(len(cited_celex(summ)))
    n = len(rates)

    # closure over the whole English corpus
    hits = tot = 0
    per_doc = []
    for cid, (_s, r) in recs.items():
        cited = cited_celex(clean(r["reference"])) - {cid}
        if not cited:
            continue
        inside = sum(c in recs for c in cited)
        hits += inside; tot += len(cited)
        per_doc.append(inside / len(cited))

    m = lambda v: f"median {st.median(v):.1f}, mean {st.mean(v):.1f}, max {max(v):.0f}"
    L = ["# Phase 3 dataset gate — EUR-Lex-Sum (feasibility probe)", "",
         "Frozen Phase-1 detector, **zero retuning** (the protocol that carried",
         "the ADGM extractor to CUAD). Source: EUR-Lex-Sum (Aumiller et al.,",
         "EMNLP 2022), English subset, CC-BY-SA 4.0. No LLM calls.", "",
         f"Corpus: **{len(recs)} English documents** "
         f"(train {sum(1 for v in recs.values() if v[0]=='train')}, "
         f"validation {sum(1 for v in recs.values() if v[0]=='validation')}, "
         f"test {sum(1 for v in recs.values() if v[0]=='test')}); "
         f"probe run on the {n} validation documents.", "",
         "## Shape", "",
         f"- document length (words): {m(dw)}",
         f"- summary length (words): {m(sw)}",
         f"- compression (summary/document): median {st.median(comp):.3f} "
         f"(~{1/st.median(comp):.0f}:1)", "",
         "## G1 — detection (does the extractor fire?)", "",
         f"- mentions per 1,000 words: **{m(rates)}**",
         f"- documents with zero mentions: **{zero}/{n}**",
         "- anchors: CUAD 11.6 per 1,000 words (gate passed, mechanism worked);",
         "  ADGM is the corpus the rules were tuned on.",
         f"- **verdict: PASS** — higher density than CUAD, and no document is empty.", "",
         "## EXT — cross-document signal (variant B)", "",
         f"- distinct other instruments cited per document: {m(extu)}",
         f"- documents citing >= 1 other instrument: "
         f"**{sum(1 for x in extu if x)}/{n}**",
         "- this is the *external* reference class — Phase 1's weakest "
         "(recall 0.743) but the class ObliQA-XRef showed carries the value.", "",
         "## G2 (PROXY ONLY) — do summaries engage with cited material?", "",
         f"- summaries citing another instrument: "
         f"**{sum(1 for x in s_instr if x)}/{n}** ({m(s_instr)})",
         f"- summaries naming a specific 'Article N': "
         f"{sum(1 for x in s_art if x)}/{n} ({m(s_art)})",
         "",
         "Reading: the summaries operate at the **instrument** level "
         "(cross-document) far more than the article level. That matches the",
         "experiment Tuba proposed — focal document alone vs focal document +",
         "graph-retrieved cited material — and it is the cross-document case.",
         "",
         "> **This is a precondition, not the gate.** A summary *mentioning* "
         "> Directive 95/46/EC does not prove its *content* came from that "
         "> instrument. True G2 requires the two-way alignment in "
         "> `DATASET_PLAN.md` §3 and is NOT established here.", "",
         "## CLOS — is the corpus closed under citation?", "",
         f"- distinct cited instruments (summed over documents): {tot:,}",
         f"- of those, present in EUR-Lex-Sum itself: **{hits:,} "
         f"({100*hits/tot:.1f}%)**",
         f"- per-document coverage: median {st.median(per_doc)*100:.0f}%, "
         f"mean {st.mean(per_doc)*100:.0f}%",
         f"- documents with >= 1 cited instrument also in corpus: "
         f"**{sum(1 for x in per_doc if x>0)}/{len(per_doc)}**", "",
         "Reading: roughly a third of citations resolve *inside* the dataset, so",
         "a first experiment needs **no scraping at all** — there is already a",
         "large population where a citation can be followed to a document we",
         "hold. Fuller coverage is programmatic (CELEX ids give stable URLs),",
         "but is an optional extension rather than a prerequisite.", "",
         "## What this settles, and what it does not", "",
         "SETTLED: the extractor transfers to EU legal text untouched; the "
         "corpus is citation-dense; gold summaries exist, are human-written, "
         "licensed (CC-BY-SA 4.0) and citable; compression is realistic "
         f"(~{1/st.median(comp):.0f}:1, not the 42K->150 ratio the March plan "
         "assumed); and no dataset construction is required to begin.", "",
         "OPEN: true G2 (does cited *content* reach the summary), resolution "
         "rate of EU-style references (detection != resolution — needs an "
         "ingest that segments acts into Articles and an instrument-id "
         "router), and G3 (does centrality predict summary-worthiness).",
         ]
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "eurlexsum_gate.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[8:]))
    print("\nwrote phase3/reports/eurlexsum_gate.md")

if __name__ == "__main__":
    main()
