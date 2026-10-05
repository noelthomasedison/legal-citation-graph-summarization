# Phase 3 v2 — Hierarchical Summarisation: pre-registration

Status: **PRE-REGISTRATION FROZEN BEFORE V2 GENERATION.** No v2 summaries or
evaluation results exist. The context-only feasibility audit described in the
dated amendment below made zero LLM calls and is not an outcome analysis.

v1 is **retained unchanged** as a historical pilot: its code (scripts 04–11),
data, caches and reports are untouched, and every v2 artefact carries a
distinct name. Its numerical results remain reproducible, but its B-vs-A
conclusion is methodologically inconclusive because of the defects below.

## Pre-generation amendment — 2026-08-11

This amendment was written after implementation and a context-only structural
audit, but before any v2 summary-generation call. It records feasibility and
engineering facts without changing H1, H2, the corpus, seed, model, threshold,
or reporting rules.

- Steps 1–4 and the graph-precision gate are complete. The final v2.2 graph
  was built from 232,756 region-aware passages with zero UID collisions.
  All 72 graph/context/cache tests pass.
- An 80-act **approximate whitespace-token audit** completed against the
  earlier v2 graph with zero LLM calls. Its `_approx` artefacts are marked
  `valid_for_generation=false`, cannot be consumed by the generator or
  evaluator, and must be rebuilt against v2.2 for a current diagnostic. The
  exact Llama-3.3 tokenizer audit was subsequently completed as recorded
  below.
- The budget control is a **matched comparator-derived prompt ceiling**, not a
  claim of byte-for-byte token equality: A may not exceed Base, B may not
  exceed A, and Oracle may not exceed Base. A comparison is eligible only when
  every paired group is within 1%; a treatment is never allowed to be longer.
- The approximate audit found 39 acts with a balanced genuine B treatment, but
  only 3 acts (3 gold sentences) in the primary
  `b_incremental_actual_rescue_idx` subset. Therefore the structural `n>=30`
  gate is a treatment-delivery sanity check only; it is **not evidence that H1
  is statistically powered**. The exact audit must report both counts.
- If the exact H1 rescue subset remains only a handful of acts, the full run
  requires a documented supervisor go/no-go decision: expand the frozen
  context screen, treat H1 as explicitly exploratory/underpowered, or stop
  generation. The threshold or labels must not be changed to manufacture n.
- The final graph is `eurlex_edges_v2_2.jsonl` (sha256 prefix
  `f4b9f0ad7203d986`). Seeds 41, 97, 173, 251 and 347 were development/repair
  samples and are not used to estimate final precision.
- The untouched seed-389 audit produced within-document 49/50 TRUE and
  cross-document 50/50 TRUE; population-weighted precision is 0.982 (95%
  stratified-bootstrap CI [0.946, 1.000]). The one observed false edge is
  retained in the audit rather than repaired from the held-out result.
- The canonical exact-token v2.2 context audit now passes all engineering
  gates: Base/A/B mean complete-prompt totals are 6,652/6,648/6,645 tokens;
  no treatment exceeds its comparator; 45/80 acts receive a balanced genuine
  B treatment; and no duplicate or structural overlap survives packing.
- The first exact attempt was invalid because Transformers 5 returned a
  `BatchEncoding` and the adapter counted its two fields instead of its
  `input_ids`. No LLM calls were made. The adapter now extracts `input_ids`,
  carries a versioned provenance field and self-tests chat-token count before
  the act loop. Old malformed metadata is rejected. All 74 tests pass.
- The scientific power warning remains: H1 has only 4 incremental-rescue
  sentences across 4 acts (H2: 11 sentences across 9 acts). Technical gate
  success does not make H1 adequately powered; a documented go/no-go or
  pre-generation amendment is required before the full run.
- A 10–15 act pilot is an engineering/manual-QA gate, not a hypothesis test.
  It must include acts where A differs from Base and B differs from A so that
  both treatments and both hierarchy stages can actually be inspected.

## Pre-generation design amendment — citation-conditioned evidence (2026-08-11)

This amendment was agreed before any v2 summary-generation call. The corrected
raw-target context audit above remains an engineering baseline and is retained;
it will not be overwritten or presented as the final treatment representation.

The raw resolved target provision is often much broader than the fact needed by
the passage containing its citation. Injecting the whole target can spend scarce
prompt budget on unrelated legal material and make the hierarchy preserve the
wrong details. The final v2 treatment therefore uses a fixed, non-agentic,
two-stage **citation-conditioned evidence card**:

1. Given the supporting source passage and resolved target location—but not the
   target text—Llama identifies the precise information need created by that
   citation (definition, scope, condition, exception, obligation, permission,
   prohibition, procedure, threshold or dependency). It may abstain when the
   citation adds no material information.
2. Given that frozen need and only the resolved target provision, Llama extracts
   a compact answer with verbatim target support spans. It must return
   `insufficient_evidence` rather than use outside knowledge.
3. A separate Llama-3.3-70B verification prompt checks that every card is
   supported by the target and answers the need. Only cards receiving `pass`
   are eligible for packing.

This is preprocessing, not an autonomous agent: there is no search, tool-choice
loop, internet access, gold-summary access or variable-hop exploration. Calls,
prompts, model settings and responses are content-addressed and cached. The
source passage, target passage, need, support spans, model versions and judge
decision remain in audit artefacts; only the compact need and evidence enter the
summarisation prompt.

The transformation is applied identically to within-document candidates in A
and cross-document candidates in B. Candidate ranking, graph frontier, group
attachment and caps are frozen before card generation. An unusable card is an
audited abstention; raw target text is never used as a silent fallback. The gold
summary remains unavailable to Base, A, B and card construction.

Because card lengths differ from raw targets, all A/B contexts, treatment labels
and exact complete-prompt token audits must be rebuilt. Cards are attached to
the structural group of their supporting source passage (within-document target
position remains recorded as provenance), allowing Stage 1 to integrate the
dependency locally before Stage 2 composes the document summary. Base remains
raw focal-act evidence and Oracle remains the separately labelled target-leaking
diagnostic arm.

Before the full run, a deterministic 10–15 act engineering pilot must pass:

- every inserted card has verbatim target support spans and a judge `pass`;
- manual review finds no unsupported claim or materially omitted citation need;
- no raw graph target is mixed into a citation-card treatment;
- exact prompt caps, comparator ordering and 1% paired balance still pass;
- Stage 1 preserves material actors, conditions, exceptions, numbers and dates;
- Stage 2 remains grounded, coherent and 400–600 words.

The pilot is a quality gate, not an outcome comparison. The representation will
not be selected based on ROUGE, BERTScore or the gold-summary rescue labels.

Implementation note (same date, before summary generation): the deterministic
pilot contains 15 acts and 132 frozen source-target requests. A five-request
smoke test exposed a legal-modality error in which an extraction and judge could
misread `shall have the right`/`may` as duties. No such card entered a summary.
The final prompt and validator now (a) explicitly distinguish duties, rights and
permissions, (b) provide a deterministic target-internal locator for mandatory
duty sentences, and (c) fail closed when an obligation card contains no duty.
The corrected regression edge extracted the actual `shall not change`, `shall
agree` and `shall cover` duties with verbatim spans and passed the judge. An
initial Nemotron judge arm was then retired before context construction because
the new endpoint produced persistent model-specific 429/503 failures. The final
pipeline uses Llama 3.3 70B for a separate judge pass at temperature 0, plus the
deterministic span/modality gates and mandatory human pilot audit. This loses
model-level judge independence but gains reproducibility; old Nemotron-labelled
smoke artefacts are versioned and cannot mix with final cards. All 102 Phase-3
graph/context/cache/card/provider tests pass (110 including the Phase-1
regression tests).
The NVIDIA account limit is 40 requests/minute. Four- and then two-worker
launches caused overlapping 429/503 retries despite remaining below the nominal
minute-level limit; the earlier stable Phase-2/Claude runs were sequential.
Card preprocessing and hierarchical generation therefore default to **one
worker** with a conservative 20-RPM launch ceiling. Model latency normally makes
the actual rate much lower. Every initial call and retry passes through the same
global limiter, and 429/503 responses retain exponential backoff.

**Inference-provider amendment (2026-08-11, before any v2 summary call).** The
final NVIDIA Llama card artefact reached 16/132 records, then the account began
returning immediate 429 responses even with one worker after an uninterrupted
five-minute cooldown. Those 16 records are retained as an operational pilot but
will not be mixed into the experiment. The frozen card set will be regenerated
from request 1 under a new artefact tag using OpenRouter's exact
`meta-llama/llama-3.3-70b-instruct` model id, pinned to the CoreWeave FP16
endpoint with provider fallbacks disabled. Gateway, endpoint, quantisation,
actual response provider, response id and token usage are recorded; provider
routing is part of cache and resume identity. A five-card OpenRouter quality
pilot must pass deterministic validation and human comparison against the
NVIDIA pilot before all 132 cards are generated. The same frozen OpenRouter
configuration will then be used for hierarchical summaries; provider backends
must not be mixed within an experimental artefact.

The live CoreWeave gate completed on the same date. The first five-card run took
38.3 seconds for 13 calls with no provider error, but manual review caught one
card that grouped Commission recommendations under an umbrella description of
Article-6 decisions. That artefact was rejected as a quality pilot. Extraction
v1.4 and judge v1.2 now require exact preservation of formal act types
(decision, recommendation, proposal and opinion), with a deterministic
fail-closed relabelling check. The corrected five-card artefact produced two
accurate supported cards, two correct insufficient-evidence abstentions and one
conservative judge rejection; no incorrect card survived. It took 22.4 seconds
for eight uncached calls, and every live response recorded CoreWeave, FP16 and
the frozen model id. All 104 Phase-3 tests pass (112 with Phase-1 regressions).
The corrected 132-card generation may therefore resume from this five-card
checkpoint; the rejected first OpenRouter pilot remains versioned and excluded.

The corrected pilot then completed all **132/132** records. Outcomes are 69
usable supported cards, 47 insufficient-evidence abstentions, 10 judge
rejections, 4 not-needed citations and 2 need-validation errors. Seven records
contain explicit fail-closed stage errors (five malformed extraction JSON
responses and two invalid composite need types); none is usable evidence. All
69 supported records have non-empty evidence, verbatim spans and a passing
judge. Across 335 unique recorded responses, provider/model/precision checks
show zero departures from CoreWeave / the frozen Llama id / FP16. Recorded usage
is 233,009 prompt and 22,952 completion tokens (about USD 0.18 at the frozen
endpoint prices). During the run, one malformed extraction exposed a runner
defect: the writer raised while a pre-submitted thread pool continued draining
API calls. The run was stopped, validated cache entries were retained, and the
default one-worker path now processes and durably appends one card before
launching the next; malformed structured responses become audited abstentions.
The resumed writer completed in 306.5 seconds. The deterministic 30-card human
audit sheet (seed 41) has been generated and remains the next quality gate.

---

## 1. Why v2 was necessary

The v1 experiment produced a useful pilot result, but post-run review found
defects serious enough that its B-vs-A comparison is not a clean test of the
cross-document effect. v2 exists to make the comparison *valid*, not to make
it *positive*.

| # | v1 defect | Consequence | v2 fix |
|---|---|---|---|
| 1 | UID = `{doc_id}-{article_idx}-{path}`; the article index is shared by every paragraph/point inside an Article | Passages with the same path collided; `Corpus.by_uid` silently kept only the last, so some edges pointed at overwritten records | `uid_version="v2"`: `{doc_id}:v2:{ordinal:06d}:{path}`, per-document ordinal, uniqueness asserted at load |
| 2 | No duplicate or containment check | Article 5 and Article 5(2) could both enter one context, double-charging the budget for the same text | `paths_overlap`; duplicates and ancestor/descendant pairs rejected and logged |
| 3 | Centroid-ranked base list re-sorted by document position | "Drop the lowest-ranked passage" actually dropped whatever appeared last in the act | `base_ranked_indices` consumed in rank order; rank stored per candidate |
| 4 | Within-doc closure from the 12 in-context passages, cross-doc closure from a 50-passage frontier | A and B were not comparable — different search scopes | one `--frontier` (default 50) for both scopes |
| 5 | B built as `(within + cross)[:4]`, within first | Within-doc additions (mean 5.5/act) consumed the cap; **B was byte-identical to A for 47/80 acts** | `build_b` takes A's *used* additions explicitly and inserts them first; cross may displace only base |
| 6 | Budget in characters | Not what the model reads; conditions could differ materially | exact-token complete-prompt budgets with comparator-derived ceilings; treatment never longer and paired groups within 1% |
| 7 | Cache keyed on `(celex, condition)` | Identical prompts paid for twice; prompt edits did not invalidate | content-addressed SHA-256 over the full request payload |
| 8 | Targeted labels computed from candidate POOLS | Credited a condition for evidence it never received | labels computed from the evidence actually packed |
| 9 | Single-pass generation | Read ~5% of an act (12 of ~246 passages) | one-level hierarchy over four structural groups |

## 2. Conditions

All four use the same architecture and group boundaries. Each treatment uses
its comparator's achieved complete-prompt size as a ceiling and must remain
within the registered 1% paired tolerance. They differ **only** in which
evidence is packed.

| condition | evidence |
|---|---|
| **base** | focal-act passages in centroid-rank order |
| **A** | base + up to `--max-within` (4) ranked, verified citation-conditioned cards from within-document references, inserted first |
| **B** | **exactly** A's used within cards + up to `--max-cross` (4) ranked, verified cards from cross-document references, then base fill |
| **oracle** | base + reference-aligned passages — **target-leaking diagnostic arm** |

These are **not literal set supersets**: at a fixed budget, additions displace
base tokens. They are nested in their *required additions*, which is the
property the hypotheses need. Cross-document evidence can never displace an A
addition; it may displace only lower-ranked base evidence.

`build_base`, `build_a` and `build_b` do not accept a gold summary in their
signatures; a unit test asserts this.

## 3. Hierarchical design

    selected evidence  ->  one brief per non-empty group  ->  one final summary

One level only; no recursion.

**Grouping** is deterministic and derived solely from focal-act document order:

    group = min(floor(position_index * n_groups / n_passages), n_groups - 1)

Boundaries are computed once per act and shared by all conditions. Focal
passages use their own position; within-document additions use their target's
position; cross-document additions attach to the group of their best supporting
focal source. The gold summary is never used for grouping.

Community detection is **not** revived: it degenerated on this corpus (median
community size 1; only 40.2% of passages in a community of size >= 2).

**Stage 1** receives focal passages plus locally attached verified citation
cards and produces evidence-preserving notes per group — purpose and scope,
actors, rights and obligations, conditions and exceptions, definitions and
dependencies, numbers/dates/thresholds — from the supplied blocks only, with
stable evidence ids and `FOCAL` / `CITED_WITHIN` / `CITED_OTHER` provenance
tags. Stage 1 is never asked to compare conditions.

**Stage 2** composes the briefs into one 400–600 word plain-language summary:
no headings, bullets, preamble or evidence ids; no outside legal knowledge.

## 4. Defaults

| parameter | default |
|---|---|
| tokenizer | `meta-llama/Llama-3.3-70B-Instruct` (configurable; exact access required for generation) |
| `--n-groups` | 4 |
| `--group-input-tokens` | 1800 |
| `--stage1-max-tokens` | 256 |
| `--final-max-tokens` | 1024 |
| `--frontier` | 50 |
| `--max-within` / `--max-cross` | 4 / 4 |
| temperature | 0 |
| threshold | 0.60 (unchanged from v1) |
| paired prompt tolerance | 1% per structural group; a treatment may never be longer than its comparator |

Citation-card preprocessing uses Llama 3.3 70B at temperature 0 for need
analysis, extraction and a separately prompted support judge. The frozen
OpenRouter model id is `meta-llama/llama-3.3-70b-instruct`, served by CoreWeave
at FP16 with fallback disabled. Using the same model for extraction and judging
is disclosed as a limitation and is backed by deterministic
verbatim-span/modality checks plus human pilot audit. It does not replace the
exact Hugging Face tokenizer used for budget counting.

If the exact tokenizer is unavailable, `--dry-run
--allow-approximate-tokenizer` may produce a separately named `_approx`
structural audit. Approximate contexts are marked `valid_for_generation=false`
and are rejected by the generator.

## 5. Candidate ranking (reference-free)

Graph candidates are ordered by:

1. lowest supporting source rank;
2. highest target-to-focal-centroid similarity;
3. target UID as a stable tie-break.

Never by passage id. The gold summary and generated text are not used.

## 6. Targeted labels

Computed **after** contexts are frozen, from evidence actually packed:

    base_missed                  = coverage(base_actual) < 0.60
    a_actual_rescue              = base_missed AND coverage(A_actual) >= 0.60
    b_incremental_actual_rescue  = coverage(A_actual) < 0.60
                                   AND coverage(B_actual) >= 0.60
    oracle_actual_rescue         = base_missed AND coverage(oracle) >= 0.60

`b_incremental` is measured against **A**, not base, so B is credited only for
what within-document evidence did not already supply. The union of potential
A/B labels used in v1 is discarded.

Also recorded per act: whether A's context differs from base, whether B's
differs from A, whether B actually contains cross-document evidence, and
whether an inserted cross passage aligns with a gold sentence A missed.

## 7. Hypotheses

**PRIMARY H1** — B vs A, targeted coverage on `b_incremental_actual_rescue_idx`
only, paired by document. Report n, mean difference, 95% bootstrap CI,
Wilcoxon p, wins/ties/losses.

**SECONDARY H2** — A vs base, targeted coverage on `a_actual_rescue_idx`.

**Aggregate (descriptive)** — ROUGE-1/2/L, ROUGE-1 precision, BERTScore.
Expected to be insensitive at this effect size; reported without inference.

**Oracle** — diagnostic sensitivity analysis only. Its selection uses the
reference, so it cannot show that a deployable method works and is not used to
support any claim about A or B.

B vs A is reported across three populations together: all complete documents;
documents where B's context genuinely differs from A's; and the incremental-
rescue subset. Reporting all three prevents cherry-picking.

## 8. Power gate

`13_build_contexts_v2.py` blocks generation if fewer than `--min-b-treated`
(default 30) documents have a genuine B treatment with balanced A/B prompts.
`--allow-underpowered` permits writing a diagnostic audit but never marks a
failed-power artefact as generation-ready.

**n=30 is a minimum sanity threshold, not a guarantee of statistical power.**
It verifies structural treatment delivery. It does not guarantee an adequate
number of acts in the primary incremental-rescue subset; that count is a
separate pre-generation feasibility decision recorded in the amendment above.

## 9. Reporting language (binding)

- A contrast with p >= 0.05 is reported as **"no statistically detectable
  difference was observed"** — never as a confirmed null.
- No hypothesis is described as *proved*.
- The oracle arm is always labelled target-leaking.
- Candidate availability is never described as treatment delivery.

## 10. RePASs

RePASs is excluded from v2. The v1 run was stopped, and the metric has not been
validated for abstractive EUR-Lex summarisation. It does not contribute to the
headline verdict.

## 11. Deviations from v1

Retained from v1: corpus, split, threshold 0.60, embedding model, the
graph-scope A/B framing, and the equal-budget principle.

Changed: UIDs, overlap handling, ranking, frontier symmetry, treatment
construction, budgeting units, cache addressing, label definitions, and
single-pass -> one-level hierarchical generation.

**Note on hierarchical generation:** covering the whole act reduces what
within-document references can add, since more of the act is already present.
H2 may therefore be *harder* to detect in v2 than in v1. This is a known and
accepted consequence of using a better summariser; it is recorded here in
advance so the outcome cannot be reinterpreted later.

## 12. Execution order

1. inspect code and git status — done
2. implement v2 without altering v1 outputs — done
3. run unit tests — done (72 passed)
4. build/validate the v2.2 region-aware graph, no LLM calls — done
5. run the context-builder audit:
   - approximate structural audit — done; preliminary only
   - exact Llama-token audit — **done; engineering gates pass**
6. adjudicate a separate 100-edge v2.2 precision sample and publish
   stratum-level and weighted precision — **done (seed 389)**
7. review exact treatment delivery, actual H1/H2 rescue counts, prompt balance,
   and graph precision — done; **supervisor go/no-go decision pending because
   H1 contains only 4 acts**
8. freeze citation requests, build verifier-approved evidence cards and
   rebuild exact-token contexts under the amendment — **cards complete (132),
   deterministic 30-card human audit pending; context rebuild pending**
9. run a deterministic 10–15 document engineering pilot — pending
10. manually inspect cards, Stage-1 briefs and Stage-2 summaries, including evidence
   preservation, hallucination, word length and formatting — pending
11. run the frozen full experiment only if Steps 5–10 pass — pending

Steps 5–7 make no LLM generation calls. Steps 8, 9 and 11 incur API calls and may
start only after their preceding gates pass. No approximate-token artefact may
be used for either generation step.
