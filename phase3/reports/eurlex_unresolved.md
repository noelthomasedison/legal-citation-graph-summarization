# EUR-Lex unresolved-mention diagnostics

Of 57,497 detected mentions, **25,708 resolved to nothing** (44.7%).

Sample of 200 failures, grouped by surface shape. A shape appearing often is a candidate RULE GAP; a shape that is genuinely out-of-corpus (citing an act we do not hold) is correct behaviour, not a defect.

| count | mention shape |
|---|---|
| 41 | `Article N` |
| 14 | `Article NC` |
| 12 | `Article NT` |
| 9 | `Article NF` |
| 9 | `Article NA` |
| 9 | `Article NI` |
| 8 | `Article NP` |
| 8 | `Article NS` |
| 7 | `Article NE` |
| 7 | `Article ND` |
| 7 | `Article NR` |
| 5 | `Article NM` |
| 4 | `N.N.N` |
| 4 | `Article N.N` |
| 4 | `Articles N` |
| 4 | `Article NG` |
| 3 | `paragraph N (a)` |
| 3 | `paragraph N (b)` |
| 3 | `Article NN` |
| 3 | `Article NB` |
| 3 | `N.N` |
| 3 | `and N` |
| 3 | `paragraph N.N` |
| 3 | `Article NH` |
| 2 | `Article N (b)` |
| 2 | `paragraph N(b)(i)` |
| 2 | `Article NO` |
| 2 | `paragraph N` |
| 2 | `, N` |
| 2 | `Article NL` |
| 1 | `Article N (a) (N)` |
| 1 | `Article N (g)` |
| 1 | `Article N (a) (ROMAN)` |
| 1 | `(d) of Article N` |
| 1 | `paragraph N(d)` |
| 1 | `paragraph N(c)` |
| 1 | `N (ROMAN)` |
| 1 | `N(N)` |
| 1 | `Chapter N` |
| 1 | `paragraph N(b)` |

## How to read

- **Correct failures:** references to acts outside the corpus, or to
  Annexes/instruments we deliberately do not model. Leaving these
  unresolved is the precision-preserving choice (the resolver refuses
  to guess), exactly as designed in Phase 1.
- **Rule gaps:** recurring EU-specific forms the ADGM grammar never
  saw. Suspected classes: `Annex ROMAN`, `Chapter ROMAN`, nested
  inverted forms. These are the only ones worth adapting rules for.
- Decide adaptation ONLY from this table plus the precision audit —
  not from the resolution rate alone.
