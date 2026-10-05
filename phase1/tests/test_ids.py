"""Unit tests for passage-ID canonicalisation — every format observed in the corpus."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from regkg.ids import canon, is_fragment, is_ancestor, is_same_or_descendant


def test_plain_dotted():
    assert canon("1.1.1") == ("1", "1", "1")
    assert canon("19.2.16") == ("19", "2", "16")


def test_trailing_dot():
    assert canon("1.") == ("1",)
    assert canon("Part 1.1.") == ("part 1", "1")


def test_parenthesised_leaf():
    assert canon("1.1.1.(2)") == ("1", "1", "1", "2")
    assert canon("2.4.2.(a)") == ("2", "4", "2", "a")


def test_labeled_segments():
    assert canon("Part 3.Chapter 1.7.(1)") == ("part 3", "chapter 1", "7", "1")
    assert canon("Schedule 1.Part 2.Chapter 1.5.(2)") == (
        "schedule 1", "part 2", "chapter 1", "5", "2")
    assert canon("PART 5.12.3.6.(3)") == ("part 5", "12", "3", "6", "3")
    # case- and spacing-insensitive matching between CSV and JSON variants
    assert canon("Part 11.Chapter 4.114.(2)") == canon("PART 11.CHAPTER 4.114.(2)")


def test_named_levels_and_appendix():
    assert canon("1.2.1.Guidance.3.") == ("1", "2", "1", "guidance", "3")
    assert canon("APP2.A2.1.1") == ("app2", "a2", "1", "1")
    assert canon("SECTION I.A.1.") == ("section i", "a", "1")


def test_fragments():
    assert is_fragment("1)")
    assert is_fragment("(a)")
    assert not is_fragment("1.1")
    assert not is_fragment("Part 2.4.(1)")
    assert canon("1)") == ("1",)


def test_ancestry():
    assert is_ancestor(canon("6.1"), canon("6.1.1"))
    assert is_ancestor(canon("6.1"), canon("6.1.1.(a)"))
    assert not is_ancestor(canon("6.1"), canon("6.10"))       # no string-prefix bleed
    assert not is_ancestor(canon("6.1.1"), canon("6.1"))
    assert is_same_or_descendant(canon("6.1"), canon("6.1"))
    assert is_same_or_descendant(canon("Part 2.4"), canon("Part 2.4.(1)"))


def test_hierarchy_across_format_variants():
    # "7." (with trailing dot) must be recognised as parent of "7.(1)"
    assert is_ancestor(canon("Part 3.Chapter 1.7."), canon("Part 3.Chapter 1.7.(1)"))
