# Phase 1 data audit

## Structured documents
- JSON files: 40
- Distinct DocumentIDs: 40
- Total passages: 13,732
- Passages per doc: min=10 (doc 8), median=128, max=2,220 (doc 13)
- Distinct PassageID shape patterns: 202
- Top 12 shapes: `9.9.9`×3182, `9.9`×1143, `9.9.9.(9)`×1038, `9)`×941, `A 9.9.(9)`×792, `9.9.9.A.9.`×606, `A 9.A 9.9.(9)`×587, `A9.A9.9.9`×543, `9.9.9.A`×504, `A 9.9.`×319, `A9.A9.9.A.9.`×296, `A 9.9.9.9.(9)`×255

## CrossReferenceData.csv (gold edges)
- Columns: ['SourceID', 'SourceDocumentID', 'SourcePassageID', 'SourcePassage', 'ReferenceText', 'ReferenceType', 'TargetID', 'TargetDocumentID', 'TargetPassageID', 'TargetPassage']
- Total rows: 1,628
- Rows with non-empty SourceID: 1,628
- ReferenceType distribution: {'External': 574, 'Internal': 986, 'Outsource': 68}
- Distinct source documents: 33
- Same-document edges: 987 | cross-document: 641
- Rows with empty TargetID: 68

## Join integrity (CSV ↔ structured JSON)
- SourceID found in JSON UIDs: 1,628/1,628 (100.0%)
- TargetID found in JSON UIDs: 1,524/1,560 (97.7%)
- (SourceDocumentID, SourcePassageID) joins to JSON: 1,623/1,628 (99.7%)
- (TargetDocumentID, TargetPassageID) joins to JSON: 1,492/1,560 (95.6%)
- Rows with ReferenceText: 1,628/1,628

## Verdict flags
- NOTE: gold edge count is 1,628 — update any '10,000+ edges' claim in deck/notes.
- SourceID join: OK (100.0%)
- TargetID join: OK (97.7%)
