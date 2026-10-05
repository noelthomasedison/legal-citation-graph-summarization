"""LLM extractor arm — schema-prompted reference detection + document routing.

Design (documented for the write-up):
  The LLM reads passages and outputs, per passage, the references it sees:
  {"ref": "<the citation string>", "doc": "<document name/alias or SAME>"}.
  Resolution of those strings to passage UIDs reuses the SAME lookup machinery
  as the rule arm (candidate tuples -> exact/suffix/ascent). This isolates the
  variable under test — language understanding in detection + routing, which is
  exactly where the rule arm is weak (external recall 0.566) — while keeping
  resolution mechanics constant across arms.

Engineering:
  - Provider: any OpenAI-compatible endpoint. Default NVIDIA Build.
    Env: NVIDIA_API_KEY (or LLM_API_KEY + LLM_BASE_URL/LLM_MODEL overrides).
  - Batching: N passages per call (prompt overhead amortised).
  - Disk cache keyed by (model, prompt version, passage uid): every passage is
    processed once, ever. Interruptions and rate limits cost nothing — rerun
    and it resumes.
  - Backoff: 429/5xx -> sleep (Retry-After respected) and retry.
  - Determinism: temperature 0; model + prompt version recorded in the cache.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .detect import KEYWORD
from .evaluate import PredEdge
from .ingest import Passage
from .resolve import Resolver, candidate_tuples
from .textutil import clean

PROMPT_VERSION = "v1"
DEFAULT_MODEL = "meta/llama-3.3-70b-instruct"
DEFAULT_BASE = "https://integrate.api.nvidia.com/v1"
BATCH_SIZE = 12
MAX_PASSAGE_CHARS = 2000
MAX_RETRIES = 8

SYSTEM = """You extract legal cross-references from regulatory text.
You will receive numbered passages from ADGM (Abu Dhabi Global Market) rulebooks.
For each passage, list every reference to another provision: rules, sections,
parts, chapters, schedules, appendices, paragraphs — including references to
other documents (e.g. "the FSMR", "GEN", "COBS", guidance documents).

Return STRICT JSON only, no prose, in this schema:
{"passages": [{"i": <passage number>, "refs": [{"ref": "<citation as written, e.g. 'Rule 6.1.2' or 'section 92(2)'>",
  "doc": "<target document name or acronym, or 'SAME' if it refers to the same document>"}]}]}

Rules:
- "ref" must quote the citation essentially as written in the text.
- "doc" is 'SAME' unless the text names or clearly implies another document
  (e.g. "of the FSMR" -> "FSMR"; bare statute-style "section 92(2)" in a
  rulebook usually means the FSMR framework law -> "FSMR").
- Do NOT list: quantities ("1.5 million"), dates, table row labels, the
  passage's own heading number, or references to laws outside ADGM (e.g.
  English statutes, IFRS) — skip those entirely.
- A passage with no references gets "refs": []."""

_KW_RE = re.compile(rf"^\s*({KEYWORD})\s+", re.IGNORECASE)


# ---------------------------------------------------------------- client
class LLMClient:
    def __init__(self, cache_dir: Path, model: str | None = None,
                 base_url: str | None = None, api_key: str | None = None,
                 dry_run: bool = False):
        self.model = model or os.environ.get("LLM_MODEL", DEFAULT_MODEL)
        self.base = (base_url or os.environ.get("LLM_BASE_URL", DEFAULT_BASE)).rstrip("/")
        self.key = api_key or os.environ.get("NVIDIA_API_KEY") or os.environ.get("LLM_API_KEY")
        if not self.key:
            # local key file (create it yourself; never commit/share it):
            #   phase1/.nvidia_api_key  containing just the key
            kf = Path(__file__).resolve().parents[2] / ".nvidia_api_key"
            if kf.exists():
                self.key = kf.read_text().strip()
        self.dry_run = dry_run
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.n_calls = 0
        self.n_cache_hits = 0

    # cache ----------------------------------------------------------
    def _ckey(self, uid: str) -> Path:
        h = hashlib.sha1(f"{self.model}|{PROMPT_VERSION}|{uid}".encode()).hexdigest()
        return self.cache_dir / f"{h}.json"

    def cached(self, uid: str):
        fp = self._ckey(uid)
        if fp.exists():
            return json.loads(fp.read_text())["refs"]
        return None

    def _save(self, uid: str, refs: list) -> None:
        self._ckey(uid).write_text(json.dumps(
            {"uid": uid, "model": self.model, "prompt": PROMPT_VERSION, "refs": refs}))

    # http -----------------------------------------------------------
    def _post(self, payload: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base}/chat/completions",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.key}"})
        delay = 15
        for attempt in range(MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    return json.loads(r.read())
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503):
                    wait = int(e.headers.get("Retry-After") or delay)
                    print(f"  [{e.code}] sleeping {wait}s (attempt {attempt+1})")
                    time.sleep(wait)
                    delay = min(delay * 2, 300)
                    continue
                raise
            except (urllib.error.URLError, TimeoutError):
                print(f"  [net] sleeping {delay}s (attempt {attempt+1})")
                time.sleep(delay)
                delay = min(delay * 2, 300)
        raise RuntimeError("LLM call failed after retries")

    # extraction -----------------------------------------------------
    def _build_user_msg(self, batch: list[Passage]) -> str:
        lines = []
        for i, p in enumerate(batch):
            text = clean(p.text)[:MAX_PASSAGE_CHARS]
            lines.append(f"[{i}] (document: {p.doc_name}, passage {p.passage_id})\n{text}")
        return "\n\n".join(lines)

    def extract(self, passages: list[Passage]) -> dict[str, list[dict]]:
        """uid -> [{"ref":..., "doc":...}]. Cached passages are not re-sent."""
        out: dict[str, list[dict]] = {}
        todo = []
        for p in passages:
            hit = self.cached(p.uid)
            if hit is not None:
                out[p.uid] = hit
                self.n_cache_hits += 1
            else:
                todo.append(p)
        for b in range(0, len(todo), BATCH_SIZE):
            batch = todo[b:b + BATCH_SIZE]
            if self.dry_run:
                print(f"--- DRY RUN batch {b//BATCH_SIZE}: {len(batch)} passages, "
                      f"~{len(self._build_user_msg(batch))//4} prompt tokens")
                for p in batch:
                    out[p.uid] = []
                continue
            payload = {"model": self.model, "temperature": 0, "max_tokens": 2048,
                       "messages": [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": self._build_user_msg(batch)}]}
            resp = self._post(payload)
            self.n_calls += 1
            content = resp["choices"][0]["message"]["content"]
            parsed = _parse_json(content)
            per_idx = {int(e.get("i", -1)): e.get("refs", []) for e in
                       (parsed.get("passages", []) if isinstance(parsed, dict) else [])}
            for i, p in enumerate(batch):
                refs = [r for r in per_idx.get(i, [])
                        if isinstance(r, dict) and r.get("ref")]
                out[p.uid] = refs
                self._save(p.uid, refs)
            done = min(b + BATCH_SIZE, len(todo))
            print(f"  batch {b//BATCH_SIZE + 1}: {done}/{len(todo)} new passages done")
        return out


def _parse_json(content: str) -> dict:
    content = content.strip()
    content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", content, re.DOTALL)
        return json.loads(m.group(0)) if m else {}


# ------------------------------------------------------- shared resolution
_POSTFIX_RE = re.compile(r"\s+(?:of|under|in)\s+(?:the\s+)?[A-Za-z].*$")
_RANGE_RE = re.compile(r"\s*(?:to|–|—|-)\s*")
_LIST_RE = re.compile(r"\s*(?:,|and|or)\s+")


def _split_cores(core: str) -> list[str]:
    """LLM ref strings carry ranges/lists verbatim: 'A4.3.2 to A4.3.6',
    '4.8.2 and 4.8.3'. Expand them the same way the rule arm does."""
    parts = [s for s in _LIST_RE.split(core) if s.strip()]
    out: list[str] = []
    for part in parts:
        ends = [e for e in _RANGE_RE.split(part) if e.strip()]
        if len(ends) == 2:
            out.append(ends[0])
            out.extend(Resolver._expand_range(ends[0], ends[1]))
        else:
            out.append(part.strip())
    return out


def resolve_llm_refs(resolver: Resolver, p: Passage,
                     refs: list[dict]) -> list[PredEdge]:
    """Map the LLM's (ref string, doc hint) outputs to passage UIDs using the
    same lookup ladder as the rule arm."""
    edges = []
    for r in refs:
        ref, hint = str(r.get("ref", "")), str(r.get("doc", "SAME"))
        # the doc hint already captured "... of the FSMR"; strip the postfix
        # from the citation string so the number parses cleanly
        ref_clean = _POSTFIX_RE.sub("", ref).strip()
        kw = None
        m = _KW_RE.match(ref_clean)
        core = ref_clean
        if m:
            kw = m.group(1)
            core = ref_clean[m.end():].strip()
        doc = p.doc_id
        if hint and hint.upper() != "SAME":
            doc = resolver.aliases.get(hint.strip().lower(), p.doc_id)
        statute = (kw or "").lower().rstrip("s") in ("section", "part", "chapter", "schedule")
        docs = [doc]
        if statute and resolver.fsmr_doc and doc != resolver.fsmr_doc:
            docs.append(resolver.fsmr_doc)
        for one_core in _split_cores(core):
            tgt, how = None, ""
            for comps in candidate_tuples(one_core, kw):
                for d in docs:
                    tgt, how = resolver._lookup(d, comps)
                    if tgt is not None:
                        break
                if tgt is not None:
                    break
            if tgt is None or tgt.uid == p.uid:
                continue
            edges.append(PredEdge(p.uid, tgt.uid, mention=ref, how=f"llm+{how}",
                                  keyword=kw or ""))
    return edges
