# EUR-Lex v2_2 graph precision audit results

Frozen graph sha256: `f4b9f0ad7203d986…`; UID version `v2`; sample seed 389.

`UNSURE` rows are reported but excluded from precision denominators.

| scope | population | weight | TRUE | FALSE | UNSURE | precision | 95% Wilson CI |
|---|---:|---:|---:|---:|---:|---:|---:|
| within | 87,074 | 0.895 | 49 | 1 | 0 | 0.980 | [0.895, 0.996] |
| cross | 10,259 | 0.105 | 50 | 0 | 0 | 1.000 | [0.929, 1.000] |

## Population-weighted overall precision

**0.982**, stratified-bootstrap 95% CI [0.946, 1.000] (10,000 resamples, seed 389).

The cross-document row is the most relevant precision estimate for
variant B. Overall precision is dominated by within-document edges and
must not be used to hide a weak cross-document result.
