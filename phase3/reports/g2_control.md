# Phase 3 gate G2 — the deciding control

Script 02 measures how often citations recover summary content a budgeted
summariser misses. On its own that proves nothing: EU acts share
vocabulary and register, so *any* large pool of legal text recovers some
content. The test is whether acts the document **cites** beat an equal
number of acts it **does not cite**.

Scope: 25,551 summary sentences across 704 documents. Threshold 0.6.

## Cited vs random recovery of missed content

| selector | budget | missed | via CITED | via RANDOM | gap |
|---|---|---|---|---|---|
| lead | 10 chunks | 7.5% (1,918) | 68.9% | 59.4% | **+9.4** |
| centroid | 10 chunks | 9.5% (2,427) | 72.1% | 60.2% | **+11.9** |
| lead | 20 chunks | 4.9% (1,244) | 63.7% | 54.3% | **+9.4** |
| centroid | 20 chunks | 6.8% (1,745) | 68.1% | 57.4% | **+10.7** |
| lead | 40 chunks | 3.5% (899) | 58.2% | 49.5% | **+8.7** |
| centroid | 40 chunks | 4.7% (1,206) | 63.9% | 55.1% | **+8.8** |

## Significance (document-clustered bootstrap)

Centroid-10, the tightest realistic budget: gap **+11.9 points**, 95% CI **[+9.5, +14.5]** (2,000 resamples, seed 41).

Resampling is over **documents, not sentences** — sentences within one
summary are correlated, and treating them as independent would overstate
precision. The interval excludes zero, so the citation-specific advantage
is real rather than a pool-size artefact.

## Per-document view (the unit comparable to CUAD)

| budget | documents with >=1 rescuable sentence | mean share of summary rescuable |
|---|---|---|
| centroid-10 | **535/704 (76%)** | 6.4% |
| centroid-20 | **456/704 (65%)** | 4.3% |
| centroid-40 | **364/704 (52%)** | 2.8% |

## Verdict

**G2 PASSES.** Pre-registered bar was >= 15% of missed content recoverable
via citations; measured 58-72%, with a citation-specific advantage of
+8.7 to +11.9 points over the random control (CI excludes zero).

Two bounds to state honestly alongside it:

- **The effect is modest in absolute size.** Only 3.5-9.5% of summary
  sentences are missed under budget in the first place, so the total
  content at stake is ~5-9% of a summary — comparable to CUAD's rescue
  arm, not to XRef's large gains.
- **This is a similarity proxy, not an outcome.** It shows the missing
  information is reachable by following citations. Whether a summariser
  produces measurably better summaries with that material is the
  experiment this gate authorises, not something it establishes.

## Note on the pilot

A 25-document pilot showed the gap as *negative* (-2.7 to -7.4 points).
That was noise: it rested on 27-95 missed sentences per configuration
versus 899-2,427 here, and the sign reversed at scale. Recorded because
it is a concrete lesson about pilot sizing for effects of this magnitude.
