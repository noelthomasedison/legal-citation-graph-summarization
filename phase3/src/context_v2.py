"""Phase 3 v2 — context construction, budgeting, grouping, caching, labelling.

Shared logic for the v2 hierarchical experiment. v1 code and artefacts are
untouched; nothing here writes to a v1 path.

WHAT v2 FIXES (see PHASE3_V2_HIERARCHICAL_PLAN.md for the full account):

  UID collisions     v1 uids reused the Article index, so paragraphs/points of
                     one Article collided and Corpus.by_uid silently dropped
                     records. v2 uses a per-document ordinal.
  Duplicate/overlap  v1 could place both Article 5 and Article 5(2) in one
                     context, double-counting the same text against the budget.
  Ranking destroyed  v1 sorted the centroid-ranked base list by document
                     position, so "drop the lowest-ranked passage" actually
                     dropped whatever came last in the act.
  Asymmetric frontier v1 followed within-doc edges from the 12 in-context
                     passages but cross-doc edges from a 50-passage frontier.
  Treatment leakage  v1 built B as (within + cross)[:4] with within FIRST, so
                     the cap was consumed by within-doc additions and B was
                     byte-identical to A for 47/80 acts.
  Char budgets       v1 budgeted by characters, which does not correspond to
                     what the model actually reads.
  Cache by condition v1 keyed the cache on (celex, condition), so identical
                     prompts across conditions were paid for twice and a
                     prompt change did not invalidate anything.
  Candidate labels   v1 computed "rescueable" labels from candidate POOLS, not
                     from the evidence a condition actually received.

NOTHING HERE USES THE GOLD SUMMARY except `build_oracle` and the labelling
functions, which run only after Base/A/B contexts are frozen.
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field, asdict, replace
from typing import Callable, Iterable, Protocol, Sequence

# ---------------------------------------------------------------- tokenizer


class TokenCounter(Protocol):
    """Minimal interface so tests can inject a fake with no model download."""

    def count(self, text: str) -> int: ...

    def truncate(self, text: str, max_tokens: int) -> str: ...

    def count_messages(self, messages: Sequence[dict]) -> int: ...

    def provenance(self) -> dict: ...


class HFTokenCounter:
    """transformers tokenizer. Loaded lazily so imports stay cheap in tests."""

    counting_adapter_version = "hf-chat-template-input-ids-v2"

    def __init__(self, name: str = "meta-llama/Llama-3.3-70B-Instruct"):
        from transformers import AutoTokenizer
        self.name = name
        self._tok = AutoTokenizer.from_pretrained(name)
        self.tokenizer_mode = "exact"
        self.valid_for_generation = True

    def count(self, text: str) -> int:
        return len(self._tok.encode(text or "", add_special_tokens=False))

    def truncate(self, text: str, max_tokens: int) -> str:
        ids = self._tok.encode(text or "", add_special_tokens=False)
        if len(ids) <= max_tokens:
            return text
        return self._tok.decode(ids[:max_tokens], skip_special_tokens=True)

    def count_messages(self, messages: Sequence[dict]) -> int:
        """Count the complete chat prompt as the generation model sees it."""
        ids = self._tok.apply_chat_template(
            list(messages), tokenize=True, add_generation_prompt=True)
        # transformers 5 returns BatchEncoding, a mapping-like object that is
        # deliberately NOT a dict.  len(BatchEncoding) counts its fields
        # (normally input_ids + attention_mask), producing the impossible
        # value 2 instead of the token sequence length.  Extract input_ids for
        # both dict and BatchEncoding return types.
        if hasattr(ids, "get"):
            input_ids = ids.get("input_ids")
            if input_ids is not None:
                ids = input_ids
        if ids and isinstance(ids[0], (list, tuple)):
            if len(ids) != 1:
                raise ValueError("chat tokenizer unexpectedly returned a batch")
            ids = ids[0]
        return len(ids)

    def provenance(self) -> dict:
        config = {
            "init_kwargs": getattr(self._tok, "init_kwargs", {}),
            "special_tokens_map": getattr(self._tok, "special_tokens_map", {}),
        }
        try:
            backend = self._tok.backend_tokenizer.to_str()
        except Exception:  # slow tokenizers need not expose a backend
            backend = json.dumps(config, sort_keys=True, default=str)
        return {
            "tokenizer_mode": self.tokenizer_mode,
            "valid_for_generation": self.valid_for_generation,
            "repository": self.name,
            "resolved_revision": getattr(self._tok, "_commit_hash", None),
            "tokenizer_class": type(self._tok).__name__,
            "counting_adapter_version": self.counting_adapter_version,
            "vocab_size": int(getattr(self._tok, "vocab_size", 0)),
            "configuration_sha256": hashlib.sha256(
                json.dumps(config, sort_keys=True, default=str).encode()).hexdigest(),
            "vocabulary_sha256": hashlib.sha256(backend.encode()).hexdigest(),
        }


class WhitespaceTokenCounter:
    """Deterministic offline fallback/fake: 1 token per whitespace chunk."""

    name = "whitespace"
    tokenizer_mode = "approximate_whitespace"
    valid_for_generation = False

    def count(self, text: str) -> int:
        return len((text or "").split())

    def truncate(self, text: str, max_tokens: int) -> str:
        w = (text or "").split()
        return " ".join(w[:max_tokens])

    def count_messages(self, messages: Sequence[dict]) -> int:
        return sum(self.count(m.get("content", "")) for m in messages)

    def provenance(self) -> dict:
        return {
            "tokenizer_mode": self.tokenizer_mode,
            "valid_for_generation": self.valid_for_generation,
            "repository": None,
            "resolved_revision": None,
            "tokenizer_class": type(self).__name__,
            "counting_adapter_version": None,
            "vocab_size": None,
            "configuration_sha256": None,
            "vocabulary_sha256": None,
        }


class TokenizerAccessError(RuntimeError):
    """The exact generation tokenizer could not be loaded."""


def load_token_counter(name: str, *, dry_run: bool = False,
                       allow_approximate: bool = False,
                       factory=HFTokenCounter) -> TokenCounter:
    """Load the exact tokenizer, failing closed unless approximation is explicit.

    Approximate counting is permitted only for a no-LLM structural dry run.
    It is never a generation-ready substitute for the model tokenizer.
    """
    try:
        return factory(name)
    except Exception as exc:
        if dry_run and allow_approximate:
            return WhitespaceTokenCounter()
        raise TokenizerAccessError(
            f"Could not load exact tokenizer {name!r}: {type(exc).__name__}: "
            f"{exc}. Accept the model licence and authenticate with Hugging "
            "Face, or use --dry-run --allow-approximate-tokenizer for a "
            "preliminary structural audit only.") from exc


def validate_generation_metadata(metadata: dict) -> None:
    """Reject contexts that were not constructed with the exact tokenizer."""
    tok = metadata.get("tokenizer", {})
    if tok.get("tokenizer_mode") != "exact" or not tok.get(
            "valid_for_generation", False):
        raise ValueError(
            "context artefact is not generation-ready: exact tokenizer "
            "metadata is missing or tokenizer_mode is approximate")
    required = ("repository", "tokenizer_class", "counting_adapter_version",
                "vocab_size",
                "configuration_sha256", "vocabulary_sha256")
    missing = [k for k in required if tok.get(k) in (None, "")]
    if missing:
        raise ValueError("context tokenizer provenance missing: " + ", ".join(missing))


# ---------------------------------------------------------------- structures

FOCAL, WITHIN, CROSS, ORACLE = "FOCAL", "CITED_WITHIN", "CITED_OTHER", "ORACLE"


@dataclass
class Candidate:
    """One selectable evidence block.

    `rank` is the ORIGINAL retrieval rank (0 = most central). It is never
    recomputed by sorting on document position or UID — that was the v1 defect
    which made "drop the lowest-ranked" mean "drop whatever is last in the act".
    """
    uid: str
    doc_id: int
    path: tuple[str, ...]
    text: str
    scope: str                       # FOCAL | CITED_WITHIN | CITED_OTHER | ORACLE
    group: int
    tokens: int
    centroid_score: float = 0.0
    rank: int = 10**9                # original retrieval rank (focal only)
    source_uids: tuple[str, ...] = ()      # graph candidates: supporting sources
    best_source_rank: int = 10**9          # graph candidates: lowest source rank
    target_sim: float = 0.0                # graph candidates: sim to focal centroid
    target_doc: str = ""                   # graph candidates: CELEX of target
    representation: str = "raw"            # raw | citation_card
    source_path: tuple[str, ...] = ()       # supporting source for a card
    information_need: str = ""              # audited card question
    support_spans: tuple[str, ...] = ()     # retained in metadata, not prompt
    evidence_card_id: str = ""              # source-target relation hash
    citation_mentions: tuple[str, ...] = ()  # exact resolver mentions for this edge
    resolution_methods: tuple[str, ...] = () # resolver provenance for audit
    citation_keywords: tuple[str, ...] = ()  # detector keyword provenance

    def as_record(self) -> dict:
        d = asdict(self)
        d["path"] = list(self.path)
        d["source_uids"] = list(self.source_uids)
        d["source_path"] = list(self.source_path)
        d["support_spans"] = list(self.support_spans)
        d.pop("text", None)
        return d


# ---------------------------------------------------------------- overlap


def paths_overlap(p1: Sequence[str], p2: Sequence[str]) -> bool:
    """True when one path is a prefix of the other (structural containment).

    Article 5 vs Article 5(2) overlap: including both puts the same text in the
    context twice and charges the budget twice. Identical paths also overlap.
    Callers must additionally check doc_id — this compares paths only.
    """
    a, b = tuple(p1), tuple(p2)
    n = min(len(a), len(b))
    return a[:n] == b[:n]


def overlaps_any(cand: Candidate, chosen: Iterable[Candidate]) -> Candidate | None:
    """Return the already-chosen candidate that `cand` collides with, if any."""
    for c in chosen:
        if c.uid == cand.uid:
            return c
        if c.doc_id == cand.doc_id and paths_overlap(c.path, cand.path):
            return c
    return None


# ---------------------------------------------------------------- grouping


def assign_group(position_index: int, n_passages: int, n_groups: int) -> int:
    """Deterministic contiguous structural group from document position only.

    Community detection is deliberately NOT revived: it degenerated on this
    corpus (median community size 1, 40.2% of passages in a community of size
    >= 2), so it would have been linear chunking with extra steps.
    """
    if n_passages <= 0:
        return 0
    g = (position_index * n_groups) // n_passages
    return min(g, n_groups - 1)


def group_boundaries(n_passages: int, n_groups: int) -> list[tuple[int, int]]:
    """[(start, end_exclusive)] per group; computed ONCE per focal act and
    shared by all four conditions."""
    out = []
    for g in range(n_groups):
        start = (g * n_passages + n_groups - 1) // n_groups if n_passages else 0
        # derive from assign_group so the two can never disagree
        idxs = [i for i in range(n_passages)
                if assign_group(i, n_passages, n_groups) == g]
        out.append((idxs[0], idxs[-1] + 1) if idxs else (start, start))
    return out


# ---------------------------------------------------------------- packing


@dataclass
class PackResult:
    selected: list[Candidate] = field(default_factory=list)
    tokens: int = 0
    rejected_duplicate: list[str] = field(default_factory=list)
    rejected_overlap: list[tuple[str, str]] = field(default_factory=list)
    displaced_base: list[str] = field(default_factory=list)
    truncated_uid: str | None = None
    truncated_to: int = 0
    exhausted: bool = False        # every eligible fill candidate was consumed
    blocks: list[str] = field(default_factory=list)
    prompt_tokens: int = 0         # COMPLETE Stage-1 prompt, not evidence only
    required_not_inserted: list[str] = field(default_factory=list)

    @property
    def n_duplicate_uids(self) -> int:
        """Duplicates that ACTUALLY survived into the selection (must be 0).

        Not to be confused with `rejected_duplicate`, which counts duplicates
        the packer correctly refused.
        """
        uids = [c.uid for c in self.selected]
        return len(uids) - len(set(uids))

    @property
    def n_surviving_overlaps(self) -> int:
        """Ancestor/descendant pairs that survived packing (must be zero)."""
        n = 0
        for i, left in enumerate(self.selected):
            for right in self.selected[i + 1:]:
                if (left.doc_id == right.doc_id and left.uid != right.uid
                        and paths_overlap(left.path, right.path)):
                    n += 1
        return n


def prompt_token_count(blocks: Sequence[str], group_label: str,
                       counter: TokenCounter) -> int:
    """Tokens of the COMPLETE Stage-1 prompt: system + wrapper + evidence.

    Budget equality is checked on this, not on evidence bodies alone, because
    the model reads the whole prompt. Labels and provenance tags are part of
    what a condition 'spends'.
    """
    msgs = build_stage1_messages(blocks, group_label)
    return counter.count_messages(msgs)


def pack_prompt(required: Sequence[Candidate], fill: Sequence[Candidate],
                target_prompt_tokens: int, counter: TokenCounter,
                group_label: str, eid_prefix: str = "e",
                min_block_tokens: int = 40) -> PackResult:
    """Pack so the COMPLETE Stage-1 prompt never exceeds `target_prompt_tokens`.

    THE CONTROL THIS ENFORCES. `target_prompt_tokens` is the EFFECTIVE BASE
    BUDGET — what Base actually managed to fill for this act/group, which for a
    short act is smaller than the configured maximum. A, B and Oracle are held
    to that same number, so graph evidence must DISPLACE base evidence rather
    than extend the prompt.

    Getting this wrong is how v1 confounded treatment with context volume: if B
    is allowed a longer prompt merely because Base ran out of material, any
    measured effect is partly just 'more text'.

    `required` (treatment evidence) is placed first and therefore survives;
    `fill` (base evidence, in centroid-rank order) is squeezed out from the
    bottom. A required block that will not fit is token-truncated against the
    complete prompt, and dropped if less than `min_block_tokens` survives —
    in which case it is reported as not inserted rather than silently shrunk
    to nothing.
    """
    res = PackResult()
    blocks: list[str] = []

    def would_be(extra_block: str) -> int:
        return prompt_token_count(blocks + [extra_block], group_label, counter)

    def largest_fitting(c: Candidate, eid: str) -> Candidate | None:
        """Largest token prefix fitting the complete rendered chat prompt.

        Chat tokenisation is not additive. Binary-search the body against the
        complete prompt instead of estimating label/header overhead.
        """
        lo, hi, best = 1, counter.count(c.text), None
        while lo <= hi:
            mid = (lo + hi) // 2
            body = counter.truncate(c.text, mid)
            short = replace(c, text=body, tokens=counter.count(body))
            if would_be(render_block(short, eid)) <= target_prompt_tokens:
                best = short
                lo = mid + 1
            else:
                hi = mid - 1
        return best

    def attempt(c: Candidate, is_required: bool) -> bool:
        clash = overlaps_any(c, res.selected)
        if clash is not None:
            if clash.uid == c.uid:
                res.rejected_duplicate.append(c.uid)
            else:
                res.rejected_overlap.append((c.uid, clash.uid))
            return False
        eid = f"{eid_prefix}{len(res.selected) + 1}"
        blk = render_block(c, eid)
        if would_be(blk) <= target_prompt_tokens:
            blocks.append(blk)
            res.selected.append(c)
            return True
        short = largest_fitting(c, eid)
        if short is not None and short.tokens >= min_block_tokens:
            blocks.append(render_block(short, eid))
            res.selected.append(short)
            res.truncated_uid = short.uid
            res.truncated_to = short.tokens
            return True
        if is_required:
            res.required_not_inserted.append(c.uid)
        return False

    for c in required:
        attempt(c, True)
    n_eligible, n_taken = 0, 0
    for c in fill:
        if overlaps_any(c, res.selected) is not None:
            clash = overlaps_any(c, res.selected)
            if clash.uid == c.uid:
                res.rejected_duplicate.append(c.uid)
            else:
                res.rejected_overlap.append((c.uid, clash.uid))
            continue
        n_eligible += 1
        if attempt(c, False):
            n_taken += 1
    res.exhausted = (n_taken == n_eligible)
    res.blocks = blocks
    res.tokens = sum(c.tokens for c in res.selected)
    res.prompt_tokens = prompt_token_count(blocks, group_label, counter)
    return res


def pack_group(required: Sequence[Candidate], fill: Sequence[Candidate],
               budget: int, counter: TokenCounter,
               allow_truncate: bool = True,
               min_truncate_tokens: int = 32) -> PackResult:
    """Pack one structural group to `budget` tokens.

    `required` are inserted first and in order (treatment evidence). `fill`
    supplies the remainder in its given order — which for base evidence is
    CENTROID RANK order, never document order.

    A final block may be truncated token-wise so every condition lands on the
    same effective budget; nothing is ever padded.
    """
    res = PackResult()

    def try_add(c: Candidate, is_fill: bool) -> bool:
        clash = overlaps_any(c, res.selected)
        if clash is not None:
            if clash.uid == c.uid:
                res.rejected_duplicate.append(c.uid)
            else:
                # keep the higher-ranked (numerically lower rank) passage
                res.rejected_overlap.append((c.uid, clash.uid))
            return False
        if res.tokens + c.tokens <= budget:
            res.selected.append(c)
            res.tokens += c.tokens
            return True
        return False

    for c in required:
        try_add(c, False)
    n_eligible_fill, n_fill_taken = 0, 0
    for c in fill:
        clash = overlaps_any(c, res.selected)
        if clash is not None:
            # record WHY it was refused, then skip: an ineligible block is not
            # evidence the budget could have held, so it must not count toward
            # the exhaustion test either
            if clash.uid == c.uid:
                res.rejected_duplicate.append(c.uid)
            else:
                res.rejected_overlap.append((c.uid, clash.uid))
            continue
        n_eligible_fill += 1
        if try_add(c, True):
            n_fill_taken += 1
    # exhausted == the budget never bound: every eligible block already fits
    res.exhausted = (n_fill_taken == n_eligible_fill)

    if allow_truncate:
        room = budget - res.tokens
        if room >= min_truncate_tokens:
            for c in fill:
                if any(s.uid == c.uid for s in res.selected):
                    continue
                if overlaps_any(c, res.selected) is not None:
                    continue
                short = Candidate(**{**asdict(c),
                                     "path": tuple(c.path),
                                     "source_uids": tuple(c.source_uids)})
                short.text = counter.truncate(c.text, room)
                short.tokens = counter.count(short.text)
                if short.tokens == 0:
                    continue
                res.selected.append(short)
                res.tokens += short.tokens
                res.truncated_uid = short.uid
                res.truncated_to = short.tokens
                break
    return res


# ---------------------------------------------------------------- conditions
#
# Base/A/B signatures take NO gold summary. Only build_oracle does, and it is a
# target-leaking diagnostic arm.


def build_base(base_ranked: Sequence[Candidate], budget: int,
               counter: TokenCounter, group_label: str = "group") -> PackResult:
    """Focal-act evidence only, in centroid-rank order.

    `budget` is the CONFIGURED MAXIMUM. Base may not reach it (a short act with
    few passages). Whatever Base achieves — `result.prompt_tokens` — becomes
    the EFFECTIVE BUDGET for every other condition on this act/group.
    """
    return pack_prompt([], base_ranked, budget, counter, group_label)


def build_a(base_ranked: Sequence[Candidate],
            within_candidates: Sequence[Candidate],
            effective_budget: int, counter: TokenCounter,
            group_label: str = "group", max_within: int = 4) -> PackResult:
    """Base + up to `max_within` within-document additions, SAME prompt budget.

    Additions go in first and base evidence is squeezed out from the
    lowest-ranked end. `effective_budget` must be Base's achieved prompt token
    count, so A can never be longer than Base.
    """
    req = list(within_candidates)[:max_within]
    res = pack_prompt(req, base_ranked, effective_budget, counter, group_label)
    base_only = build_base(base_ranked, effective_budget, counter, group_label)
    kept = {c.uid for c in res.selected}
    res.displaced_base = [c.uid for c in base_only.selected if c.uid not in kept]
    return res


def build_b(base_ranked: Sequence[Candidate],
            a_used_within: Sequence[Candidate],
            cross_candidates: Sequence[Candidate],
            effective_budget: int, counter: TokenCounter,
            group_label: str = "group", max_cross: int = 4) -> PackResult:
    """A's used within additions + cross additions, SAME prompt budget.

    Order of priority: A's additions, then cross additions, then base fill.
    Cross evidence therefore displaces the lowest-ranked BASE evidence and can
    never evict an A addition, and B is never longer than Base.

    A short act does NOT earn B a bigger prompt — that would confound the
    treatment with context volume, which is the v1 defect this whole rebuild
    exists to remove.
    """
    req = list(a_used_within) + list(cross_candidates)[:max_cross]
    res = pack_prompt(req, base_ranked, effective_budget, counter, group_label)
    base_only = build_base(base_ranked, effective_budget, counter, group_label)
    kept = {c.uid for c in res.selected}
    res.displaced_base = [c.uid for c in base_only.selected if c.uid not in kept]
    return res


def build_oracle(base_ranked: Sequence[Candidate],
                 oracle_candidates: Sequence[Candidate],
                 effective_budget: int, counter: TokenCounter,
                 group_label: str = "group", max_oracle: int = 4) -> PackResult:
    """TARGET-LEAKING DIAGNOSTIC ARM. Same effective budget as every condition.

    `oracle_candidates` are chosen by the caller USING THE GOLD SUMMARY. Not
    deployable; a sensitivity bound, never evidence that the method works.
    """
    req = list(oracle_candidates)[:max_oracle]
    return pack_prompt(req, base_ranked, effective_budget, counter, group_label)


# ---------------------------------------------------------------- ranking


def rank_graph_candidates(cands: Sequence[Candidate]) -> list[Candidate]:
    """Deterministic, reference-free ordering for graph evidence.

    1. lowest supporting source rank  (reached from better-ranked evidence)
    2. highest target-to-focal-centroid similarity
    3. target UID as a stable tie-break

    Explicitly NOT sorted by passage id — that was a v1 defect which made
    selection an artefact of numbering.
    """
    return sorted(cands, key=lambda c: (c.best_source_rank, -c.target_sim, c.uid))


# ---------------------------------------------------------------- cache


def payload_hash(model: str, prompt_version: str, stage: str,
                 temperature: float, max_tokens: int,
                 messages: Sequence[dict],
                 request_options: dict | None = None) -> str:
    """SHA-256 over the COMPLETE request.

    Content-addressed, so identical Stage-1 prompts across conditions reuse one
    brief, and changing any prompt text, model or token limit invalidates the
    entry. v1 keyed on (celex, condition), which did neither.
    """
    payload = {
        "model": model,
        "prompt_version": prompt_version,
        "stage": stage,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
    }
    if request_options:
        payload["request_options"] = request_options
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def generation_settings_hash(model: str, prompt_version: str,
                             temperature: float, stage1_max_tokens: int,
                             final_max_tokens: int,
                             request_options: dict | None = None) -> str:
    """Stable identity of every setting that can change a generated row.

    Resume checks use this in addition to context and request hashes. In
    particular, changing only the Stage-2 token limit must invalidate an old
    completed row even though its Stage-1 hashes remain unchanged.
    """
    payload = {
        "model": model,
        "prompt_version": prompt_version,
        "temperature": temperature,
        "stage1_max_tokens": stage1_max_tokens,
        "final_max_tokens": final_max_tokens,
    }
    if request_options:
        payload["request_options"] = request_options
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def context_hash(selected_uids_by_group: dict, budget: int, n_groups: int,
                 blocks_by_group: dict | None = None) -> str:
    """Stable identity of a packed context, including truncated block text."""
    payload = {"g": {str(k): list(v) for k, v in
                     sorted(selected_uids_by_group.items())},
               "budget": budget, "n_groups": n_groups}
    if blocks_by_group is not None:
        payload["blocks"] = {str(k): list(v) for k, v in
                             sorted(blocks_by_group.items())}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- prompts
#
# One-level hierarchy ONLY:  selected evidence -> N group briefs -> summary.

PROMPT_VERSION = "hier-v2.1-citation-cards"

STAGE1_SYS = (
    "You are a legal analyst preparing evidence notes from provisions of an EU "
    "legal act. Work ONLY from the supplied evidence blocks. Preserve: purpose "
    "and scope; who it applies to; rights and obligations; conditions and "
    "exceptions; definitions and dependencies; and all numbers, dates and "
    "thresholds. A CITATION_CARD contains only the part of a resolved target "
    "provision needed by its supporting source passage; treat it as supporting "
    "evidence, not as an independent topic. Write compact structured notes, "
    "not polished prose. Keep the "
    "evidence id in square brackets after each note so it can be audited. Do "
    "not add legal knowledge from outside the supplied blocks."
)

STAGE2_SYS = (
    "You are writing the official plain-language summary of an EU legal act for "
    "the EUR-Lex summaries series. Compose the supplied group notes into ONE "
    "flowing summary of 400-600 words. Remove repetition. Preserve important "
    "qualifications and exceptions. Use ONLY the supplied notes; add no outside "
    "legal knowledge. Do not use headings, bullet points, preamble, or evidence "
    "ids in your output."
)


def render_block(c: Candidate, eid: str) -> str:
    """Evidence block with a stable id and provenance tag."""
    tag = {FOCAL: "FOCAL", WITHIN: "CITED_WITHIN",
           CROSS: "CITED_OTHER", ORACLE: "ORACLE"}.get(c.scope, c.scope)
    loc = ".".join(c.path)
    if c.representation == "citation_card":
        src = ".".join(c.source_path) or "unknown"
        return (f"[{eid} | {tag} | CITATION_CARD | SOURCE Article {src} -> "
                f"TARGET {c.target_doc} Article {loc}]\n"
                f"Information need: {c.information_need}\n"
                f"Relevant cited information: {c.text}")
    return f"[{eid} | {tag} | Article {loc}]\n{c.text}"


def build_stage1_messages(blocks: Sequence[str], group_label: str) -> list[dict]:
    body = "\n\n".join(blocks)
    return [{"role": "system", "content": STAGE1_SYS},
            {"role": "user",
             "content": f"EVIDENCE ({group_label}):\n\n{body}\n\n"
                        "Write the evidence notes."}]


def build_stage2_messages(briefs: Sequence[str]) -> list[dict]:
    body = "\n\n".join(f"GROUP {i + 1} NOTES:\n{b}" for i, b in enumerate(briefs))
    return [{"role": "system", "content": STAGE2_SYS},
            {"role": "user",
             "content": f"{body}\n\nWrite the final summary."}]


# ---------------------------------------------------------------- cache


class HierCache:
    """Content-addressed cache: one file per request-payload hash.

    Keyed on the payload, NOT on (celex, condition) as v1 was. Identical
    Stage-1 prompts arising in different conditions therefore share one entry,
    and any prompt/model/token change produces a different key.
    """

    def __init__(self, cache_dir):
        from pathlib import Path as _P
        self.dir = _P(cache_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.n_hits = 0
        self.n_writes = 0
        self._counter_lock = threading.Lock()

    def path_for(self, h: str):
        return self.dir / f"{h}.json"

    def get(self, h: str):
        row = self.get_entry(h)
        return None if row is None else row["response"]

    def get_entry(self, h: str, count_hit: bool = True):
        fp = self.path_for(h)
        if fp.exists():
            row = json.loads(fp.read_text())
            if row.get("request_hash") != h or not isinstance(row.get("response"), str):
                raise ValueError(f"invalid hierarchical cache entry: {fp.name}")
            if count_hit:
                with self._counter_lock:
                    self.n_hits += 1
            return row
        return None

    def put(self, h: str, response: str, meta: dict) -> None:
        self.path_for(h).write_text(json.dumps(
            {"request_hash": h, "response": response, **meta}))
        with self._counter_lock:
            self.n_writes += 1


class HierLLM:
    """Thin wrapper so tests can inject a fake backend and count calls.

    `backend(messages, temperature, max_tokens) -> str`. In --dry-run the
    backend is never invoked and `n_calls` must remain 0.
    """

    def __init__(self, backend: Callable, cache: HierCache, model: str,
                 prompt_version: str = PROMPT_VERSION, dry_run: bool = False,
                 request_options: dict | None = None):
        self.backend = backend
        self.cache = cache
        self.model = model
        self.prompt_version = prompt_version
        self.dry_run = dry_run
        self.request_options = request_options or {}
        self.n_calls = 0
        self._counter_lock = threading.Lock()
        self._hash_locks_guard = threading.Lock()
        self._hash_locks: dict[str, threading.Lock] = {}

    def complete(self, stage: str, messages: Sequence[dict],
                 temperature: float, max_tokens: int) -> tuple[str, str]:
        h = payload_hash(self.model, self.prompt_version, stage, temperature,
                         max_tokens, messages, self.request_options)
        with self._hash_locks_guard:
            request_lock = self._hash_locks.setdefault(h, threading.Lock())
        # Identical prompts from concurrent conditions share one actual call.
        with request_lock:
            hit = self.cache.get(h)
            if hit is not None:
                return hit, h
            if self.dry_run:
                return "", h
            from llm_provider_v2 import unpack_backend_response
            out, transport = unpack_backend_response(
                self.backend(messages, temperature, max_tokens))
            with self._counter_lock:
                self.n_calls += 1
            self.cache.put(h, out, {"model": self.model, "stage": stage,
                                    "prompt_version": self.prompt_version,
                                    "temperature": temperature,
                                    "max_tokens": max_tokens,
                                    "request_options": self.request_options,
                                    "transport": transport})
            return out, h

    def transport_for(self, h: str | None) -> dict | None:
        if h is None:
            return None
        row = self.cache.get_entry(h, count_hit=False)
        return None if row is None else row.get("transport", {})


def generate_hierarchical(group_blocks: Sequence[Sequence[str]], llm: HierLLM,
                          stage1_max_tokens: int = 256,
                          final_max_tokens: int = 1024,
                          temperature: float = 0.0) -> dict:
    """One-level hierarchy: one brief per NON-EMPTY group, then one composition.

    Never recurses. Returns the final summary plus every hash, so the run is
    auditable and resume-safe.
    """
    briefs, s1_hashes, s1_transport = [], [], []
    for gi, blocks in enumerate(group_blocks):
        if not blocks:
            continue                                   # no brief for empty groups
        msgs = build_stage1_messages(blocks, f"group {gi + 1}")
        text, h = llm.complete("stage1", msgs, temperature, stage1_max_tokens)
        briefs.append(text)
        s1_hashes.append(h)
        s1_transport.append(llm.transport_for(h))
    msgs2 = build_stage2_messages(briefs)
    final, h2 = llm.complete("stage2", msgs2, temperature, final_max_tokens)
    return {"summary": final, "briefs": briefs,
            "stage1_hashes": s1_hashes, "stage2_hash": h2,
            "stage1_transport": s1_transport,
            "stage2_transport": llm.transport_for(h2),
            "n_groups_used": len(briefs)}


# ---------------------------------------------------------------- labelling
#
# Runs ONLY after Base/A/B contexts are frozen. Labelling is evaluation, not
# retrieval selection.


THRESHOLD = 0.60


def coverage_flags(sent_sims: Sequence[float], threshold: float = THRESHOLD):
    return [s >= threshold for s in sent_sims]


def targeted_labels(cov_base: Sequence[float], cov_a: Sequence[float],
                    cov_b: Sequence[float], cov_oracle: Sequence[float] | None = None,
                    threshold: float = THRESHOLD) -> dict:
    """Labels from ACTUAL selected evidence, not candidate pools.

    base_missed                    coverage(base_actual)  < threshold
    a_actual_rescue                base_missed AND coverage(A_actual) >= threshold
    b_incremental_actual_rescue    coverage(A_actual) < threshold
                                   AND coverage(B_actual) >= threshold
    oracle_actual_rescue           base_missed AND coverage(oracle) >= threshold

    b_incremental is deliberately measured against A, not base: it isolates
    what CROSS-document evidence adds over within-document evidence, which is
    the primary hypothesis. v1 used the union of potential A/B labels, which
    credited B for content A already had.
    """
    n = len(cov_base)
    base_missed, a_res, b_inc, o_res = [], [], [], []
    for i in range(n):
        bm = cov_base[i] < threshold
        if bm:
            base_missed.append(i)
        if bm and cov_a[i] >= threshold:
            a_res.append(i)
        if cov_a[i] < threshold <= cov_b[i]:
            b_inc.append(i)
        if cov_oracle is not None and bm and cov_oracle[i] >= threshold:
            o_res.append(i)
    return {
        "base_missed_idx": base_missed,
        "a_actual_rescue_idx": a_res,
        "b_incremental_actual_rescue_idx": b_inc,
        "oracle_actual_rescue_idx": o_res,
    }


def treatment_flags(base_uids: set, a_uids: set, b_uids: set,
                    cross_uids_in_b: set) -> dict:
    """Did each condition actually receive a different treatment?

    Candidate availability is NOT treatment delivery — v1 conflated them and
    reported potential rescues for acts whose contexts were identical.
    """
    return {
        "a_differs_from_base": a_uids != base_uids,
        "b_differs_from_a": b_uids != a_uids,
        "b_has_cross": len(cross_uids_in_b) > 0,
        "n_cross_in_b": len(cross_uids_in_b),
    }
