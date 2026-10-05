"""Phase 3 v2 — build base/A/B/oracle contexts. NO LLM CALLS, EVER.

This is the auditable dry run that must pass before any paid generation. It
packs every condition to the same per-group token budget, computes the targeted
labels from the evidence ACTUALLY selected (not candidate pools), and refuses
to hand off to generation unless enough documents receive a genuine B
treatment.

Guarantees enforced here (each was a v1 defect):
  * v2 UIDs, asserted unique
  * no duplicate and no ancestor/descendant pair inside one context
  * base consumed in CENTROID-RANK order, never re-sorted by document position
  * one frontier (default 50) for BOTH within- and cross-document closure
  * A's used additions retained verbatim in B; cross may displace only base
  * identical token budget per group across all four conditions
  * gold summary touched only for the oracle arm and for labelling AFTER
    base/A/B are frozen

It also exports the frozen source-target requests consumed by
19_build_citation_evidence_v2.py.  A later invocation can load those verified
cards and repack newly named citation-card contexts; raw target passages are
never silently mixed with cards.
"""
import argparse
import json
import random
import re
import statistics as st
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from context_v2 import (                                    # noqa: E402
    Candidate, CROSS, FOCAL, ORACLE, WITHIN,
    assign_group, build_a, build_b, build_base, build_oracle, context_hash,
    build_stage1_messages, group_boundaries, load_token_counter, overlaps_any,
    rank_graph_candidates, render_block, sha256_file, targeted_labels,
    treatment_flags,
)
from citation_evidence_v2 import (                           # noqa: E402
    SCHEMA_VERSION as CARD_SCHEMA_VERSION, card_is_usable,
    request_id as citation_request_id,
)
from regkg.textutil import clean                            # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
pick = ap.add_mutually_exclusive_group()
pick.add_argument("--n", type=int, default=80)
pick.add_argument("--act-list", type=Path,
                  help="JSON list or one CELEX id per line; preserves order")
ap.add_argument("--seed", type=int, default=41)
ap.add_argument("--n-groups", type=int, default=4)
ap.add_argument("--group-input-tokens", type=int, default=1800)
ap.add_argument("--frontier", type=int, default=50)
ap.add_argument("--max-within", type=int, default=4)
ap.add_argument("--max-cross", type=int, default=4)
ap.add_argument("--tokenizer", default="meta-llama/Llama-3.3-70B-Instruct")
ap.add_argument("--dry-run", action="store_true",
                help="build/audit contexts only; this script never calls an LLM")
ap.add_argument("--allow-approximate-tokenizer", action="store_true",
                help="with --dry-run only, permit a preliminary whitespace audit")
ap.add_argument("--min-b-treated", type=int, default=30)
ap.add_argument("--allow-underpowered", action="store_true")
ap.add_argument("--threshold", type=float, default=0.60)
ap.add_argument("--budget-tolerance-pct", type=float, default=1.0,
                help="maximum paired Stage-1 prompt difference per group")
ap.add_argument("--device", choices=("auto", "cpu", "mps"), default="auto",
                help="embedding device; auto tries MPS then falls back to CPU")
ap.add_argument("--graph-tag", default="v2_2",
                help="versioned graph artifact tag (default: audited v2_2)")
ap.add_argument("--segmentation-version", choices=("legacy", "region-v2"),
                default="region-v2")
ap.add_argument("--artifact-tag", default="",
                help="safe suffix for separate request/pilot/card artefacts")
ap.add_argument("--citation-evidence-cards", type=Path,
                help="verified JSONL cards produced by script 19")
ap.add_argument("--prepare-citation-cards", action="store_true",
                help="export the frozen card requests without loading cards")
args = ap.parse_args()

SPLIT = args.split
if not re.fullmatch(r"[a-zA-Z0-9_]+", args.graph_tag):
    sys.exit("--graph-tag may contain only letters, numbers and underscores")
if args.artifact_tag and not re.fullmatch(r"[a-zA-Z0-9_]+", args.artifact_tag):
    sys.exit("--artifact-tag may contain only letters, numbers and underscores")
EDGES = ROOT / "data" / f"eurlex_edges_{args.graph_tag}.jsonl"

if not EDGES.exists():
    sys.exit(f"run 12_build_graph_v2.py first ({EDGES.name} missing)")

# ---- tokenizer ----
try:
    counter = load_token_counter(
        args.tokenizer, dry_run=args.dry_run,
        allow_approximate=args.allow_approximate_tokenizer)
except Exception as e:                                    # noqa: BLE001
    sys.exit(str(e))
tok_meta = counter.provenance()
approximate = tok_meta["tokenizer_mode"] != "exact"
probe_messages = build_stage1_messages([], "counter self-test")
probe_content_tokens = sum(counter.count(m["content"]) for m in probe_messages)
probe_chat_tokens = counter.count_messages(probe_messages)
if probe_chat_tokens < probe_content_tokens:
    sys.exit(
        "tokenizer counter self-test failed: complete chat prompt counted as "
        f"{probe_chat_tokens} tokens but its message content alone is "
        f"{probe_content_tokens}; refusing to build generation contexts")
tok_meta["counter_probe"] = {
    "content_tokens": probe_content_tokens,
    "complete_chat_tokens": probe_chat_tokens,
    "passed": True,
}
tag_suffix = f"_{args.artifact_tag}" if args.artifact_tag else ""
approx_suffix = "_approx" if approximate else ""
suffix = f"{tag_suffix}{approx_suffix}"
OUT_CTX = ROOT / "data" / f"contexts_hier_v2_{SPLIT}{suffix}.json"
OUT_AUDIT = ROOT / "data" / f"context_audit_hier_v2_{SPLIT}{suffix}.json"
OUT_REPORT = ROOT / "reports" / f"context_audit_hier_v2{suffix}.md"
OUT_MANIFEST = ROOT / "data" / f"context_manifest_hier_v2_{SPLIT}{suffix}.json"
OUT_REQUESTS = ROOT / "data" / f"citation_evidence_requests_hier_v2_{SPLIT}{suffix}.jsonl"
tok_name = tok_meta.get("repository") or tok_meta["tokenizer_mode"]
if approximate:
    print("[tokenizer] PRELIMINARY whitespace audit enabled explicitly; "
          "outputs are not valid for generation", flush=True)

# ---- corpus + graph ----
print("loading corpus (uid_version=v2)...", flush=True)
from eurlex_ingest import load_eurlexsum                    # noqa: E402
corpus, id2celex, celex2id = load_eurlexsum(
    uid_version="v2", segmentation_version=args.segmentation_version)
assert len(corpus.passages) == len(corpus.by_uid)
print(f"  {len(corpus.passages):,} passages", flush=True)

outn = defaultdict(list)
edge_meta = {}
for line in open(EDGES):
    e = json.loads(line)
    if e["src"] != e["tgt"]:
        outn[e["src"]].append(e["tgt"])
        edge_meta[(e["src"], e["tgt"])] = {
            "mentions": tuple(e.get("mentions") or ()),
            "methods": tuple(e.get("methods") or ()),
            "keywords": tuple(e.get("keywords") or ()),
        }

# Verified card records are an optional, frozen input.  A card file may contain
# supported, insufficient and rejected records; only verifier-approved
# supported cards enter a model prompt.
cards = {}
cards_manifest = None
card_mode = args.citation_evidence_cards is not None
if args.prepare_citation_cards and card_mode:
    sys.exit("--prepare-citation-cards and --citation-evidence-cards are exclusive")
if args.prepare_citation_cards and not args.artifact_tag:
    sys.exit("--prepare-citation-cards requires --artifact-tag to preserve raw artefacts")
citation_design = args.prepare_citation_cards or card_mode
if card_mode:
    if approximate:
        sys.exit("citation-card contexts require the exact tokenizer")
    cards_path = args.citation_evidence_cards.resolve()
    if not cards_path.exists():
        sys.exit(f"citation evidence file not found: {cards_path}")
    for lineno, line in enumerate(cards_path.read_text().splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        rid = row.get("request_id")
        if not rid or rid in cards:
            sys.exit(f"invalid/duplicate card request_id at line {lineno}")
        if row.get("schema_version") != CARD_SCHEMA_VERSION:
            sys.exit(f"unsupported card schema at line {lineno}")
        cards[rid] = row
    cards_manifest_path = cards_path.with_name(cards_path.stem + "_manifest.json")
    if not cards_manifest_path.exists():
        sys.exit(f"citation evidence manifest missing: {cards_manifest_path.name}")
    cards_manifest = json.loads(cards_manifest_path.read_text())
    if cards_manifest.get("cards_sha256") != sha256_file(cards_path):
        sys.exit("citation evidence file hash does not match its manifest")
    print(f"loaded {len(cards):,} citation evidence records", flush=True)

# ---- summaries (gold): used ONLY for oracle + post-hoc labelling ----
from huggingface_hub import hf_hub_download                 # noqa: E402
gold = {}
p = hf_hub_download("dennlinger/eur-lex-sum", f"data/english/{SPLIT}.json",
                    repo_type="dataset")
for line in open(p):
    if line.strip():
        r = json.loads(line)
        gold[r["celex_id"]] = clean(r["summary"])

_SENT = re.compile(r"(?<=[.;:])\s+|\n+")
def sentences(t):
    return [s.strip() for s in _SENT.split(t or "") if len(s.strip().split()) >= 8]

cands_pool = [c for c in gold if c in celex2id
              and len(corpus.in_doc(celex2id[c])) >= 15]
if args.act_list:
    raw = args.act_list.read_text().strip()
    try:
        loaded = json.loads(raw)
        acts = loaded if isinstance(loaded, list) else loaded.get("celex_ids", [])
    except json.JSONDecodeError:
        acts = [x.strip() for x in raw.splitlines()
                if x.strip() and not x.lstrip().startswith("#")]
    if not acts or not all(isinstance(x, str) and x for x in acts):
        sys.exit("act list must contain CELEX strings")
    if len(acts) != len(set(acts)):
        sys.exit("act list contains duplicate CELEX ids")
    unavailable = [c for c in acts if c not in cands_pool]
    if unavailable:
        sys.exit(f"act list contains unavailable ids: {unavailable[:10]}")
else:
    acts = sorted(random.Random(args.seed).sample(
        cands_pool, min(args.n, len(cands_pool))))
print(f"  {len(acts)} acts selected (seed {args.seed})", flush=True)

import torch  # noqa: E402
from sentence_transformers import SentenceTransformer        # noqa: E402
_DEVICE = "mps" if torch.backends.mps.is_available() else "cpu"
if args.device == "auto":
    try:
        sbert = SentenceTransformer("BAAI/bge-small-en-v1.5", device=_DEVICE)
        embedding_device = _DEVICE
    except RuntimeError as e:
        print(f"[embedding] MPS unavailable ({e}); falling back to CPU",
              flush=True)
        sbert = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")
        embedding_device = "cpu"
else:
    sbert = SentenceTransformer("BAAI/bge-small-en-v1.5", device=args.device)
    embedding_device = args.device
QP = "Represent this sentence for searching relevant passages: "

CONDS = ("base", "A", "B", "oracle")
contexts, audit_rows = {}, []
tok_rows = []
citation_requests = {}
missing_card_ids = set()


def make_citation_request(cx, candidate, group):
    """Freeze the exact source-target relation before any LLM preprocessing."""
    if len(candidate.source_uids) != 1:
        raise ValueError(f"candidate {candidate.uid} lacks one best source")
    source_uid = candidate.source_uids[0]
    source = corpus.by_uid[source_uid]
    rid = citation_request_id(source_uid, candidate.uid, candidate.scope)
    row = {
        "schema_version": CARD_SCHEMA_VERSION,
        "request_id": rid, "celex": cx, "scope": candidate.scope,
        "group": group,
        "source_uid": source_uid,
        "source_doc": id2celex.get(source.doc_id, ""),
        "source_path": list(source.path), "source_text": clean(source.text),
        "target_uid": candidate.uid,
        "target_doc": candidate.target_doc,
        "target_path": list(candidate.path), "target_text": candidate.text,
        "citation_mentions": list(candidate.citation_mentions),
        "resolution_methods": list(candidate.resolution_methods),
        "citation_keywords": list(candidate.citation_keywords),
        "selection": {
            "best_source_rank": candidate.best_source_rank,
            "target_similarity": candidate.target_sim,
        },
    }
    previous = citation_requests.get(rid)
    if previous is not None and previous != row:
        raise ValueError(f"citation request collision for {rid}")
    citation_requests[rid] = row
    return row


def apply_card(candidate, request):
    """Return a card-backed candidate, None for an audited abstention."""
    if not card_mode:
        return candidate
    rid = request["request_id"]
    card = cards.get(rid)
    if card is None:
        missing_card_ids.add(rid)
        return None
    for field in ("source_uid", "target_uid", "scope"):
        if card.get(field) != request.get(field):
            raise ValueError(f"card {rid} does not match request field {field}")
    if not card_is_usable(card, require_judge=True):
        return None
    need = card.get("need") or {}
    evidence = clean(card["evidence"])
    return replace(
        candidate, text=evidence, tokens=counter.count(evidence),
        representation="citation_card",
        source_path=tuple(request["source_path"]),
        information_need=str(need.get("question", "")),
        support_spans=tuple(card.get("support_spans", [])),
        evidence_card_id=rid,
    )

for n_act, cx in enumerate(acts):
    d = celex2id[cx]
    ps = corpus.in_doc(d)                       # DOCUMENT ORDER preserved
    n_p = len(ps)
    texts = [clean(x.text) for x in ps]
    P = sbert.encode(texts, normalize_embeddings=True, batch_size=64,
                     show_progress_bar=False)
    centroid = P.mean(axis=0, keepdims=True)
    scores = (P @ centroid.T).ravel()

    # CENTROID RANK ORDER — never re-sorted by document position (v1 defect C)
    base_ranked_indices = np.argsort(-scores).tolist()
    rank_of = {idx: r for r, idx in enumerate(base_ranked_indices)}
    tokens_of = [counter.count(t) for t in texts]
    grp_of = [assign_group(i, n_p, args.n_groups) for i in range(n_p)]

    def focal_cand(i):
        return Candidate(uid=ps[i].uid, doc_id=d, path=tuple(ps[i].path),
                         text=texts[i], scope=FOCAL, group=grp_of[i],
                         tokens=tokens_of[i], centroid_score=float(scores[i]),
                         rank=rank_of[i])

    base_ranked = [focal_cand(i) for i in base_ranked_indices]

    # ---- graph candidates: ONE frontier for both scopes (v1 defect D) ----
    frontier = base_ranked_indices[: max(args.frontier, 1)]
    uid2i = {x.uid: i for i, x in enumerate(ps)}
    within_raw, cross_raw = {}, {}
    for i in frontier:
        for t in outn.get(ps[i].uid, []):
            if t in uid2i:                                   # same act
                j = uid2i[t]
                if j in rank_of and rank_of[j] < len(base_ranked):
                    prev = within_raw.get(t)
                    if prev is None or rank_of[i] < prev[1]:
                        within_raw[t] = (j, rank_of[i], ps[i].uid)
            elif t in corpus.by_uid:                         # other act
                prev = cross_raw.get(t)
                if prev is None or rank_of[i] < prev[0]:
                    cross_raw[t] = (rank_of[i], ps[i].uid)

    within_cands = []
    for t, (j, src_rank, src_uid) in within_raw.items():
        meta = edge_meta.get((src_uid, t), {})
        within_cands.append(Candidate(
            uid=t, doc_id=d, path=tuple(ps[j].path), text=texts[j],
            # Citation cards attach to the supporting source's local group.
            # The old raw-target design used the target position and is kept
            # only when citation_design is false for historical reproducibility.
            scope=WITHIN,
            group=(grp_of[uid2i[src_uid]] if citation_design else grp_of[j]),
            tokens=tokens_of[j],
            centroid_score=float(scores[j]), rank=rank_of[j],
            source_uids=(src_uid,), best_source_rank=src_rank,
            target_sim=float(scores[j]), target_doc=cx,
            citation_mentions=tuple(meta.get("mentions") or ()),
            resolution_methods=tuple(meta.get("methods") or ()),
            citation_keywords=tuple(meta.get("keywords") or ())))
    cross_cands = []
    if cross_raw:
        ctexts = [clean(corpus.by_uid[t].text) for t in cross_raw]
        CE = sbert.encode(ctexts, normalize_embeddings=True, batch_size=64,
                          show_progress_bar=False)
        sims = (CE @ centroid.T).ravel()
        for k, (t, (src_rank, src_uid)) in enumerate(cross_raw.items()):
            tp = corpus.by_uid[t]
            src_i = uid2i.get(src_uid)
            meta = edge_meta.get((src_uid, t), {})
            cross_cands.append(Candidate(
                uid=t, doc_id=tp.doc_id, path=tuple(tp.path), text=ctexts[k],
                scope=CROSS,
                group=grp_of[src_i] if src_i is not None else 0,
                tokens=counter.count(ctexts[k]),
                source_uids=(src_uid,), best_source_rank=src_rank,
                target_sim=float(sims[k]),
                target_doc=id2celex.get(tp.doc_id, ""),
                citation_mentions=tuple(meta.get("mentions") or ()),
                resolution_methods=tuple(meta.get("methods") or ()),
                citation_keywords=tuple(meta.get("keywords") or ())))
    within_cands = rank_graph_candidates(within_cands)
    cross_cands = rank_graph_candidates(cross_cands)

    # ---- oracle candidates: GOLD-SUMMARY-DEPENDENT, diagnostic only ----
    gs = sentences(gold[cx])
    S = sbert.encode([QP + s for s in gs], normalize_embeddings=True,
                     batch_size=64, show_progress_bar=False) if gs else None
    oracle_cands = []
    if S is not None:
        sim_sp = S @ P.T
        for i in sorted({int(x) for x in sim_sp.argmax(axis=1)}):
            oracle_cands.append(Candidate(
                uid=ps[i].uid, doc_id=d, path=tuple(ps[i].path), text=texts[i],
                scope=ORACLE, group=grp_of[i], tokens=tokens_of[i],
                centroid_score=float(scores[i]), rank=rank_of[i]))
        oracle_cands.sort(key=lambda c: c.rank)

    # ---- pack per group, same budget for every condition ----
    sel = {c: {} for c in CONDS}
    packres = {c: {} for c in CONDS}
    redundant_within = 0
    redundant_oracle = 0
    for g in range(args.n_groups):
        gbase = [c for c in base_ranked if c.group == g]
        gwith = [c for c in within_cands if c.group == g]
        gcross = [c for c in cross_cands if c.group == g]
        gorac = [c for c in oracle_cands if c.group == g]
        configured_budget = args.group_input_tokens
        group_label = f"group {g + 1}"

        # Base is constructed first. Its achieved COMPLETE-prompt size becomes
        # this act/group's effective budget. A short group therefore makes all
        # conditions shorter; graph evidence must replace focal evidence and
        # can never turn unused capacity into a longer treatment prompt.
        rb = build_base(gbase, configured_budget, counter, group_label)
        effective_budget = rb.prompt_tokens
        # A graph target already contained in a selected Base parent/child is
        # not new evidence. Do not replace the parent with its own descendant
        # and mislabel that reshuffling as reference augmentation.
        novel_gwith = [c for c in gwith if overlaps_any(c, rb.selected) is None]
        novel_gorac = [c for c in gorac if overlaps_any(c, rb.selected) is None]
        redundant_within += len(gwith) - len(novel_gwith)
        redundant_oracle += len(gorac) - len(novel_gorac)
        # Freeze only the candidates the registered max could insert.  Cards
        # are created for these relations, then either enter as verified compact
        # evidence or abstain; unrelated target text is never used as fallback.
        requested_within = []
        for candidate in novel_gwith[:args.max_within]:
            request = make_citation_request(cx, candidate, g)
            transformed = apply_card(candidate, request)
            if transformed is not None:
                requested_within.append(transformed)
        requested_cross = []
        for candidate in gcross[:args.max_cross]:
            request = make_citation_request(cx, candidate, g)
            transformed = apply_card(candidate, request)
            if transformed is not None:
                requested_cross.append(transformed)

        ra = build_a(gbase, requested_within, effective_budget, counter, group_label,
                     max_within=args.max_within)
        a_used = [c for c in ra.selected if c.scope == WITHIN]
        # B is compared with A, so A's achieved prompt size is B's ceiling.
        # Cross evidence must displace A's retained Base material, never turn
        # A's unused capacity into a longer B prompt.
        rbb = build_b(gbase, a_used, requested_cross, ra.prompt_tokens, counter,
                      group_label,
                      max_cross=args.max_cross)
        ro = build_oracle(gbase, novel_gorac, effective_budget, counter,
                          group_label)
        for name, r in (("base", rb), ("A", ra), ("B", rbb), ("oracle", ro)):
            sel[name][g] = r.selected
            packres[name][g] = r

    # ---- coverage of gold sentences by ACTUAL selected evidence ----
    cov = {}
    for name in CONDS:
        chosen = [c for g in range(args.n_groups) for c in sel[name][g]]
        if not gs or not chosen:
            cov[name] = [0.0] * len(gs)
            continue
        CT = sbert.encode([c.text for c in chosen], normalize_embeddings=True,
                          batch_size=64, show_progress_bar=False)
        cov[name] = (S @ CT.T).max(axis=1).tolist()

    labels = targeted_labels(cov["base"], cov["A"], cov["B"], cov["oracle"],
                             threshold=args.threshold)
    uids = {k: {c.uid for g in range(args.n_groups) for c in sel[k][g]}
            for k in CONDS}
    cross_in_b = {c.uid for g in range(args.n_groups) for c in sel["B"][g]
                  if c.scope == CROSS}
    flags = treatment_flags(uids["base"], uids["A"], uids["B"], cross_in_b)
    def selection_signature(name):
        return tuple((g, c.uid, c.text, c.scope)
                     for g in range(args.n_groups) for c in sel[name][g])
    flags["a_differs_from_base"] = (
        selection_signature("A") != selection_signature("base"))
    flags["b_differs_from_a"] = (
        selection_signature("B") != selection_signature("A"))

    a_prompt_delta = [packres["A"][g].prompt_tokens
                      - packres["base"][g].prompt_tokens
                      for g in range(args.n_groups)]
    b_prompt_delta = [packres["B"][g].prompt_tokens
                      - packres["A"][g].prompt_tokens
                      for g in range(args.n_groups)]
    tol = args.budget_tolerance_pct / 100.0
    a_balanced = all(
        abs(packres["A"][g].prompt_tokens - packres["base"][g].prompt_tokens)
        / max(packres["base"][g].prompt_tokens, 1) <= tol
        for g in range(args.n_groups))
    b_balanced = all(
        abs(packres["B"][g].prompt_tokens - packres["A"][g].prompt_tokens)
        / max(packres["A"][g].prompt_tokens, 1) <= tol
        for g in range(args.n_groups))
    a_used_all = [c for g in range(args.n_groups) for c in sel["A"][g]
                  if c.scope == WITHIN]
    b_within_sig = {(c.uid, c.text) for g in range(args.n_groups)
                    for c in sel["B"][g] if c.scope == WITHIN}
    b_retains_a = all((c.uid, c.text) in b_within_sig for c in a_used_all)
    a_primary_eligible = (flags["a_differs_from_base"] and bool(a_used_all)
                          and a_balanced)
    b_primary_eligible = (flags["b_differs_from_a"] and flags["b_has_cross"]
                          and b_retains_a and b_balanced)

    # does an inserted cross passage align with a gold sentence A missed?
    cross_aligned = False
    if cross_in_b and gs:
        idx_missed_by_a = [i for i, v in enumerate(cov["A"]) if v < args.threshold]
        if idx_missed_by_a:
            CT = sbert.encode([c.text for g in range(args.n_groups)
                               for c in sel["B"][g] if c.scope == CROSS],
                              normalize_embeddings=True, show_progress_bar=False)
            sub = S[idx_missed_by_a] @ CT.T
            cross_aligned = bool((sub.max(axis=1) >= args.threshold).any())

    per_cond = {}
    for name in CONDS:
        groups_out = {}
        for g in range(args.n_groups):
            blocks, meta = [], []
            for k, c in enumerate(sel[name][g]):
                eid = f"g{g+1}e{k+1}"
                blocks.append(render_block(c, eid))
                meta.append({"eid": eid, **c.as_record()})
            groups_out[str(g)] = {"blocks": blocks, "evidence": meta,
                                  "evidence_tokens": packres[name][g].tokens,
                                  "prompt_tokens": packres[name][g].prompt_tokens,
                                  "effective_base_prompt_budget":
                                      packres["base"][g].prompt_tokens,
                                  "displaced_base_uids":
                                      packres[name][g].displaced_base,
                                  "required_not_inserted":
                                      packres[name][g].required_not_inserted}
        tot = sum(packres[name][g].tokens for g in range(args.n_groups))
        prompt_tot = sum(packres[name][g].prompt_tokens
                         for g in range(args.n_groups))
        by_group_uids = {g: [c.uid for c in sel[name][g]]
                         for g in range(args.n_groups)}
        by_group_blocks = {g: groups_out[str(g)]["blocks"]
                           for g in range(args.n_groups)}
        per_cond[name] = {
            "groups": groups_out,
            "total_evidence_tokens": tot,
            "total_prompt_tokens": prompt_tot,
            "context_hash": context_hash(by_group_uids,
                                            args.group_input_tokens,
                                            args.n_groups,
                                            blocks_by_group=by_group_blocks),
            "n_focal": sum(1 for g in range(args.n_groups)
                           for c in sel[name][g] if c.scope == FOCAL),
            "n_within": sum(1 for g in range(args.n_groups)
                            for c in sel[name][g] if c.scope == WITHIN),
            "n_cross": sum(1 for g in range(args.n_groups)
                           for c in sel[name][g] if c.scope == CROSS),
            "n_oracle": sum(1 for g in range(args.n_groups)
                            for c in sel[name][g] if c.scope == ORACLE),
        }
        tok_rows.append({"celex": cx, "cond": name,
                         "evidence_tokens": tot,
                         "prompt_tokens": prompt_tot})

    contexts[cx] = {
        "celex": cx, "doc_id": d, "n_passages": n_p,
        "group_boundaries": [list(x) for x in
                             group_boundaries(n_p, args.n_groups)],
        "summary_sentences": gs,
        "conditions": per_cond,
        "labels": labels,
        "flags": {
            **flags,
            "cross_aligned_with_a_miss": cross_aligned,
            "a_prompt_balanced": a_balanced,
            "b_prompt_balanced": b_balanced,
            "b_retains_a_additions": b_retains_a,
            "a_primary_eligible": a_primary_eligible,
            "b_primary_eligible": b_primary_eligible,
        },
    }
    base_underfilled_groups = sum(
        packres["base"][g].prompt_tokens < args.group_input_tokens
        for g in range(args.n_groups))
    audit_rows.append({
        "celex": cx, "n_passages": n_p,
        **flags, "cross_aligned_with_a_miss": cross_aligned,
        "a_prompt_balanced": a_balanced,
        "b_prompt_balanced": b_balanced,
        "b_retains_a_additions": b_retains_a,
        "a_primary_eligible": a_primary_eligible,
        "b_primary_eligible": b_primary_eligible,
        "a_group_prompt_delta": a_prompt_delta,
        "b_group_prompt_delta": b_prompt_delta,
        "base_underfilled_groups": base_underfilled_groups,
        "within_candidates_already_in_base": redundant_within,
        "oracle_candidates_already_in_base": redundant_oracle,
        "n_base_missed": len(labels["base_missed_idx"]),
        "n_a_rescue": len(labels["a_actual_rescue_idx"]),
        "n_b_incremental": len(labels["b_incremental_actual_rescue_idx"]),
        "n_oracle_rescue": len(labels["oracle_actual_rescue_idx"]),
        # duplicates the packer REFUSED (correct behaviour, not a defect)
        "rejected_duplicate": sum(len(packres[c][g].rejected_duplicate)
                                  for c in CONDS for g in range(args.n_groups)),
        "rejected_overlap": sum(len(packres[c][g].rejected_overlap)
                                for c in CONDS for g in range(args.n_groups)),
        # duplicates that SURVIVED into a context (must be 0)
        "surviving_duplicate": sum(packres[c][g].n_duplicate_uids
                                   for c in CONDS for g in range(args.n_groups)),
        "surviving_overlap": sum(packres[c][g].n_surviving_overlaps
                                 for c in CONDS for g in range(args.n_groups)),
        "evidence_tokens": {
            c: per_cond[c]["total_evidence_tokens"] for c in CONDS},
        "prompt_tokens": {
            c: per_cond[c]["total_prompt_tokens"] for c in CONDS},
        "group_prompt_tokens": {
            c: [packres[c][g].prompt_tokens for g in range(args.n_groups)]
            for c in CONDS},
        "ctx_hash": {c: per_cond[c]["context_hash"] for c in CONDS},
    })
    if (n_act + 1) % 10 == 0:
        print(f"  built {n_act+1}/{len(acts)}", flush=True)

# Freeze the request universe before validating a supplied card file.
OUT_REQUESTS.parent.mkdir(parents=True, exist_ok=True)
OUT_REQUESTS.write_text("".join(
    json.dumps(citation_requests[rid], ensure_ascii=False) + "\n"
    for rid in sorted(citation_requests)))

# ---------------- audit ----------------
n = len(audit_rows)
a_diff = sum(r["a_differs_from_base"] for r in audit_rows)
b_diff = sum(r["b_differs_from_a"] for r in audit_rows)
b_cross = sum(r["b_has_cross"] for r in audit_rows)
a_eligible = sum(r["a_primary_eligible"] for r in audit_rows)
b_eligible = sum(r["b_primary_eligible"] for r in audit_rows)
b_aligned = sum(r["cross_aligned_with_a_miss"] for r in audit_rows)
has_a_res = sum(r["n_a_rescue"] > 0 for r in audit_rows)
has_b_inc = sum(r["n_b_incremental"] > 0 for r in audit_rows)
h1_sent = sum(r["n_b_incremental"] for r in audit_rows)
h2_sent = sum(r["n_a_rescue"] for r in audit_rows)
dups_rejected = sum(r["rejected_duplicate"] for r in audit_rows)
dups_surviving = sum(r["surviving_duplicate"] for r in audit_rows)
overs = sum(r["rejected_overlap"] for r in audit_rows)
overs_surviving = sum(r["surviving_overlap"] for r in audit_rows)
n_underfilled = sum(r["base_underfilled_groups"] > 0 for r in audit_rows)

def tk(c, field="prompt_tokens"):
    return [r[field][c] for r in audit_rows]

# Report paired prompt differences without allowing a short-document waiver.
# A/B eligibility requires <=1 token in every structural group.
pair_diffs = {}
for hi, lo in (("A", "base"), ("B", "base"), ("B", "A"), ("oracle", "base")):
    pct = [abs(r["prompt_tokens"][hi] - r["prompt_tokens"][lo])
           / max(r["prompt_tokens"][lo], 1) for r in audit_rows]
    group_abs = [abs(r["group_prompt_tokens"][hi][g]
                     - r["group_prompt_tokens"][lo][g])
                 for r in audit_rows for g in range(args.n_groups)]
    pair_diffs[f"{hi}-{lo}"] = {
        "mean_pct": 100 * st.mean(pct),
        "max_pct": 100 * max(pct),
        "max_group_tokens": max(group_abs, default=0),
    }

over_budget = sorted({r["celex"] for r in audit_rows for c in CONDS
                      for v in r["group_prompt_tokens"][c]
                      if v > args.group_input_tokens})
longer_than_comparator = sorted({
    r["celex"] for r in audit_rows
    for hi, lo in (("A", "base"), ("B", "A"), ("oracle", "base"))
    for g in range(args.n_groups)
    if r["group_prompt_tokens"][hi][g]
       > r["group_prompt_tokens"][lo][g]})
hash_equal = {f"{hi}=={lo}": sum(r["ctx_hash"][hi] == r["ctx_hash"][lo]
                                 for r in audit_rows)
              for hi, lo in (("A", "base"), ("B", "A"), ("oracle", "base"))}
sector = Counter(r["celex"][:1] for r in audit_rows if r["b_has_cross"])
gate_ok = b_eligible >= args.min_b_treated

problems = []
if over_budget:
    problems.append(f"{len(over_budget)} acts exceed a per-group prompt cap")
if longer_than_comparator:
    problems.append(
        f"{len(longer_than_comparator)} acts contain a treatment prompt longer "
        "than its paired comparator")
if dups_surviving:
    problems.append(f"{dups_surviving} duplicate UIDs survived packing")
if overs_surviving:
    problems.append(f"{overs_surviving} structural overlaps survived packing")
if card_mode and missing_card_ids:
    problems.append(
        f"{len(missing_card_ids)} frozen citation requests lack card records")
if card_mode and cards_manifest.get("requests_sha256") != sha256_file(OUT_REQUESTS):
    problems.append("citation cards were built from a different request artefact")
if not gate_ok and not args.allow_underpowered:
    problems.append(
        f"only {b_eligible} documents have a balanced genuine B treatment "
        f"(< {args.min_b_treated})")

valid_for_generation = bool(
    tok_meta["valid_for_generation"] and not problems
    and (gate_ok or args.allow_underpowered)
    and not args.prepare_citation_cards)
metadata = {
    "schema_version": "hier-v2.1",
    "created_utc": datetime.now(timezone.utc).isoformat(),
    "dataset": "dennlinger/eur-lex-sum",
    "split": SPLIT,
    "seed": args.seed,
    "n_acts": n,
    "parameters": {k: (str(v) if isinstance(v, Path) else v)
                   for k, v in vars(args).items()},
    "embedding_model": "BAAI/bge-small-en-v1.5",
    "embedding_device": embedding_device,
    "tokenizer": tok_meta,
    "approximate_structural_audit": approximate,
    "valid_for_generation": valid_for_generation,
    "zero_llm_calls": True,
    "evidence_representation": (
        "citation_card" if card_mode else
        "citation_card_request_export" if args.prepare_citation_cards else
        "raw_target"),
    "citation_evidence": {
        "request_artifact": str(OUT_REQUESTS.relative_to(ROOT)),
        "request_sha256": sha256_file(OUT_REQUESTS),
        "n_requests": len(citation_requests),
        "cards_artifact": (str(args.citation_evidence_cards.resolve())
                           if args.citation_evidence_cards else None),
        "cards_sha256": (sha256_file(args.citation_evidence_cards.resolve())
                         if args.citation_evidence_cards else None),
        "cards_manifest": cards_manifest,
        "missing_card_records": len(missing_card_ids),
        "usable_cards": sum(card_is_usable(x, require_judge=True)
                            for x in cards.values()),
    },
    "power_gate": {
        "minimum_b_treated": args.min_b_treated,
        "balanced_b_treated": b_eligible,
        "passed": gate_ok,
        "underpowered_pilot_override": bool(
            args.allow_underpowered and not gate_ok),
    },
    "budget_validation": {
        "per_group_prompt_cap": args.group_input_tokens,
        "over_budget_acts": over_budget,
        "treatment_longer_than_comparator_acts": longer_than_comparator,
        "surviving_duplicate_count": dups_surviving,
        "surviving_overlap_count": overs_surviving,
        "problems": problems,
    },
    "graph_sha256": sha256_file(EDGES),
    "graph_artifact": str(EDGES.relative_to(ROOT)),
}

OUT_CTX.parent.mkdir(parents=True, exist_ok=True)
json.dump({"schema_version": "hier-v2.1", "metadata": metadata,
           "contexts": contexts}, open(OUT_CTX, "w"))
json.dump({"schema_version": "hier-v2.1", "metadata": metadata,
           "rows": audit_rows}, open(OUT_AUDIT, "w"))

L = []
if approximate:
    L += ["# PRELIMINARY ONLY — approximate structural audit", "",
          "Word-based whitespace counting was used because the official Llama",
          "tokenizer was unavailable. This report is **not valid for final",
          "token-budget verification or LLM generation**.", ""]
L += ["# Phase 3 v2 — context audit (DRY RUN, zero LLM calls)", "",
     f"Split `{SPLIT}`, {n} acts, seed {args.seed}. Tokenizer: `{tok_name}`. ",
     f"{args.n_groups} groups x {args.group_input_tokens} tokens = "
     "a maximum complete Stage-1 prompt budget per group. Short Base groups",
     "set a smaller effective budget shared by every condition.", "",
     "## Treatment delivery (candidate availability is NOT delivery)", "",
     "| quantity | count |", "|---|---|",
     f"| sampled acts | {n} |",
     f"| A context differs from base | **{a_diff}** |",
     f"| B context differs from A | **{b_diff}** |",
     f"| B actually contains cross-document evidence | **{b_cross}** |",
     f"| A comparisons with genuine treatment and balanced prompts | "
     f"**{a_eligible}** |",
     f"| B comparisons with genuine treatment and balanced prompts | "
     f"**{b_eligible}** |",
     f"| inserted cross evidence aligns with a gold sentence A missed | {b_aligned} |",
     f"| acts with >=1 a_actual_rescue sentence | {has_a_res} |",
     f"| acts with >=1 b_incremental_actual_rescue sentence | **{has_b_inc}** |",
     "", "## Target sentences for the pre-registered hypotheses", "",
     f"- H1 (B vs A, incremental rescue): **{h1_sent}** sentences across "
     f"{has_b_inc} acts",
     f"- H2 (A vs base, actual rescue): **{h2_sent}** sentences across "
     f"{has_a_res} acts", "",
     "## Complete Stage-1 prompt budgets", "",
     "| condition | mean total | median total | max total |",
     "|---|---|---|---|"]
for c in CONDS:
    v = tk(c)
    L.append(f"| {c} | {st.mean(v):.0f} | {st.median(v):.0f} | {max(v)} |")
L += ["", "Paired prompt differences across all acts "
      f"(eligibility tolerance {args.budget_tolerance_pct:.1f}% per group):", ""]
for k, d in pair_diffs.items():
    L.append(f"- {k}: mean {d['mean_pct']:.2f}%, max {d['max_pct']:.2f}%; "
             f"largest group difference {d['max_group_tokens']} tokens")
L += ["",
      f"- acts with at least one underfilled Base group: {n_underfilled}/{n}",
      "- underfilled Base groups create a smaller effective budget; they do",
      "  **not** permit A, B or Oracle to receive a longer prompt",
      f"- acts exceeding a per-group prompt cap: **{len(over_budget)}**",
      f"- acts where any treatment group is longer than its comparator: "
      f"**{len(longer_than_comparator)}**",
      f"- duplicates REFUSED by the packer (correct): {dups_rejected} | "
      f"ancestor/descendant overlaps refused: {overs}",
      f"- duplicates that SURVIVED into a context (must be 0): "
      f"**{dups_surviving}**",
      f"- structural overlaps that SURVIVED (must be 0): "
      f"**{overs_surviving}**", "",
      "## Context-hash equality (identical hash = identical evidence)", ""]
for k, v in hash_equal.items():
    L.append(f"- {k}: {v}/{n}")
L += ["", "## Treatment by CELEX sector (B with cross evidence)", "",
      "  " + (", ".join(f"sector {k}: {v}" for k, v in sorted(sector.items()))
             or "none"), "",
      "## Citation evidence representation", "",
      f"- mode: **{'citation cards' if card_mode else 'citation-card request export' if args.prepare_citation_cards else 'raw targets'}**",
      f"- frozen source-target requests: **{len(citation_requests)}**",
      f"- verifier-approved usable cards loaded: "
      f"**{sum(card_is_usable(x, require_judge=True) for x in cards.values())}**",
      f"- missing card records: **{len(missing_card_ids)}**", "",
      "## Power gate", ""]
L += [f"- documents with balanced genuine B treatment: **{b_eligible}** "
      f"(minimum {args.min_b_treated})",
      f"- gate: **{'PASS' if gate_ok else 'UNDERPOWERED PILOT OVERRIDE' if args.allow_underpowered else 'FAIL'}**", "",
      "n=30 is a minimum sanity threshold, **not** a guarantee of statistical",
      "power. The explicit override permits an engineering pilot only; the",
      "full experiment must still pass this gate.", "",
      "## Provenance", "",
      f"- graph: `data/{EDGES.name}` sha256 "
      f"`{sha256_file(EDGES)[:16]}…`",
      f"- contexts: `data/{OUT_CTX.name}` sha256 `{sha256_file(OUT_CTX)[:16]}…`",
      f"- tokenizer mode: `{tok_meta['tokenizer_mode']}`",
      f"- valid for generation: **{str(valid_for_generation).lower()}**",
      "", "**Zero LLM calls were made by this script.**"]
OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
OUT_REPORT.write_text("\n".join(L) + "\n")
print("\n".join(L[4:]))

manifest = {**metadata,
            "context_sha256": sha256_file(OUT_CTX),
            "audit_sha256": sha256_file(OUT_AUDIT),
            "report_sha256": sha256_file(OUT_REPORT)}
OUT_MANIFEST.write_text(json.dumps(manifest, indent=2))

if problems:
    sys.exit("ABORT — dry-run checks failed:\n  " + "\n  ".join(problems))
print(f"\nwrote data/{OUT_CTX.name}, data/{OUT_AUDIT.name}, "
      f"data/{OUT_MANIFEST.name}, reports/{OUT_REPORT.name}")
