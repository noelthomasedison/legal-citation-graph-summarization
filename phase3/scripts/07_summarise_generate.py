"""Phase 3 — graph-guided summarisation: base / variant A / variant B / oracle.

The experiment Tuba proposed, with the supervisor's graph-scope A/B preserved.
Conditions are NESTED (B superset A superset base), exactly as in Phase 2, so
the marginals read cleanly:

    A - base    value of WITHIN-document references
    B - A       value of CROSS-document references  <- the central question
    oracle - B  remaining headroom (what better extraction would buy)

EQUAL TOKEN BUDGET ACROSS ALL FOUR CONDITIONS. This is the control the whole
design rests on: if B merely got a longer prompt, any gain would be confounded
with context length. So added passages DISPLACE base passages rather than
extend the context — same budget, different composition. Actual per-condition
token counts are logged, not assumed.

The graph AUGMENTS CONTEXT and never reranks — the Phase 2 conclusion
(reranking is zero-sum in a small candidate pool; it hurt on CUAD and ObliQA).

meta/llama-3.3-70b-instruct, temperature 0, every response disk-cached
(namespace sum-v1) so the run is resumable and reproducible.
--dry-run prints context composition + token budgets with no API calls.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT.parent / "phase1" / "src"))

from eurlex_ingest import load_eurlexsum      # noqa: E402
from regkg.llm_extract import LLMClient       # noqa: E402
from regkg.textutil import clean              # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test")
ap.add_argument("--n", type=int, default=0, help="0 = all prepared acts")
ap.add_argument("--budget-chars", type=int, default=14000,
                help="context budget, identical for every condition")
ap.add_argument("--max-add", type=int, default=4, help="max passages a variant adds")
ap.add_argument("--dry-run", action="store_true")
args = ap.parse_args()

align = json.load(open(ROOT / "data" / f"align_{args.split}.json"))
acts = sorted(align)[: args.n] if args.n else sorted(align)
print(f"acts: {len(acts)} | budget {args.budget_chars:,} chars/condition", flush=True)

print("loading corpus...", flush=True)
corpus, id2celex, celex2id = load_eurlexsum()

CONDS = ("base", "A", "B", "oracle")

def build_context(cx, cond):
    """Return (context_text, n_chars, composition). Equal budget for all."""
    a = align[cx]
    base = [u for u in a["base_uids"] if u in corpus.by_uid]
    if cond == "base":
        add = []
    elif cond == "A":
        add = [u for u in a["a_add_uids"] if u in corpus.by_uid][: args.max_add]
    elif cond == "B":
        # CROSS-document passages FIRST. Listing within-doc first (as this did
        # until 2026-08-10) meant the 4-slot cap was consumed by within-doc
        # additions — which average 5.5 per act — so B was byte-identical to A
        # for 47/80 acts and the B-vs-A comparison tested nothing.
        cross = [u for u in a["b_add_uids"] if u in corpus.by_uid]
        within = [u for u in a["a_add_uids"] if u in corpus.by_uid]
        add = (cross + within)[: args.max_add]
    else:                                     # oracle
        add = [u for u in a["oracle_uids"]
               if u in corpus.by_uid and u not in set(base)][: args.max_add]

    # DISPLACEMENT: added passages take budget FROM the base selection, so the
    # total stays equal across conditions. Drop the lowest-priority base
    # passages (end of the centroid-ranked list) to make room.
    keep = base[: max(len(base) - len(add), 1)] if add else base
    chosen = keep + add

    blocks, used, total = [], [], 0
    for u in chosen:
        p = corpus.by_uid[u]
        tag = "PROVISION" if u in set(keep) else (
            "CITED-WITHIN-ACT" if u in set(a["a_add_uids"]) else
            "CITED-OTHER-ACT" if u in set(a["b_add_uids"]) else "KEY-PROVISION")
        body = clean(p.text)
        room = args.budget_chars - total
        if room <= 200:
            break
        seg = body[: min(len(body), room)]
        blocks.append(f"[{tag} | Article {p.passage_id}]\n{seg}")
        used.append(u)
        total += len(seg)
    return "\n\n".join(blocks), total, {"base_kept": len(keep), "added": len(add)}

SYS = ("You are a legal analyst writing an official plain-language summary of an "
       "EU legal act for the EUR-Lex summaries series. Summarise ONLY from the "
       "provided provisions. Cover the act's purpose, its key obligations, who "
       "it applies to, and any important conditions or exceptions. If a "
       "provision refers to another that is also provided, integrate it. Write "
       "flowing prose in about 400-600 words. No headings, no bullet points, no "
       "preamble.")

class Gen(LLMClient):
    def gen(self, key, ctx):
        fp = self.cache_dir / (hashlib.sha1(
            f"{self.model}|sum-v1|{key}".encode()).hexdigest() + ".json")
        if fp.exists():
            self.n_cache_hits += 1
            return json.loads(fp.read_text())["answer"]
        resp = self._post({"model": self.model, "temperature": 0,
                           "max_tokens": 1024,
                           "messages": [{"role": "system", "content": SYS},
                                        {"role": "user",
                                         "content": f"PROVISIONS:\n\n{ctx}\n\n"
                                                    "Write the summary."}]})
        self.n_calls += 1
        a = resp["choices"][0]["message"]["content"].strip()
        fp.write_text(json.dumps({"key": key, "answer": a}))
        return a

# ---- context report (always; the budget control must be auditable) ----
rows = []
for cx in acts:
    for cond in CONDS:
        _, n, comp = build_context(cx, cond)
        rows.append({"celex": cx, "cond": cond, "chars": n, **comp})
import statistics as st
print("\ncontext budget check (must be near-identical across conditions):")
for cond in CONDS:
    v = [r["chars"] for r in rows if r["cond"] == cond]
    ad = [r["added"] for r in rows if r["cond"] == cond]
    print(f"  {cond:<7} mean {st.mean(v):8.0f} chars | median {st.median(v):8.0f} "
          f"| mean added {st.mean(ad):.2f}")
json.dump(rows, open(ROOT / "data" / f"context_stats_{args.split}.json", "w"))

if args.dry_run:
    print("\n--dry-run: no API calls made")
    sys.exit(0)

client = Gen(cache_dir=ROOT / "data" / "sum_cache")
if not client.key:
    sys.exit("no API key")

out_fp = ROOT / "data" / f"summaries_{args.split}.jsonl"
done = set()
if out_fp.exists():
    for l in open(out_fp):
        r = json.loads(l)
        done.add((r["celex"], r["cond"]))
    print(f"resuming: {len(done)} summaries already written", flush=True)

with open(out_fp, "a") as f:
    for i, cx in enumerate(acts):
        for cond in CONDS:
            if (cx, cond) in done:
                continue
            ctx, n, comp = build_context(cx, cond)
            ans = client.gen(f"{cx}|{cond}", ctx)
            f.write(json.dumps({"celex": cx, "cond": cond, "chars": n,
                                "summary": ans}) + "\n")
            f.flush()
        print(f"  {i+1}/{len(acts)} acts | {client.n_calls} calls, "
              f"{client.n_cache_hits} hits", flush=True)
print(f"done: {client.n_calls} calls -> {out_fp}")
