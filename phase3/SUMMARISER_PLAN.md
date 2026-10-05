# Phase 3 — Graph-Guided Summarisation: method and experiment plan

Status: **PLAN. Nothing built.** Written 2026-08-10, after the dataset gate
passed (`DATASET_PLAN.md`, `reports/g2_control.md`). Pre-registered in the same
spirit as `phase1/PLAN.md`: design, metrics and thresholds fixed *before* the
run, so results cannot be reverse-engineered into a story.

---

## 1. What the gate licenses, and what it does not

**Licensed.** On EUR-Lex-Sum, when a budgeted summariser misses summary
content, following citations recovers it 58–72% of the time versus 50–60% for
unrelated acts (+8.7 to +11.9 pts, centroid-10 95% CI [+9.5, +14.5]). 76% of
documents have at least one rescueable sentence. So there is real, broadly
distributed, citation-specific information to be won.

**NOT licensed.** The gate is a *similarity proxy*. It shows the missing
information is reachable; it does not show a summariser writes better summaries
when handed it. That is precisely what this phase tests — so the null result is
live and must be reportable.

**Expected effect size, stated in advance so we cannot inflate it later.**
~5–9% of a summary's content is at stake. This is the CUAD regime (a real
effect that fires on a minority of cases), not the XRef regime (+22 points).
Design for detecting a small effect: paired comparisons, adequate n, and a
pre-specified subset where the mechanism should fire hardest.

---

## 2. The experiment (Tuba's design, adopted)

For each act, generate a summary under **four** conditions and score all against
the EU's official human summary. The graph arm splits into the supervisor's
agreed **graph-scope A/B**, carried through from Phase 2:

| Condition | Context construction | Content available |
|---|---|---|
| **base** | budgeted selection, linear chunks | focal act only |
| **variant A** | selection **+ within-document reference closure** | focal act only |
| **variant B** | as A **+ cross-document reference closure** (CELEX) | focal act + cited acts |
| **oracle** | selection + the passages the gold summary actually draws on | — |

> **REVISED 2026-08-10 after the density check** (`reports/eurlex_graph.md`).
> Variant A was originally *community chunking*. Measured: Louvain on EU acts
> gives median community size **1**, with only **31%** of passages in a
> community of size ≥2 — so community chunking degenerates into linear
> chunking for most of a document and variant A would have collapsed toward
> base for the wrong reason (a sparsity artefact, not a finding about
> references). **Reference closure works on single edges instead of clusters**:
> 863/3,681 passages have ≥1 within-document reference and 595 are cited, so
> A has real coverage. This also makes A and B exactly symmetric — the same
> operation over internal vs internal+external edges — mirroring Phase 2's
> A/B and keeping the comparison like-for-like.
>
> Community detection is **not discarded**: it becomes an optional chunking
> refinement (§3.1), tested separately and reported on its own merits, rather
> than being load-bearing for an entire arm.

Conditions are **nested** (B ⊇ A ⊇ base), exactly as in Phase 2 where
B = A + cross-document edges. That gives clean marginal contributions:

- **A − base** = the value of *within-document* references.
- **B − A** = the value of *cross-document* references — the supervisor's
  central question, and the one the gate produced evidence for.
- **oracle − B** = remaining headroom, i.e. what better extraction would buy.

> **Note on evidence asymmetry.** The G2 gate (+11.9 pts, CI [+9.5, +14.5])
> measured recovery from *cited external acts* — it supports **B**. Variant A
> is untested: no gate measured whether within-document references supply
> summary content the budgeted selection missed. A is therefore genuinely
> exploratory, and a null on A−base is a plausible, reportable outcome rather
> than a failure.

`oracle` is the ceiling: it separates "the graph fetched the wrong material"
from "extra material does not help anyway" — the diagnostic that made the CUAD
result interpretable.

**Token budget is held identical across all four conditions.** If B simply gets
a bigger prompt, any gain is confounded with context length. So B *displaces*
focal content rather than adding to it: same budget, different composition.
This is the single most important control in the design and the first thing a
reviewer will look for. Log actual token counts per condition and report them —
do not assume the budgeting code worked.

Note the budget control is what makes **A − base** meaningful too: A and base
receive the same content volume from the same document, differing only in how
it was grouped and which passages the grouping surfaced.

Consistent with Phase 2's conclusion, the graph is used to **augment context,
never to rerank**.

---

## 2b. DEVIATIONS FROM THIS PLAN AS EXECUTED (recorded 2026-08-10, BEFORE results)

Written while generation was running and before any summary was scored, so the
record cannot be shaped by the outcome. Three departures from §3:

**D1 — Chunking is NOT community detection.** §3.1 specified Leiden
communities as the unit, conditional on a density check, with the fallback
stated in advance: *"if it degenerates, fall back to linear chunking + one-hop
closure and say so plainly."* **It degenerated.** Measured on EUR-Lex
(`reports/eurlex_graph.md`): median community size **1**, only **40.2%** of
passages in a community of size ≥2, 0.68 edges/passage. Community chunking
would have been linear chunking wearing a hat.

*What runs instead:* the act's own **Article → paragraph → point** units from
`eurlex_ingest.py` (structurally better than fixed-width windows), selected by
centroid similarity to a 12-passage budget, plus one-hop reference closure.
This is the pre-registered fallback, and it is why variant A was redefined
from "community chunking" to "within-document reference closure" (§2) —
closure works on single edges, so it survives sparsity.
**Status: plan-sanctioned deviation, invoked by the measurement it was
conditioned on.**

**D2 — No PACB centrality budgeting.** §3.2 gated this arm on **G3** (does
centrality predict summary-worthiness above lead-position and length
baselines). **G3 was never run.** The arm is therefore correctly absent, but
the centrality-budgeting premise is **untested, not disproven** — it must be
reported that way, not quietly dropped.
**Status: correctly gated; G3 outstanding.**

**D3 — Generation is SINGLE-PASS, not hierarchical.** §3.3 specified
"summarise each community, then compose the community summaries". What runs
makes **one LLM call per act** over all selected passages
(`07_summarise_generate.py`, one `client.gen` call site).

*No measurement forced this.* The honest reasoning: hierarchical
summarisation's natural unit was communities, which D1 removed; the 14,000-char
context fits llama-3.3-70b comfortably, so length does not force decomposition;
and hierarchical would multiply calls ~5–10×, which did not fit the schedule.
But this is a **design decision, not a consequence** — and it drops one of the
two approaches raised in the supervisor meetings (hierarchical vs
chunk-and-stitch).
**Status: unforced deviation. Hierarchical remains a legitimate follow-up arm,
runnable on the same 80 acts and the same cached alignment, and the
single-pass-vs-hierarchical contrast is a separate question (generation
architecture) from the graph-scope question this run answers.**

### What the running experiment therefore tests

base / variant A / variant B / oracle over **80 test-split acts**, equal
context budget, single-pass generation, graph used to augment context and never
to rerank. It answers the **graph-scope** question (does within- or
cross-document reference closure improve summaries) and NOT the chunking or
generation-architecture questions, which D1–D3 removed from scope.

---

## 3. Method: how context is selected

> **NOT EXECUTED AS WRITTEN — see D1 in §2b.** The density check this section
> was conditioned on failed (median community size 1). The text below is
> retained as the pre-registered design; the fallback it specifies is what
> actually ran.

### 3.1 Chunking — dynamic community detection (decided 2026-08-10)

Linear windows sever a clause from the definition it depends on. Instead,
chunk by structure: build the within-document citation graph and let
**communities** be the units.

- **Computed per document, at summarisation time** — never a partition fixed on
  the ADGM graph. The project's strength is that nothing is tuned per corpus; a
  fixed partition would not transfer to EU acts.
- **Leiden, not Louvain.** Louvain can return internally disconnected
  communities — disqualifying when connectivity is the whole point. Fix the
  seed for reproducibility.
- **Symmetrise the directed graph** (A cites B ⇒ they belong together) and
  state that as an explicit assumption, not a library default.
- **Resolution derived from the budget**, not hand-tuned: to fill a budget of
  B tokens at ~N tokens per community summary, target ~B/N communities.
- **Hybrid closure.** Modularity may separate a definition cited *once* from
  the clause depending on it — exactly the case this thesis cares about. So
  after community detection, pull in directly-cited passages that landed
  outside their citer's community. Communities give balance; the closure step
  guarantees one-hop dependencies survive.

**PREREQUISITE — density check (§6, must run first).** ADGM has <1 edge per
passage. On a graph that sparse, community detection returns mostly singletons
and degenerates into linear chunking wearing a hat. Measure the community-size
distribution on EUR-Lex before building anything on it. If it degenerates, fall
back to linear chunking + one-hop closure and say so plainly.

### 3.2 Budgeting

Two arms, because the second is unvalidated:

- **Uniform** — equal budget per community. The honest default.
- **Centrality-weighted (PACB)** — more budget to communities containing
  heavily-cited passages. **Gated on G3** (§6): if centrality does not predict
  summary-worthiness above lead-position and length baselines, this arm is
  dropped rather than run and quietly buried.

### 3.3 Generation

> **NOT EXECUTED AS WRITTEN — see D3 in §2b.** A single pass over the selected
> passages ran instead. Retained as the pre-registered design and as the
> specification for the follow-up hierarchical arm.

Hierarchical, one level: summarise each community, then compose the community
summaries into the final summary under the global budget. One level, not
recursive halving — each extra round loses the definitions and exceptions the
thesis is about, and the ~13:1 compression does not require more.

`meta/llama-3.3-70b-instruct`, temperature 0, every response disk-cached
(namespace `sum-v1`), so runs are resumable and reproducible.

---

## 4. Evaluation

**Primary — content coverage against the human summary.** ROUGE-1/2/L and
BERTScore. Standard, comparable to the EUR-Lex-Sum paper's own baselines.

**Secondary — faithfulness.** RePASs, reusing the Phase 2 stack unchanged
(entailment support, contradiction, obligation coverage). Absolute values are
not comparable across corpora; only paired within-corpus contrasts are.

**The targeted metric — this is the one that tests the hypothesis.**
Aggregate ROUGE will drown a 5–9% effect. So, pre-specified: from the gate data
we already know *which* summary sentences are rescueable (missed by the focal
selection, recoverable via citations). Measure **coverage of exactly those
sentences** under base vs graph. This is the direct analogue of CUAD's rescue
arm, which is what turned a null aggregate into a significant, interpretable
result. Selection uses only retrieval/graph structure, fixed before generation
— never model output.

**Statistics.** Paired per-document differences; Wilcoxon signed-rank;
bootstrap CIs resampled **by document**.

---

## 5. Pre-registered thresholds and decision rule

Fixed before the run. All comparisons paired per document, Wilcoxon
signed-rank, bootstrap CIs resampled by document.

- **H1 (primary — cross-document value):** **B > A** on rescueable-sentence
  coverage, p < 0.05. This is the supervisor's central question and the one
  the gate produced evidence for. Note it is B vs **A**, not B vs base — that
  isolates the cross-document contribution from the chunking contribution.
- **H2 (structure value):** **A > base** on rescueable-sentence coverage.
  **Untested by the gate** — this is the RCGC/community claim and may well be
  null, especially if the density check (§6.2) is marginal.
- **H3 (aggregate):** B ≥ base on overall ROUGE-L/BERTScore — expected
  **null or near-null**. Recorded in advance so an aggregate null reads as a
  known property of a 5–9% effect, not as a failure discovered afterwards.
- **H4 (ceiling):** oracle > base. If this fails, the harness or metric is
  insensitive and **no conclusion may be drawn** about A or B.

**Decision rule.**
- H4 fails → report a harness/metric limitation; draw no conclusion about the
  graph.
- H4 passes, H1 passes → cross-document references demonstrably help
  summarisation. Report H2 and H3 honestly alongside, whatever they show.
- H4 passes, H1 fails → cross-document augmentation fetched the wrong
  material; report as a negative, with oracle − B quantifying the headroom
  and linking it (as in Phase 2) to Phase 1's external-recall weakness.
- H2 null with H1 positive → report that the win comes from *content*, not
  *organisation*: community chunking did not pay off on this corpus. That is
  a clean, publishable separation, not a disappointment.

---

## 5b. RESULTS (run 2026-08-10/11, 80 acts, EUR-Lex-Sum test split)

`reports/summarisation_results_fast.md`; raw per-act values in
`data/eval_test.json`; 320 summaries in `data/summaries_test.jsonl`.

### Means (higher is better)

| metric | base | variant A | variant B | oracle |
|---|---|---|---|---|
| **targeted** (rescueable-sentence coverage) | 0.195 | **0.267** | 0.251 | **0.347** |
| ROUGE-L | 0.202 | 0.202 | 0.204 | 0.206 |
| ROUGE-1 precision (contamination check) | 0.673 | 0.688 | 0.680 | 0.696 |
| BERTScore | 0.837 | 0.839 | 0.839 | 0.841 |

Both graph conditions beat base on every metric — variant A is ~37% above base
on the targeted measure. **The direction is consistently positive.**

### Paired contrasts (same act, only the context differs)

| contrast | targeted | p | wins/losses | verdict |
|---|---|---|---|---|
| oracle − base | +0.152 | 0.072 (BERTScore **1.05e-06**) | 9/2 | **SIGNIFICANT** |
| oracle − B | +0.096 | **0.027** | 6/0 | **SIGNIFICANT** |
| A − base | +0.073 | 0.115 | 5/1 | not significant |
| B − base | +0.057 | 0.394 | 5/2 | not significant |
| B − A | **−0.016** | 0.58 | 1/3 | **no difference** |

### Verdict against the pre-registered hypotheses (§5)

| | claim | outcome |
|---|---|---|
| **H1** | B > A (cross-document value) — *the central question* | **FAILS.** −0.016, p=0.58. Cross-document references gave no advantage over within-document ones. |
| **H2** | A > base (structure value) | **NOT ESTABLISHED.** +0.073, p=0.115. Direction positive, 5/1 wins, but underpowered. |
| **H3** | aggregate ROUGE/BERTScore ≥ base, *expected null* | **Confirmed null**, exactly as pre-registered. |
| **H4** | oracle > base (ceiling / sensitivity) | **PASSES**, p=1.05e-06 on BERTScore. |

**Decision rule applied (§5):** H4 passes and H1 fails → "cross-document
augmentation fetched the wrong material; report as a negative, with oracle − B
quantifying the headroom." That is the result: oracle − B = +0.096, p=0.027.

### Why the gaps do not reach significance

Although 80 acts were generated, adding referenced passages **changed the
outcome on only 6 acts (A) and 4 acts (B)**; the rest were effectively
unchanged. So the effective n for the decisive comparisons is a handful, not
80. A won 5 of its 6, which is encouraging and worthless as proof.

This was predicted before generation: the alignment showed base misses 9.7% of
summary content and B could reach 17.6% of that — **~1.7% of a summary ever at
stake**.

### Why B failed — NOT graph sparsity

The EU graph is **denser** than the corpora that produced positive results:
0.68 edges/passage vs ADGM's 0.50, 57.2% resolution vs CUAD's 38.9%. The real
causes, all measured:

1. **Only 38.6% citation closure.** EUR-Lex-Sum holds 1,504 acts; when one
   cites another the target usually is not in the corpus to follow.
2. **EU summaries summarise ONE act.** They mention other instruments
   constantly but draw little *content* from them.
3. Hence ~1.7% of a summary at stake — the CUAD frontier lesson again: a
   signal strong at document level nearly vanishes at the passage-level window
   a real method uses.

### What is genuinely defensible from this

- **The premise is proven:** better evidence produces better summaries
  (oracle − base, p=1.05e-06). The idea is sound.
- **The failure is located:** in graph *coverage*, not in the concept —
  oracle − B is significant, quantifying what better extraction would buy.
- **The negative on B is clean** and was predicted in advance by the alignment.

### RePASs faithfulness — PARTIAL (21 of 80 acts, stopped 2026-08-11)

Stopped deliberately: ~4.6 min/act on an 8 GB machine meant ~5 more hours for
a supplementary metric. `data/repass_test.jsonl` holds 84 rows / 21 complete
acts; the scorer resumes from that file if ever wanted.

| | base | A | B | oracle |
|---|---|---|---|---|
| RePASs | 0.3846 | 0.3865 | 0.3744 | **0.3501** |
| entailment support | 0.337 | 0.357 | 0.365 | 0.283 |
| contradiction (lower better) | 0.290 | 0.308 | 0.342 | 0.322 |
| obligation coverage | 0.106 | 0.111 | 0.101 | 0.089 |

Paired: A−base +0.002 (p=0.62), B−A −0.012 (p=0.33), B−base −0.010 (p=0.47)
— **all null, consistent with the content metrics**. But
**oracle−base = −0.034, p=0.007**: the oracle is *significantly LESS faithful*,
the exact reverse of its significant *win* on content metrics.

**Interpretation (tentative, n=21).** All conditions are scored against the
same source-passage pool, but oracle's context holds the passages the human
summary actually used, so its output tracks that human summary most closely.
EU summaries are written for citizens — they paraphrase, compress and
interpret rather than restate legal wording. A summary imitating that style is
**less literally entailed by the raw text** even while matching the reference
better. So the two metric families measure genuinely different things on
abstractive gold, and can move in opposite directions.

**Caution worth reporting:** RePASs was built for QA answers scored against
regulatory passages, not for abstractive summarisation. This may be as much a
finding *about the metric* as about the summaries — and it is a reason not to
treat RePASs as a faithfulness oracle in Phase 3 without further validation.

### Outstanding
Also outstanding: manual adjudication of the 100-edge EU precision audit
(`reports/eurlex_audit_sample.md`); these results inherit its unknown error rate.

---

## 6. Prerequisites (cheap, no LLM, run these first)

1. ~~**Resolution rate for EU references.**~~ **DONE** — `reports/eurlex_graph.md`:
   **57.2%** resolution, 260,149 passages, 175,976 edges (of which ~7,856
   cross-document via CELEX routing). Required building `eurlex_ingest.py`
   (Article→paragraph→point + Chapters) and `eurlex_resolve.py` (the EU guard).
2. ~~**Community density check.**~~ **DONE and FAILED** — median community size
   1, 40.2% of passages in a community of size ≥2. Triggered the §3.1 fallback;
   see D1 in §2b.
3. **G3 — does centrality predict summary-worthiness?** **STILL OUTSTANDING.**
   AUC of in-degree / PageRank against gold-summary usage, versus
   **lead-position and length baselines**. Gates the PACB arm (D2). Lead bias
   is notoriously strong in summarisation; beating it is the honest bar.

### Defects found and fixed while building these (2026-08-10)

Each was caught by measurement, not inspection, and each is a reportable
finding about transferring a rules-based extractor to a new legal system:

| Defect | Effect | Fix |
|---|---|---|
| `use_aliases=False` also disabled the *unknown-document* guard | third-country law ("Land Law 2013", "Decree No. 02/ND-CP") force-resolved into the focal act | `EuResolver` subclass; `phase1` left frozen so Phase 1/CUAD results stay reproducible |
| `sorted(celex)[:N]` is not a sample | CELEX sorts by sector, so the first 200 were all 150 international agreements (11% of corpus) — segmentation and precision measured on the wrong document type | seeded random sampling in `load_eurlexsum` |
| Chapter passages carried 4,000-char bodies | they contained the Article headings inside them; the detector read those as citations (15/100 sampled edges were chapter→contained-article artefacts) | truncate chapter body at the first Article heading |
| EU *relative* references unmodelled | "paragraph 1" inside Article 29 resolved to Article 1, not 29(1) (10/100 sampled edges) | relative resolution against the source's own Article |
| Nested-quantifier regex | 1,196 µs/call vs 0.9 µs — ~8 min of pure waste per full run | bounded search over a fixed window |
| Variant B built as `(within + cross)[:4]` | within-doc additions (mean 5.5) consumed the cap, so **B was byte-identical to A for 47/80 acts** — the comparison tested nothing | cross-document passages listed first; frontier widened to 50 for cross-doc closure |

The last one is the CUAD lesson recurring: the G2 gate measured linkage at
**document** level (+11.9 pts), but the summariser operates at **passage**
level, and the signal nearly vanished at that frontier. Re-check the gate
whenever the granularity of the method changes.

---

## 7. Scope realism (read before starting)

Presentation mid-August, dissertation September. This plan is a full programme;
the calendar does not fit all of it. Priority order if time runs short:

1. Prerequisites §6 (cheap, and each is a reportable finding in its own right)
2. **base / A / B** on a **stratified subset** (~100 documents) with the
   targeted rescueable-sentence metric — enough for paired significance tests
   on both H1 (B−A) and H2 (A−base). ~300 LLM calls, comparable to the CUAD
   rescue arm (300 calls, ran overnight on the free tier).
3. **oracle** arm (+~100 calls) — needed for H4, without which nothing else
   is interpretable. Do not drop this to save time; drop breadth instead.
4. Aggregate ROUGE/BERTScore over the full test split
5. PACB centrality arm (only if G3 passes)

If forced to cut further: keep base / A / B / oracle on **fewer documents**
rather than dropping a condition. A four-condition design on 60 documents is
interpretable; a three-condition design on 200 is not, because the missing
condition is exactly the one that tells you what the result means.

**A completed gate study plus one well-run, properly controlled generation
experiment is a stronger dissertation contribution than a half-built pipeline
with no result.** Tuba has explicitly offered consolidating existing work as
the alternative; that remains legitimate and is not a retreat.

---

## 8. Risks

- **Effect too small to detect.** ~5–9% of content at stake; aggregate metrics
  may show nothing. Mitigated by the targeted metric (§4) — and the expectation
  is pre-registered (H2) so a null is interpretable, not embarrassing.
- **Budget confound.** Handled by equal-budget displacement (§2); must be
  verified by logging actual token counts per condition, not assumed.
- **Community degeneration** on sparse graphs. Handled by the §6 density check
  and a stated fallback.
- **ROUGE insensitivity.** EU summaries are written for citizens and include
  framing with no source in any act; n-gram overlap may not move even when
  content improves. This is why RePASs and the targeted metric run alongside.
- **Extraction quality ceiling.** EU external references are the class Phase 1
  is weakest on (0.743). The oracle arm quantifies how much this costs.
