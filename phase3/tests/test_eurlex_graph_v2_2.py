"""Regression tests for the 16 false edges found in the v2 precision audit.

These use synthetic legal text, not the audit sample itself, so the sample can
remain a development set and a fresh held-out graph audit can follow v2.2.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from eurlex_ingest import segment_act, to_celex               # noqa: E402
from eurlex_resolve import EuResolver                         # noqa: E402
from regkg.ingest import Corpus, Passage                      # noqa: E402


NEVER = re.compile(r"(?!x)x")


def passage(uid, doc, path, text, region="main"):
    p = Passage(uid=uid, doc_id=doc, doc_name=f"doc{doc}",
                passage_id=".".join(path), path=tuple(path), text=text)
    p.region = region
    return p


def resolver(*passages, celex2id=None):
    corpus = Corpus()
    for p in passages:
        corpus.add(p)
    return EuResolver(corpus=corpus, aliases={}, alias_re=NEVER,
                      use_guards=True, use_aliases=False, use_fsmr=False,
                      use_tolerant=True, use_attribution=True,
                      celex2id=celex2id or {}), corpus


def targets(res, source):
    return {e.target_uid for e in res.resolve_passage(source)}


def test_annex_isolated_but_retained_and_bare_numbers_rejected():
    text = (
        "Article 1\nMain rule\n1. This is the main legal provision with enough text.\n"
        "ANNEX I TECHNICAL TABLE\n1.1.2. Sales contract or equivalent with details.\n"
        "Article 2 Correlation-table label that is not a focal-act Article.\n"
    )
    ps = segment_act(text, 0, "CELEX", uid_version="v2",
                     segmentation_version="region-v2")
    assert any(p.path == ("1",) and "1.1.2" not in p.text for p in ps)
    annex = [p for p in ps if getattr(p, "region", None) == "annex"]
    assert annex and any("1.1.2" in p.text for p in annex)
    assert not any(p.path == ("2",) for p in ps)

    fake_target = passage("target", 0, ("1", "1"), "Target provision text.")
    res, _ = resolver(*ps, fake_target)
    source = next(p for p in annex if "1.1.2" in p.text)
    assert "target" not in targets(res, source)
    assert res.n_refused_annex_number >= 1


def test_compact_annex_contents_list_is_skipped_before_real_annex():
    text = (
        "CONTENTS\nANNEX I\nANNEX II\nANNEX III\n"
        "Article 1\nMain body\n1. This main rule has sufficient body text.\n"
        "Article 2\nFinal rule\n1. This final rule has sufficient body text.\n"
        "ANNEX I\nTECHNICAL DATA\n1.1. A technical table row with enough text.\n"
    )
    ps = segment_act(text, 0, "CELEX", uid_version="v2",
                     segmentation_version="region-v2")
    assert any(p.path == ("2",) for p in ps), "contents list must not truncate body"
    annex = [p for p in ps if getattr(p, "region", None) == "annex"]
    assert annex and all(p.path[-1].startswith("chunk ") for p in annex)


def test_this_article_resolves_relative_paragraph_not_article_number():
    source = passage("src", 0, ("65", "2"),
                     "The authorisation referred to in paragraph 1 of this Article applies.")
    right = passage("right", 0, ("65", "1"), "Paragraph one of Article 65.")
    wrong = passage("wrong", 0, ("1",), "Article 1.")
    res, _ = resolver(source, right, wrong)
    assert targets(res, source) == {"right"}


def test_that_article_uses_latest_preceding_explicit_article():
    source = passage("src", 0, ("31", "7", "b"),
                     "Point (b) of Article 20(1) or paragraph 2 of that Article applies.")
    art20p1 = passage("art20p1", 0, ("20", "1"), "Article 20 paragraph 1.")
    right = passage("right", 0, ("20", "2"), "Article 20 paragraph 2.")
    wrong = passage("wrong", 0, ("2",), "Article 2.")
    res, _ = resolver(source, art20p1, right, wrong)
    got = targets(res, source)
    assert "right" in got and "wrong" not in got


def test_this_article_range_expands_under_source_article():
    source = passage("src", 0, ("46", "1"),
                     "It shall satisfy paragraphs 2 to 9 of this Article.")
    rights = [passage(f"p{i}", 0, ("46", str(i)), f"Paragraph {i}.")
              for i in range(2, 10)]
    wrong = passage("wrong", 0, ("4",), "Article 4.")
    res, _ = resolver(source, *rights, wrong)
    got = targets(res, source)
    assert got == {f"p{i}" for i in range(2, 10)}


def test_instrument_at_end_of_list_routes_every_list_item():
    source = passage(
        "src", 0, ("52", "1"),
        "Pursuant to Articles 11(1), 13(1), 13(2) or 32(4) of Regulation "
        "(EU) No 1031/2010, the system shall provide the table."
    )
    local = passage("local", 0, ("13", "2"), "Local Article 13(2).")
    external = passage("external", 1, ("13", "2"), "Cited Article 13(2).")
    res, _ = resolver(source, local, external, celex2id={"32010R1031": 1})
    got = targets(res, source)
    assert "external" in got and "local" not in got


def test_singular_article_is_not_stolen_by_later_unrelated_instrument():
    source = passage(
        "src", 0, ("41", "3"),
        "Without prejudice to Article 11, and to Article 63 of Regulation "
        "(EU) No 1306/2013, the payment shall be granted."
    )
    local = passage("local", 0, ("11",), "Local Article 11.")
    external = passage("external", 1, ("11",), "External Article 11.")
    res, _ = resolver(source, local, external, celex2id={"32013R1306": 1})
    assert "local" in targets(res, source)


def test_that_regulation_inherits_previously_named_eu_act():
    source = passage(
        "src", 0, ("27", "2"),
        "EBA shall act under Article 19(3) of Regulation (EU) No 1093/2010. "
        "It may also act under Article 19(1) of that Regulation."
    )
    local = passage("local", 0, ("19", "1"), "Local Article 19(1).")
    external = passage("external", 1, ("19", "1"), "External Article 19(1).")
    res, _ = resolver(source, local, external, celex2id={"32010R1093": 1})
    assert "external" in targets(res, source) and "local" not in targets(res, source)


def test_charter_scope_before_mentions_prevents_local_fallback():
    source = passage(
        "src", 0, ("0",),
        "The rights are guaranteed by the Charter. Specifically, it protects "
        "personal data (Article 8) and freedom of expression (Article 11)."
    )
    local = passage("local", 0, ("11",), "Training under Article 11.")
    res, _ = resolver(source, local)
    assert "local" not in targets(res, source)


def test_same_document_duplicate_path_is_not_an_edge():
    source = passage("heading", 0, ("12",),
                     "The arrangements under Article 12 apply to these ports.")
    body = passage("body", 0, ("12",),
                   "Article 12 Ports and airports. This provision applies to terminals.")
    res, _ = resolver(source, body)
    assert not targets(res, source)
    assert res.n_refused_duplicate_path >= 1


def test_article_heading_in_incorporated_annex_is_not_a_citation():
    source = passage("annex-heading", 0, ("annex-zone", "5"),
                     "Article 5\nValuables\nThe carrier shall not be liable.",
                     region="annex")
    local = passage("local", 0, ("5",), "Article 5 Global limitation.")
    res, _ = resolver(source, local)
    assert "local" not in targets(res, source)


def test_unqualified_article_inside_annex_does_not_fall_back_to_focal_act():
    source = passage("annex", 0, ("annex-zone", "chunk 4"),
                     "Vehicles covered by Article 5 may circulate freely.",
                     region="annex")
    local = passage("local", 0, ("5",), "Unrelated focal Article 5.")
    res, _ = resolver(source, local)
    assert "local" not in targets(res, source)


def test_annex_qualified_part_is_not_focal_article():
    source = passage("src", 0, ("314",), "See Annex X, Part 4, points 3 and 4.")
    wrong = passage("wrong", 0, ("4",), "Article 4 Definitions.")
    res, _ = resolver(source, wrong)
    assert "wrong" not in targets(res, source)


def test_unmodelled_section_and_annex_tariff_chapter_are_refused():
    section_source = passage("s1", 0, ("135", "2"), "Sub-Section 2 Mapping.")
    tariff_source = passage("s2", 0, ("annex-zone", "chunk 1"),
                            "Products falling within Chapters 25 to 97 of the "
                            "Harmonised System qualify.", region="annex")
    wrong2 = passage("a2", 0, ("2",), "Article 2.")
    wrong30 = passage("a30", 0, ("30",), "Article 30.")
    res, _ = resolver(section_source, tariff_source, wrong2, wrong30)
    assert not targets(res, section_source)
    assert not targets(res, tariff_source)


def test_uppercase_structural_heading_and_oj_date_are_not_edges():
    heading = passage("h", 0, ("279",), "Prior text.\nCHAPTER 3\nTaxation\n")
    date = passage("d", 0, ("112",), "Official Journal L 141, 5.6.2015, p. 1.")
    wrong3 = passage("w3", 0, ("chapter 3",), "CHAPTER 3 Other subject.")
    wrongdate = passage("wd", 0, ("5", "6"), "Article 5 paragraph 6.")
    res, _ = resolver(heading, date, wrong3, wrongdate)
    assert not targets(res, heading)
    assert not targets(res, date)


def test_unqualified_chapter_never_falls_back_to_article_number():
    source = passage("src", 0, ("160", "4"),
                     "Protection applies in accordance with Chapter 4.")
    wrong = passage("wrong", 0, ("4",), "Article 4 Definitions.")
    res, _ = resolver(source, wrong)
    assert "wrong" not in targets(res, source)


def test_dotted_article_heading_and_rules_keyword_are_not_references():
    heading = passage("h", 0, ("3", "2"),
                      "Prior paragraph.\nARTICLE 15.4\nSelection of the Mediator\n")
    rules = passage("r", 0, ("9",),
                    "Article 9 Public contracts under international rules\n"
                    "1. This Directive shall not apply to these contracts.")
    wrong_heading = passage("wh", 0, ("3", "15", "4"), "Wrong provision.")
    wrong_rules = passage("wr", 0, ("1",), "Article 1.")
    res, _ = resolver(heading, rules, wrong_heading, wrong_rules)
    assert not targets(res, heading)
    assert "wr" not in targets(res, rules)


def test_annex_owner_before_point_blocks_wrong_article_resolution():
    source = passage("src", 0, ("4", "1"),
                     "The criteria in Annex II, points 3.6 to 3.8 of that "
                     "Regulation shall apply.")
    wrong = passage("wrong", 1, ("3", "8"), "Article 3 point 8.")
    res, _ = resolver(source, wrong, celex2id={"32009R1107": 1})
    assert "wrong" not in targets(res, source)


def test_qualified_chapter_uses_full_part_title_hierarchy():
    target = passage("right", 0, ("part 3", "title 2", "chapter 2"),
                     "CHAPTER 2 Risk weights.")
    wrong = passage("wrong", 0, ("chapter 2",), "CHAPTER 2 Prudential consolidation.")
    source = passage("src", 0, ("400", "2", "b"),
                     "The claims are weighted under Part Three, Title II, Chapter 2.")
    res, _ = resolver(source, target, wrong)
    assert targets(res, source) == {"right"}


def test_numeric_point_and_subpoint_are_segmented_and_resolved_completely():
    target_text = (
        "Article 4\nDefinitions\n"
        "1. The following definitions apply.\n"
        "(15) parent undertaking means an undertaking which:\n"
        "(a) controls another undertaking under the applicable rules;\n"
        "(b) prepares consolidated accounts for the group.\n"
        "(16) subsidiary means an undertaking controlled by another.\n"
    )
    target_passages = segment_act(target_text, 1, "32013R0575", uid_version="v2",
                                  segmentation_version="region-v2")
    correct = next(p for p in target_passages if p.path == ("4", "1", "15", "a"))
    assert "controls another" in correct.text

    source = passage(
        "src", 0, ("2", "1"),
        "A parent undertaking is defined in point (15)(a) of Article 4(1) of "
        "Regulation (EU) No 575/2013."
    )
    res, _ = resolver(source, *target_passages, celex2id={"32013R0575": 1})
    got = targets(res, source)
    assert correct.uid in got
    assert all(res.corpus.by_uid[u].path != ("4", "1", "a") for u in got)


def test_numeric_points_directly_under_definition_article_are_segmented():
    text = (
        "Article 2\nDefinitions\nFor the purposes of this Regulation:\n"
        "(9) clearing means the process of establishing positions;\n"
        "(10) balancing means all actions performed by a system operator;\n"
        "(11) balancing energy means energy used by operators.\n"
    )
    ps = segment_act(text, 1, "CELEX", uid_version="v2",
                     segmentation_version="region-v2")
    p10 = next(p for p in ps if p.path == ("2", "10"))
    assert "balancing means" in p10.text


def test_plain_point_of_article_resolves_to_complete_numeric_point():
    source = passage("src", 0, ("3",),
                     "A repository is defined in point (2) of Article 2 of "
                     "Regulation (EU) No 648/2012.")
    parent = passage("parent", 1, ("2",), "Article 2 Definitions.")
    point = passage("point", 1, ("2", "2"), "(2) trade repository means...")
    res, _ = resolver(source, parent, point, celex2id={"32012R0648": 1})
    assert targets(res, source) == {"point"}


def test_unparenthesised_point_and_nested_subpoint_are_complete():
    source1 = passage("s1", 0, ("3",),
                      "Capacity is defined in point 11 of Article 2 of Regulation "
                      "(EC) No 765/2008.")
    source2 = passage("s2", 0, ("4",),
                      "The firm in point (2)(c) of Article 4(1) of Regulation "
                      "(EU) No 575/2013 qualifies.")
    p11 = passage("p11", 1, ("2", "11"), "(11) national body means...")
    p2c = passage("p2c", 2, ("4", "1", "2", "c"), "(c) local firm...")
    res, _ = resolver(source1, source2, p11, p2c,
                      celex2id={"32008R0765": 1, "32013R0575": 2})
    assert targets(res, source1) == {"p11"}
    assert targets(res, source2) == {"p2c"}


def test_legacy_two_digit_directive_celex_order():
    assert to_celex("Directive", "96", "67") == "31996L0067"
    assert to_celex("Regulation", "765", "2008") == "32008R0765"


def test_plain_legacy_directive_name_is_recognised_as_external():
    source = passage("src", 0, ("11",),
                     "Confidentiality applies under Article 4 of Directive "
                     "2003/4/EC of the European Parliament.")
    wrong = passage("wrong", 0, ("4",), "Focal Article 4.")
    res, _ = resolver(source, wrong)
    assert "wrong" not in targets(res, source)


def test_combined_eu_euratom_instrument_is_not_mistaken_for_focal_act():
    source = passage(
        "src", 0, ("1",),
        "The rules in Article 53 of Regulation (EU, Euratom) 2018/1046 apply."
    )
    wrong = passage("wrong", 0, ("53",), "Focal Article 53.")
    res, _ = resolver(source, wrong)
    assert "wrong" not in targets(res, source)


def test_council_prefix_instrument_is_not_mistaken_for_focal_act():
    source = passage(
        "src", 0, ("1",),
        "The procedure in Article 2 of Council Regulation (EC) No 734/2008 applies."
    )
    wrong = passage("wrong", 0, ("2",), "Focal Article 2.")
    res, _ = resolver(source, wrong)
    assert "wrong" not in targets(res, source)


def test_this_regulation_list_is_not_stolen_by_later_external_instrument():
    source = passage(
        "src", 0, ("29", "7"),
        "Articles 18 to 27 of this Regulation apply together with Article 30 "
        "of Regulation (EU) No 1095/2010."
    )
    local18 = passage("local18", 0, ("18",), "Article 18.")
    local19 = passage("local19", 0, ("19",), "Article 19.")
    external18 = passage("external18", 1, ("18",), "External Article 18.")
    res, _ = resolver(source, local18, local19, external18,
                      celex2id={"32010R1095": 1})
    got = targets(res, source)
    assert "external18" not in got
    assert {"local18", "local19"} <= got


def test_point_of_relative_paragraph_keeps_complete_source_article_path():
    source = passage(
        "src", 0, ("41", "2"),
        "The amount shall be reduced as specified in point (b) of paragraph 1."
    )
    right = passage("right", 0, ("41", "1", "b"), "Point (b) of Article 41(1).")
    wrong = passage("wrong", 0, ("1", "b"), "Point (b) of Article 1.")
    res, _ = resolver(source, right, wrong)
    got = targets(res, source)
    assert "right" in got and "wrong" not in got


def test_named_rules_of_procedure_do_not_fall_back_to_focal_act():
    source = passage(
        "src", 0, ("227", "6"),
        "Article 131 and Article 135(2) of the Rules of Procedure of the "
        "General Court of 2 May 1991 shall continue to apply."
    )
    wrong131 = passage("wrong131", 0, ("131",), "Current Article 131.")
    wrong135 = passage("wrong135", 0, ("135", "2"), "Current Article 135(2).")
    res, _ = resolver(source, wrong131, wrong135)
    assert not targets(res, source)


def test_amendment_sentence_is_not_segmented_as_a_chapter_heading():
    text = (
        "Article 39\nAmendments\n1. Regulation 765/2008 is amended as follows.\n"
        "Chapter III, containing Articles 15 to 29, is deleted;\n"
        "Article 40\nFinal provisions\n1. This provision has enough text.\n"
    )
    passages = segment_act(text, 0, "CELEX", uid_version="v2",
                           segmentation_version="region-v2")
    assert not any(p.path == ("chapter 3",) for p in passages)


def test_amendment_child_routes_unqualified_article_to_amended_instrument():
    parent = passage(
        "parent", 0, ("28",),
        "Article 28\nAmendments to Directive 2001/83/EC\n"
        "Directive 2001/83/EC is hereby amended as follows:")
    source = passage(
        "src", 0, ("28", "3"),
        "3. in Article 4, the following paragraph shall be added: ‘Text.’")
    wrong_local = passage("wrong", 0, ("4",), "Local Article 4.")
    right_external = passage("right", 1, ("4",), "Amended Directive Article 4.")
    res, _ = resolver(parent, source, wrong_local, right_external,
                      celex2id={"32001L0083": 1})
    assert targets(res, source) == {"right"}
    assert res.n_routed_amendment >= 1


def test_amendment_child_is_refused_when_amended_instrument_is_absent():
    parent = passage(
        "parent", 0, ("28",),
        "Article 28\nAmendments to Directive 2001/83/EC\n"
        "Directive 2001/83/EC is hereby amended as follows:")
    source = passage("src", 0, ("28", "4"),
                     "4. in Article 6(1), the first subparagraph is replaced.")
    wrong_local = passage("wrong", 0, ("6", "1"), "Local Article 6(1).")
    res, _ = resolver(parent, source, wrong_local)
    assert "wrong" not in targets(res, source)
    assert res.n_refused_amendment >= 1
