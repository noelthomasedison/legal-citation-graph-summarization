# EUR-Lex v2 precision audit — AI-assisted initial adjudication

Date: 2026-08-11

Adjudicator: Codex AI, followed by required researcher verification. These
labels must not be described as an independent human-only audit. Noel should
personally review every FALSE row and all 50 cross-document rows before the
labels are treated as final.

## Decision rule

An edge is TRUE only when the source contains a genuine legal reference and
the displayed target is the correct act and provision. A shared number or
similar topic is insufficient. Ranges are TRUE when the target lies inside the
stated range. A relative paragraph must resolve within the named/current
Article. Annex/table numbering mistaken for an Article, wrong-instrument
routing, and duplicate heading/body artefacts are FALSE.

## Initial counts

- TRUE: 84/100
- FALSE: 16/100
- UNSURE: 0/100 after reopening the full source passages
- Within-document: 35 TRUE, 15 FALSE
- Cross-document: 49 TRUE, 1 FALSE

## FALSE rows and reasons

- **002** — “paragraph 1 of this Article” in Article 65(2) means Article 65(1),
  not Article 1.
- **005** — annex/table item 1.1.2 was misread as Article 1(1); the target text
  is unrelated.
- **010** — the source specifies Part Three, Title II, Chapter 2, but the target
  is the different Chapter 2 on prudential consolidation.
- **011** — a duplicate Article 5 heading/body collision links “Valuables” to
  the different Article 5 on global limitation of liability.
- **012** — annex subsection 2.3.2 was misread as Article 2(3).
- **014** — form/table item 6.1 (“Transport”) was misread as Article 6(1).
- **016** — the source explicitly cites Article 13(2) of Regulation 1031/2010,
  but the edge points to Article 13(2) of the focal Regulation 1122/2019.
- **017** — duplicate-alt heading/body artefact; the heading “Article 12: Ports
  and airports” is not a dependency reference.
- **021** — indicator 6.4 in an annex/table was misread as Article 6(4).
- **022** — duplicate-alt Article 15 heading/body artefact, not a dependency
  reference.
- **023** — the recital refers to Article 11 of the EU Charter, but the edge
  points to Article 11 of the focal Directive.
- **036** — “Annex X, Part 4” was misread as Article 4.
- **042** — “paragraph 2 of that Article” refers to Article 20(2), not Article 2.
- **043** — “paragraphs 2 to 9 of this Article” refers to Article 46(2–9), not
  Article 4.
- **048** — module/annex subsection 3.2 was misread as Article 3(2).
- **079** — the source cites point (15)(a) of Article 4(1) of Regulation
  575/2013, but the edge points to a different Article 4(1)(a) definition.

## Required researcher check

Review the rows above in
`reports/eurlex_audit_v2_sample.md`. Also review rows 050–099 because they are
the cross-document population relevant to Variant B. If any decision changes,
edit only its `label` in `data/eurlex_audit_v2_sample.jsonl`, record the reason,
and rerun `scripts/17_eurlex_audit_v2_results.py`.
