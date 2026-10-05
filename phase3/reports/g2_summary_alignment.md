# Phase 3 gate G2 — does summary content come from CITED documents?

EUR-Lex-Sum (English). For every summary sentence we find its best match
in the act itself (FOCAL), in the acts it cites (CITED), and in an equal
number of acts it does **not** cite (RANDOM control). Semantic matching
with bge-small; document-level (no Article segmentation — justified by
the 01 probe, which showed summaries engage at instrument level).

**Scope:** 704 focal documents, 25,551 summary sentences.

## Similarity of a summary sentence to its best match

| Source | median similarity |
|---|---|
| FOCAL (the act itself) | 0.756 |
| CITED (acts it cites) | 0.706 |
| RANDOM (acts it does not cite) | 0.666 |

## Headline

- summary sentences whose best match is in a CITED act rather than the focal act: **23.9%**
- summary sentences matching a CITED act better than a RANDOM act: **77.3%**  (50% = no signal)
- mean similarity lift of CITED over RANDOM: **+0.0405**
- alignment coverage (matches FOCAL or CITED above 0.6): 98.7%
- sentences covered ONLY by a cited act (not by the focal act): **1.3%**

### Threshold sensitivity (the headline must not hinge on one cut)

| threshold | coverage (focal or cited) | ONLY cited |
|---|---|---|
| 0.60 | 98.7% | **1.3%** |
| 0.65 | 94.1% | **1.9%** |
| 0.70 | 82.8% | **3.8%** |
| 0.75 | 57.1% | **3.5%** |
| 0.80 | 27.5% | **1.8%** |

## G2b — the fair test: a BUDGETED summariser

The figures above assume the summariser can read the **whole** act
(~13,000 words). A real long-document summariser reads a selection.
Here we give it the first B chunks (lead) or the B chunks closest to the
document centroid, then ask: of the summary sentences its selection does
NOT cover, how many are recoverable by following a citation? This is the
direct analogue of the CUAD rescue-arm population.

| selector | budget (chunks) | sentences missed | of those, recoverable via citations |
|---|---|---|---|
| lead | 10 (~1,800 words) | 7.5% (1,918) | **68.9%** |
| centroid | 10 (~1,800 words) | 9.5% (2,427) | **72.1%** |
| lead | 20 (~3,600 words) | 4.9% (1,244) | **63.7%** |
| centroid | 20 (~3,600 words) | 6.8% (1,745) | **68.1%** |
| lead | 40 (~7,200 words) | 3.5% (899) | **58.2%** |
| centroid | 40 (~7,200 words) | 4.7% (1,206) | **63.9%** |

## How to read this

The RANDOM control is the load-bearing comparison. EU legal texts share
vocabulary and register, so a summary sentence will resemble *any* act to
some degree. Citation dependence is only demonstrated if CITED beats
RANDOM: at 50% the 'linkage' would be generic legal-language similarity
rather than evidence that the summary draws on the cited material.

**Which number decides the gate.** The whole-document 'ONLY cited' figure
is the pessimistic bound: it assumes the summariser reads all ~13,000
words, so the focal act gets every chance to cover the summary itself.
The G2b table is the fair test, because real long-document summarisers
work from a selection. If the recoverable-via-citations column is high at
realistic budgets, the graph has a job to do even though the focal act
dominates when fully available.

Anchors from Phase 2: ObliQA 0.5% linkage produced a guaranteed null;
CUAD 3.2% rescueable produced a real effect that fired rarely; XRef 90%
produced large gains. A summarisation corpus should sit well above the
CUAD-marginal regime, because Phase 3 has no rescue-arm escape hatch —
there is no way to select only the questions where the graph fires.
