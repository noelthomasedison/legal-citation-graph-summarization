"""Create a manual precision sample from a versioned Phase 3 graph.

The historical script 05 sample uses v1 UIDs and must remain untouched. This
script samples the frozen ``eurlex_edges_v2.jsonl`` population directly, with
separate quotas for within- and cross-document edges because B depends on the
much smaller cross-document stratum.

No LLM calls. Outputs are v2-only and refuse to overwrite adjudicated labels
unless ``--force`` is supplied explicitly.
"""
import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from context_v2 import sha256_file                         # noqa: E402
from eurlex_ingest import load_eurlexsum                   # noqa: E402
from eurlex_resolve import EuResolver                      # noqa: E402
from regkg.detect import detect                            # noqa: E402
from regkg.textutil import clean                           # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--n-within", type=int, default=50)
ap.add_argument("--n-cross", type=int, default=50)
ap.add_argument("--seed", type=int, default=389,
                help="fresh held-out seed; development audits used 41, 97, 173, 251, 347")
ap.add_argument("--artifact-tag", default="v2_2")
ap.add_argument("--segmentation-version", choices=("legacy", "region-v2"),
                default="region-v2")
ap.add_argument("--force", action="store_true",
                help="replace an existing v2 sample, including any labels")
args = ap.parse_args()

if not re.fullmatch(r"[a-zA-Z0-9_]+", args.artifact_tag):
    sys.exit("--artifact-tag may contain only letters, numbers and underscores")
EDGES = ROOT / "data" / f"eurlex_edges_{args.artifact_tag}.jsonl"
OUT_JSONL = ROOT / "data" / f"eurlex_audit_{args.artifact_tag}_sample.jsonl"
OUT_MANIFEST = ROOT / "data" / f"eurlex_audit_{args.artifact_tag}_manifest.json"
OUT_REPORT = ROOT / "reports" / f"eurlex_audit_{args.artifact_tag}_sample.md"

if not EDGES.exists():
    sys.exit("run 12_build_graph_v2.py first")
if args.n_within <= 0 or args.n_cross <= 0:
    sys.exit("--n-within and --n-cross must both be positive")
if OUT_JSONL.exists() and not args.force:
    old = [json.loads(x) for x in OUT_JSONL.read_text().splitlines() if x.strip()]
    if any(r.get("label") is not None for r in old):
        sys.exit("refusing to overwrite adjudicated v2 labels; use --force only "
                 "if replacement is intentional")
    sys.exit(f"{OUT_JSONL.name} already exists; use --force to regenerate")

print("loading collision-free v2 corpus...", flush=True)
corpus, id2celex, celex2id = load_eurlexsum(
    uid_version="v2", segmentation_version=args.segmentation_version)
assert len(corpus.passages) == len(corpus.by_uid)

seen = set()
population = {"within": [], "cross": []}
for line in EDGES.read_text().splitlines():
    if not line.strip():
        continue
    e = json.loads(line)
    key = (e["src"], e["tgt"])
    if key in seen or e["src"] == e["tgt"]:
        continue
    if e["src"] not in corpus.by_uid or e["tgt"] not in corpus.by_uid:
        sys.exit(f"graph edge points outside v2 corpus: {key}")
    seen.add(key)
    src, tgt = corpus.by_uid[e["src"]], corpus.by_uid[e["tgt"]]
    scope = "within" if src.doc_id == tgt.doc_id else "cross"
    population[scope].append(key)

for scope, requested in (("within", args.n_within), ("cross", args.n_cross)):
    if len(population[scope]) < requested:
        sys.exit(f"requested {requested} {scope} edges but population has only "
                 f"{len(population[scope])}")

rng = random.Random(args.seed)
sampled = {
    "within": rng.sample(population["within"], args.n_within),
    "cross": rng.sample(population["cross"], args.n_cross),
}

# Re-resolve each detected mention so attribution includes its exact character
# offset. ``PredEdge`` stores only surface text; using ``text.find(mention)``
# showed the wrong occurrence when a long passage repeated e.g. "Articles 1 to
# 17" for several instruments.
never = re.compile(r"(?!x)x")
resolver = EuResolver(corpus=corpus, aliases={}, alias_re=never,
                      use_guards=True, use_aliases=False, use_fsmr=False,
                      use_tolerant=True, use_attribution=True,
                      celex2id=celex2id)
source_uids = sorted({s for pairs in sampled.values() for s, _ in pairs})
attribution = {}
print(f"recovering offset-aware attribution for {len(source_uids)} sampled sources...",
      flush=True)
for uid in source_uids:
    src = corpus.by_uid[uid]
    source_text = clean(src.text)
    for mention_obj in detect(source_text, None, guards=True):
        for edge in resolver._resolve_mention(src, source_text, mention_obj):
            attribution.setdefault((edge.source_uid, edge.target_uid),
                                   (edge, mention_obj.start))

records = []
report = [f"# EUR-Lex {args.artifact_tag} graph precision audit sample", "",
          f"Frozen graph: `data/{EDGES.name}` sha256 "
          f"`{sha256_file(EDGES)[:16]}…`", "",
          f"Seed {args.seed}. Population: {len(population['within']):,} within-"
          f"document and {len(population['cross']):,} cross-document edges.",
          f"Sample: {args.n_within} within + {args.n_cross} cross.",
          f"Segmentation: `{args.segmentation_version}`. Seeds 41, 97, 173, 251 and 347",
          "are development/repair sets; this is a fresh held-out sample.", "",
          "For every row, judge whether the source passage genuinely refers to",
          "the displayed target passage. Put `TRUE`, `FALSE`, or `UNSURE` in",
          f"the matching `label` field of `data/{OUT_JSONL.name}`.",
          "Do not infer correctness merely because the article numbers match.", ""]

i = 0
for scope in ("within", "cross"):
    for source_uid, target_uid in sampled[scope]:
        src, tgt = corpus.by_uid[source_uid], corpus.by_uid[target_uid]
        attributed = attribution.get((source_uid, target_uid))
        edge, edge_pos = attributed if attributed is not None else (None, -1)
        mention = edge.mention if edge is not None else ""
        how = (edge.how or "exact") if edge is not None else "unavailable"
        keyword = edge.keyword if edge is not None else ""
        source_text = clean(src.text)
        pos = edge_pos if edge is not None else -1
        if pos >= 0:
            context = source_text[max(0, pos - 220):
                                  pos + len(mention) + 220]
        else:
            context = source_text[:600]
        source_celex = id2celex.get(src.doc_id, str(src.doc_id))
        target_celex = id2celex.get(tgt.doc_id, str(tgt.doc_id))
        report += [f"## {i:03d} [{scope.upper()}] `{mention or 'mention unavailable'}`",
                   f"- Resolution: `{how}`; keyword: `{keyword or 'none'}`",
                   f"- Source act/path: `{source_celex}` / `{src.passage_id}`",
                   f"- Target act/path: `{target_celex}` / `{tgt.passage_id}`",
                   f"- Source context: ...{context.replace(chr(10), ' ')}...",
                   f"- Target text: {clean(tgt.text)[:600].replace(chr(10), ' ')}",
                   ""]
        records.append({
            "i": i,
            "scope": scope,
            "source_celex": source_celex,
            "target_celex": target_celex,
            "source_path": src.passage_id,
            "target_path": tgt.passage_id,
            "source_uid": source_uid,
            "target_uid": target_uid,
            "mention": mention,
            "how": how,
            "keyword": keyword,
            "label": None,
        })
        i += 1

how_counts = Counter(r["how"] for r in records)
manifest = {
    "schema_version": "eurlex-audit-v2.2",
    "seed": args.seed,
    "graph": str(EDGES.relative_to(ROOT)),
    "graph_sha256": sha256_file(EDGES),
    "uid_version": "v2",
    "segmentation_version": args.segmentation_version,
    "population": {k: len(v) for k, v in population.items()},
    "sample": {"within": args.n_within, "cross": args.n_cross},
    "sample_how": dict(sorted(how_counts.items())),
    "zero_llm_calls": True,
}

OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)
OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
with OUT_JSONL.open("w") as f:
    for rec in records:
        f.write(json.dumps(rec) + "\n")
OUT_MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
OUT_REPORT.write_text("\n".join(report) + "\n")

print(f"wrote {OUT_REPORT.relative_to(ROOT)}")
print(f"wrote {OUT_JSONL.relative_to(ROOT)}")
print(f"wrote {OUT_MANIFEST.relative_to(ROOT)}")
print("zero LLM calls")
