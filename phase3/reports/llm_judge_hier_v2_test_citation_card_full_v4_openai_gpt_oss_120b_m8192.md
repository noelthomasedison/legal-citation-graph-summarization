# Phase 3 v2 — blinded LLM summary evaluation

Status: **complete** (80/80 acts).
Judge: `openai/gpt-oss-120b`, pinned to `coreweave` `fp4` with provider fallbacks disabled.

This is a **post-hoc diagnostic**, additional to ROUGE/BERTScore and the pre-registered hypothesis tests. For every act, Base/A/B/Oracle were anonymised and deterministically shuffled before the judge saw them. The gold summary and all four candidates were evaluated in the same request.

The gold summary is a public-facing comparison reference, not a guarantee that every extra candidate claim is false. No source act text was supplied, so legal detail absent from the gold cannot be independently assessed.

## Headline comparison scores

All scores use 1 (unusable) to 5 (excellent). `user` assesses a clear, accurate public-facing explanation; `legal` assesses preservation of the material legal meaning represented in the gold.

| condition | user comparison | legal comparison |
|---|---:|---:|
| base | 2.825 | 2.987 |
| A | 2.763 | 3.000 |
| B | 2.725 | 2.975 |
| oracle | 3.163 | 3.325 |

## Diagnostic dimension scores

`macro` is the unweighted mean of the six diagnostic dimensions.

| condition | macro | fidelity | coverage | salience | lay clarity | practical | concision |
|---|---:|---:|---:|---:|---:|---:|---:|
| base | 3.054 | 3.300 | 2.975 | 2.875 | 3.312 | 3.125 | 2.737 |
| A | 3.023 | 3.312 | 2.975 | 2.925 | 3.225 | 3.087 | 2.612 |
| B | 2.983 | 3.263 | 2.987 | 2.875 | 3.188 | 3.038 | 2.550 |
| oracle | 3.304 | 3.500 | 3.337 | 3.288 | 3.425 | 3.413 | 2.862 |

## Paired exploratory contrasts

These comparisons are descriptive/post-hoc, not new confirmatory tests.

| perspective | contrast | n | mean difference | 95% bootstrap CI | Wilcoxon p | W/T/L |
|---|---|---:|---:|---:|---:|---:|
| user | A-base | 80 | -0.062 | [-0.200, +0.075] | 0.3863 | 11/53/16 |
| user | B-A | 80 | -0.037 | [-0.100, +0.025] | 0.2568 | 2/73/5 |
| user | oracle-base | 80 | +0.338 | [+0.163, +0.537] | 0.0008303 | 26/45/9 |
| legal | A-base | 80 | +0.013 | [-0.113, +0.150] | 0.8405 | 11/57/12 |
| legal | B-A | 80 | -0.025 | [-0.100, +0.037] | 0.4795 | 3/72/5 |
| legal | oracle-base | 80 | +0.338 | [+0.150, +0.525] | 0.001083 | 26/44/10 |

## Diagnostic flag rates

| condition | material error | material omission | not confirmed by reference |
|---|---:|---:|---:|
| base | 10.0% | 48.8% | 56.2% |
| A | 7.5% | 46.2% | 55.0% |
| B | 7.5% | 42.5% | 53.8% |
| oracle | 8.8% | 40.0% | 50.0% |

## Provenance

- Actual providers: `{'CoreWeave': 80}`
- Usage: `{'prompt_tokens': 337377, 'completion_tokens': 156897, 'total_tokens': 494274}`
- Prompt version: `legal-user-rubric-v1`
- Run configuration hash: `de9fed6d55cfc9a0a46bf277c4fab1c567eda5e8ffddf260b6f56a501c2dcd05`
- Runtime this invocation: `33.0 minutes`
- Candidate condition mapping is retained in the machine-readable JSONL but was never included in judge prompts.
