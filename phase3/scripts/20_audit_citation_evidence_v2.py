"""Create a deterministic manual-QA sheet for citation evidence cards.

No models, embeddings or gold summaries are loaded.  The sheet exposes the
source need, extracted card, exact support spans, judge decision and target
text so a human can mark each sampled record TRUE/FALSE before summarisation.
"""
import argparse
import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from citation_evidence_v2 import SCHEMA_VERSION, card_is_usable  # noqa: E402
from context_v2 import sha256_file                              # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--artifact-tag", required=True)
ap.add_argument("--requests", type=Path, required=True)
ap.add_argument("--n", type=int, default=30)
ap.add_argument("--seed", type=int, default=41)
args = ap.parse_args()

if args.n <= 0:
    sys.exit("--n must be positive")
CARDS = ROOT / "data" / f"citation_evidence_cards_hier_v2_{args.split}_{args.artifact_tag}.jsonl"
MANIFEST = CARDS.with_name(CARDS.stem + "_manifest.json")
OUT = ROOT / "reports" / f"citation_evidence_audit_{args.artifact_tag}.md"
OUT_JSON = ROOT / "data" / f"citation_evidence_audit_{args.artifact_tag}.json"
if not CARDS.exists() or not MANIFEST.exists() or not args.requests.exists():
    sys.exit("cards, card manifest or request artefact is missing")
manifest = json.loads(MANIFEST.read_text())
if manifest.get("cards_sha256") != sha256_file(CARDS):
    sys.exit("cards hash does not match manifest")
if manifest.get("requests_sha256") != sha256_file(args.requests):
    sys.exit("request hash does not match card manifest")

requests = {}
for line in args.requests.read_text().splitlines():
    if line.strip():
        row = json.loads(line)
        requests[row["request_id"]] = row
cards = []
for line in CARDS.read_text().splitlines():
    if not line.strip():
        continue
    row = json.loads(line)
    if row.get("schema_version") != SCHEMA_VERSION:
        sys.exit("unsupported card schema")
    if row["request_id"] not in requests:
        sys.exit(f"card has no frozen request: {row['request_id']}")
    cards.append(row)

# Stratify by scope and outcome, shuffle within each cell deterministically,
# then round-robin. This is an engineering sample and never uses gold outcomes.
strata = defaultdict(list)
for card in cards:
    strata[(card["scope"], card["status"])].append(card)
rng = random.Random(args.seed)
for values in strata.values():
    values.sort(key=lambda r: r["request_id"])
    rng.shuffle(values)
keys = sorted(strata)
sample = []
while len(sample) < min(args.n, len(cards)):
    progressed = False
    for key in keys:
        if strata[key] and len(sample) < min(args.n, len(cards)):
            sample.append(strata[key].pop())
            progressed = True
    if not progressed:
        break

rows = []
for index, card in enumerate(sample, 1):
    req = requests[card["request_id"]]
    rows.append({
        "audit_id": index, "request_id": card["request_id"],
        "scope": card["scope"], "status": card["status"],
        "human_need_valid": None,
        "human_supported": None, "human_answers_need": None,
        "human_outcome_correct": None,
        "human_notes": "",
    })

OUT_JSON.write_text(json.dumps({
    "schema_version": "citation-evidence-human-audit-v1.1",
    "seed": args.seed, "cards_sha256": sha256_file(CARDS), "rows": rows,
}, indent=2) + "\n")

counts = Counter(card["status"] for card in cards)
usable = sum(card_is_usable(card, True) for card in cards)
L = [
    "# Phase 3 v2 — citation evidence manual audit", "",
    f"Cards: `{CARDS.name}` (`{sha256_file(CARDS)[:16]}…`).",
    f"Deterministic engineering sample: {len(sample)}/{len(cards)}, seed {args.seed}.",
    "This sheet uses no gold summaries. Mark the matching JSON fields only after",
    "checking the need, card and complete target text.", "",
    "## Population", "",
    f"- usable supported cards: **{usable}/{len(cards)}**",
    "- statuses: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())),
    "",
]
for index, card in enumerate(sample, 1):
    req = requests[card["request_id"]]
    need = card.get("need") or {}
    judge = card.get("judge") or {}
    extraction = card.get("extraction") or {}
    review_evidence = card.get("evidence") or extraction.get("evidence") or ""
    review_spans = card.get("support_spans") or extraction.get("support_spans") or []
    evidence_label = ("**Proposed evidence card (rejected by model judge)**"
                      if card.get("status") == "rejected_by_judge" else
                      "**Proposed evidence card**")
    L += [
        f"## {index:03d} [{card['scope']}] {card['status']}", "",
        f"- Source: `{req['source_doc']}` / `{'.'.join(req['source_path'])}`",
        f"- Target: `{req['target_doc']}` / `{'.'.join(req['target_path'])}`",
        f"- Need type: `{need.get('need_type', '')}`",
        f"- Information need: {need.get('question') or '(abstained)' }",
        f"- Judge: `{judge.get('verdict', 'not_run')}` — "
        f"{judge.get('reason', '')}", "",
        "**Source passage**", "", req["source_text"], "",
        evidence_label, "",
        review_evidence or "*(none — audited abstention)*", "",
        "**Verbatim support spans**", "",
    ]
    L += ([f"> {span}" for span in review_spans] if review_spans else ["*(none)*"])
    L += ["", "**Complete resolved target**", "", req["target_text"], "",
          "Human need valid: `null`  |  Human supported: `null`  |  "
          "Human answers need: `null`  |  Human outcome correct: `null`  |  Notes: ` `",
          ""]

OUT.write_text("\n".join(L) + "\n")
print(f"cards: {len(cards)} | usable: {usable} | audit sample: {len(sample)}")
print(f"audit sheet -> {OUT.relative_to(ROOT)}")
print(f"audit judgements -> {OUT_JSON.relative_to(ROOT)}")
