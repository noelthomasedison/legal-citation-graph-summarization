"""Unit tests for Phase 3 v2 context construction.

Synthetic passages only — no model or dataset downloads. Covers requirements
N1-N10 (UIDs, duplicates/overlap, ranking, treatment nesting, budgets, labels,
gold-summary isolation).
"""
import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from context_v2 import (                                    # noqa: E402
    Candidate, WhitespaceTokenCounter, FOCAL, WITHIN, CROSS,
    assign_group, build_a, build_b, build_base, build_oracle,
    group_boundaries, pack_group, paths_overlap, prompt_token_count,
    rank_graph_candidates, render_block, targeted_labels, treatment_flags,
)

TOK = WhitespaceTokenCounter()


def mk(uid, path, scope=FOCAL, rank=0, tokens=10, doc_id=1, **kw):
    text = " ".join(["w"] * tokens)
    return Candidate(uid=uid, doc_id=doc_id, path=tuple(path), text=text,
                     scope=scope, group=0, tokens=tokens, rank=rank, **kw)


def prompt_budget(cands, group_label="group"):
    blocks = [render_block(c, f"e{i + 1}") for i, c in enumerate(cands)]
    return prompt_token_count(blocks, group_label, TOK)


# ---------------------------------------------------------------- N1 uids
def test_v2_uids_unique_and_deterministic():
    from eurlex_ingest import segment_act
    text = ("Article 1\nSubject matter\n"
            "1. This Regulation lays down rules for the purposes described.\n"
            "2. It shall apply to all operators established in the Union.\n"
            "(a) point one describing a specific condition in some detail\n"
            "Article 2\nDefinitions\n"
            "1. For the purposes of this Regulation the following apply here.\n")
    a = segment_act(text, 7, "CELEX", uid_version="v2")
    b = segment_act(text, 7, "CELEX", uid_version="v2")
    assert [p.uid for p in a] == [p.uid for p in b], "v2 uids must be deterministic"
    assert len({p.uid for p in a}) == len(a), "v2 uids must be unique"
    assert all(":v2:" in p.uid for p in a)


def test_v1_uid_behaviour_preserved():
    """v1 remains the default and keeps its (colliding) scheme untouched."""
    from eurlex_ingest import segment_act
    text = ("Article 1\nSubject\n"
            "1. Paragraph one of article one with enough text to be kept.\n"
            "2. Paragraph two of article one with enough text to be kept.\n")
    v1 = segment_act(text, 3, "CELEX")
    assert all(":v2:" not in p.uid for p in v1)
    assert v1[0].uid.startswith("3-")


# ---------------------------------------------------------------- N2/N3
def test_no_duplicate_uids_in_context():
    c = mk("u1", ("1",))
    res = pack_group([], [c, c, mk("u2", ("2",))], budget=100, counter=TOK)
    uids = [x.uid for x in res.selected]
    assert len(uids) == len(set(uids))
    assert "u1" in res.rejected_duplicate
    assert res.n_duplicate_uids == 0


def test_no_ancestor_and_descendant_together():
    parent = mk("art5", ("5",), rank=0)
    child = mk("art5p2", ("5", "2"), rank=1)
    res = pack_group([], [parent, child], budget=100, counter=TOK)
    paths = [x.path for x in res.selected]
    assert ("5",) in paths
    assert ("5", "2") not in paths, "descendant must not join its ancestor"
    assert res.rejected_overlap and res.rejected_overlap[0][0] == "art5p2"
    assert res.n_surviving_overlaps == 0


def test_paths_overlap_semantics():
    assert paths_overlap(("5",), ("5", "2"))
    assert paths_overlap(("5", "2"), ("5",))
    assert paths_overlap(("5",), ("5",))
    assert not paths_overlap(("5",), ("6",))
    assert not paths_overlap(("5", "2"), ("5", "3"))


# ---------------------------------------------------------------- N4 ranking
def test_base_centroid_order_preserved():
    """Ranked list must be consumed in rank order, not document/UID order."""
    ranked = [mk("z_top", ("9",), rank=0, tokens=10),
              mk("a_mid", ("1",), rank=1, tokens=10),
              mk("m_low", ("5",), rank=2, tokens=10)]
    res = build_base(ranked, budget=prompt_budget(ranked[:2]), counter=TOK)
    assert [c.uid for c in res.selected] == ["z_top", "a_mid"], \
        "highest-ranked kept; lowest-ranked dropped (not last-in-document)"


def test_graph_candidate_ranking_is_deterministic_and_not_by_uid():
    a = mk("zzz", ("9",), scope=CROSS, best_source_rank=0, target_sim=0.9)
    b = mk("aaa", ("8",), scope=CROSS, best_source_rank=5, target_sim=0.99)
    c = mk("mmm", ("7",), scope=CROSS, best_source_rank=0, target_sim=0.5)
    assert [x.uid for x in rank_graph_candidates([a, b, c])] == ["zzz", "mmm", "aaa"]


# ---------------------------------------------------------------- N5/N6/N7
def _abc_fixture():
    base = [mk(f"b{i}", (str(10 + i),), rank=i, tokens=10) for i in range(6)]
    within = [mk("w1", ("21",), scope=WITHIN, best_source_rank=0, tokens=10),
              mk("w2", ("22",), scope=WITHIN, best_source_rank=1, tokens=10)]
    cross = [mk("c1", ("31",), scope=CROSS, doc_id=2, best_source_rank=0, tokens=10)]
    return base, within, cross


def test_a_used_within_additions_retained_in_b():
    base, within, cross = _abc_fixture()
    effective = build_base(base, prompt_budget(base[:5]), TOK).prompt_tokens
    a = build_a(base, within, effective_budget=effective, counter=TOK,
                max_within=4)
    a_used = [c for c in a.selected if c.scope == WITHIN]
    b = build_b(base, a_used, cross, effective_budget=a.prompt_tokens, counter=TOK,
                max_cross=4)
    b_uids = {c.uid for c in b.selected}
    assert all(c.uid in b_uids for c in a_used), "B must retain every A addition"


def test_cross_cannot_displace_a_additions():
    base, within, _ = _abc_fixture()
    many_cross = [mk(f"c{i}", (str(40 + i),), scope=CROSS, doc_id=2,
                     best_source_rank=i, tokens=10) for i in range(4)]
    effective = build_base(base, prompt_budget(base[:4]), TOK).prompt_tokens
    a = build_a(base, within, effective_budget=effective, counter=TOK,
                max_within=4)
    a_used = [c for c in a.selected if c.scope == WITHIN]
    b = build_b(base, a_used, many_cross, effective_budget=a.prompt_tokens,
                counter=TOK, max_cross=4)
    b_uids = {c.uid for c in b.selected}
    assert all(c.uid in b_uids for c in a_used)
    dropped_base = [c.uid for c in a.selected
                    if c.scope == FOCAL and c.uid not in b_uids]
    assert dropped_base, "cross evidence must displace BASE content, not A additions"


def test_b_differs_from_a_when_cross_inserted():
    base, within, cross = _abc_fixture()
    effective = build_base(base, prompt_budget(base[:5]), TOK).prompt_tokens
    a = build_a(base, within, effective_budget=effective, counter=TOK)
    a_used = [c for c in a.selected if c.scope == WITHIN]
    b = build_b(base, a_used, cross, effective_budget=a.prompt_tokens, counter=TOK)
    a_uids = {c.uid for c in a.selected}
    b_uids = {c.uid for c in b.selected}
    inserted = {c.uid for c in b.selected if c.scope == CROSS}
    assert inserted, "fixture must insert a cross passage"
    assert b_uids != a_uids
    flags = treatment_flags(set(), a_uids, b_uids, inserted)
    assert flags["b_differs_from_a"] and flags["b_has_cross"]


# ---------------------------------------------------------------- N8 budgets
@pytest.mark.parametrize("n_base_blocks", [2, 4, 6])
def test_all_conditions_obey_same_budget(n_base_blocks):
    base, within, cross = _abc_fixture()
    configured = prompt_budget(base[:n_base_blocks])
    rb = build_base(base, budget=configured, counter=TOK)
    effective = rb.prompt_tokens
    a = build_a(base, within, effective_budget=effective, counter=TOK)
    a_used = [c for c in a.selected if c.scope == WITHIN]
    results = {
        "base": rb,
        "A": a,
        "B": build_b(base, a_used, cross, effective_budget=a.prompt_tokens,
                     counter=TOK),
        "oracle": build_oracle(base, [mk("o1", ("55",), tokens=10)],
                               effective_budget=effective, counter=TOK),
    }
    for name, r in results.items():
        assert r.prompt_tokens <= effective, \
            f"{name} exceeded budget: {r.prompt_tokens} > {effective}"
        uids = [c.uid for c in r.selected]
        assert len(uids) == len(set(uids)), f"{name} has duplicate uids"
    assert results["B"].prompt_tokens <= results["A"].prompt_tokens


def test_short_base_sets_smaller_effective_budget_for_graph_conditions():
    """Graph evidence replaces short Base content; it never lengthens prompt."""
    base = [mk("b0", ("1",), rank=0, tokens=20)]
    within = [mk("w0", ("2",), scope=WITHIN, tokens=80)]
    cross = [mk("c0", ("9",), scope=CROSS, doc_id=2, tokens=80)]
    rb = build_base(base, budget=10_000, counter=TOK)
    assert rb.prompt_tokens < 10_000             # deliberately underfilled Base
    a = build_a(base, within, rb.prompt_tokens, TOK)
    a_used = [c for c in a.selected if c.scope == WITHIN]
    b = build_b(base, a_used, cross, rb.prompt_tokens, TOK)
    assert a.prompt_tokens <= rb.prompt_tokens
    assert b.prompt_tokens <= a.prompt_tokens
    assert not [c for c in b.selected if c.scope == CROSS], \
        "cross evidence too large to fit meaningfully must be rejected"


def test_truncation_fills_budget_without_padding():
    base = [mk("b0", ("1",), rank=0, tokens=10), mk("b1", ("2",), rank=1, tokens=100)]
    res = pack_group([], base, budget=60, counter=TOK)
    assert res.tokens <= 60
    assert res.truncated_uid == "b1"
    assert res.truncated_to > 0


# ---------------------------------------------------------------- N9 labels
def test_targeted_labels_use_actual_coverage():
    cov_base = [0.10, 0.90, 0.10, 0.10]
    cov_a = [0.90, 0.90, 0.10, 0.10]      # rescues sentence 0
    cov_b = [0.90, 0.90, 0.95, 0.10]      # additionally rescues sentence 2
    lab = targeted_labels(cov_base, cov_a, cov_b)
    assert lab["base_missed_idx"] == [0, 2, 3]
    assert lab["a_actual_rescue_idx"] == [0]
    assert lab["b_incremental_actual_rescue_idx"] == [2], \
        "B credited only for what A did NOT already cover"


def test_b_incremental_excludes_content_a_already_had():
    cov_base = [0.10]
    cov_a = [0.95]
    cov_b = [0.99]
    lab = targeted_labels(cov_base, cov_a, cov_b)
    assert lab["a_actual_rescue_idx"] == [0]
    assert lab["b_incremental_actual_rescue_idx"] == []


# ---------------------------------------------------------------- N10 leakage
def test_base_a_b_builders_cannot_see_gold_summary():
    for fn in (build_base, build_a, build_b):
        params = set(inspect.signature(fn).parameters)
        assert not (params & {"gold", "gold_summary", "summary", "reference"}), \
            f"{fn.__name__} must not accept gold-summary data"
    assert "oracle_candidates" in inspect.signature(build_oracle).parameters


# ---------------------------------------------------------------- grouping
def test_group_assignment_deterministic_and_contiguous():
    n, g = 10, 4
    groups = [assign_group(i, n, g) for i in range(n)]
    assert groups == sorted(groups), "groups must be contiguous in doc order"
    assert set(groups) <= set(range(g))
    assert max(groups) == g - 1
    b = group_boundaries(n, g)
    assert len(b) == g
