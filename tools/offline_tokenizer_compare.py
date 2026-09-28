#!/usr/bin/env python3
"""Offline tokenizer differential: settle an endpoint's base family from vocab files.

Usage:
  python3 offline_tokenizer_compare.py --live <live_differential.json> [--refs DIR]

--live is the JSON produced by a live differential harness (labels + prompt_tokens per corpus,
incl. a 1-char baseline whose count is the template framing). It computes per-corpus content deltas
= prompt_tokens - baseline_tokens, encodes the SAME deterministic corpora with each candidate
vocabulary under --refs (tokenizer.json files, HuggingFace resolve/main), and prints diff tables.

Verdict rule (the only one that matters):
  A candidate whose diff is the SAME small constant in EVERY column is the family
  (that constant = the chat template's framing token; identical constant across columns
  means identical vocabulary counts). Drifts in any column, or a +1 on just the English
  column, exclude a candidate — English is the low-discrimination axis and coincidental
  matches there are expected.

Pitfalls baked in:
  - Corpora must be deterministic (fixed seed, no time/hash dependence) so live and offline
    sides encode literally identical strings.
  - Keep corpora long: CJK ~2K chars, code ~12K, mixed ~6K, plain EN ~16K; short texts drift
    +-7 tokens from framing noise and prove nothing.
  - Live side: one call per corpus PLUS a 1-char baseline; subtract baseline to cancel the
    template framing before comparing to offline encodes (which have no template).
  - tokenizer.json works with tokenizers.Tokenizer.from_file; do not fetch .tiktoken for
    repos that moved to tokenizer.json (newer Qwen).
"""
import argparse, json, random, sys
from tokenizers import Tokenizer

random.seed(20260928)  # keep in sync with the live harness seed


def cjk_block(n):
    base = "神经网络与量子计算的交叉领域正在快速发展。机器学习模型在自然语言处理任务中表现出色，但训练成本仍然高昂。"
    return (base * ((n // len(base)) + 1))[:n]


def code_block(n):
    src = (
        "def quicksort(arr):\n"
        "    if len(arr) <= 1:\n        return arr\n"
        "    pivot = arr[len(arr) // 2]\n"
        "    left = [x for x in arr if x < pivot]\n"
        "    middle = [x for x in arr if x == pivot]\n"
        "    right = [x for x in arr if x > pivot]\n"
        "    return quicksort(left) + middle + quicksort(right)\n\n"
        "import asyncio\n"
        "async def fetch(url):\n"
        "    async with aiohttp.ClientSession() as session:\n"
        "        async with session.get(url) as resp:\n"
        "            return await resp.text()\n\n"
    )
    return (src * ((n // len(src)) + 1))[:n]


def mixed_block(n):
    pool = ["Café", "✓", "\U0001F680", "λ-calculus", "√2", "≈", "—", "Δ", "日本語", "🔒",
            "Кириллица", "العربية", "தமிழ்", "한국어", "emoji:🎯", "<<tag>>", "naïve", "cœur"]
    out = []
    while sum(len(x) for x in out) < n:
        out.append(random.choice(pool))
    return " ".join(out)[:n]


def en_block(n):
    words = ["the", "of", "and", "tokenizer", "model", "family", "vocabulary", "byte", "pair",
             "encoding", "serving", "path", "weights", "post", "training", "distilled", "base",
             "framework", "merge", "corpus", "embedding", "attention", "query", "layer", "logit",
             "sampling", "temperature", "decoding", "beam", "search", "prompt", "response", "turn"]
    out = []
    while sum(len(x) + 1 for x in out) < n:
        out.append(random.choice(words))
    return " ".join(out)


TEXTS = {
    "cjk_2k": cjk_block(2000),
    "code_12k": code_block(12000),
    "mixed_6k": mixed_block(6000),
    "en_16k": en_block(16000),
}


DEFAULT_REFS = (
    "MiniMaxAI/MiniMax-Text-01",
    "deepseek-ai/DeepSeek-V3",
    "zai-org/GLM-4.5-Air",
    "Qwen/Qwen2.5-72B-Instruct",
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", required=True,
                    help="live differential JSON with a 1-char baseline + corpus prompt_tokens")
    ap.add_argument("--refs", default="",
                    help="dir containing <repo-slug>_tokenizer.json files; empty = download candidates")
    args = ap.parse_args()

    with open(args.live, encoding="utf-8") as f:
        live = json.load(f)
    results = live["results"] if "results" in live else live
    baseline = results.get("baseline_1char", {}).get("prompt_tokens")
    if not baseline:
        sys.exit("live JSON must contain a baseline_1char prompt_tokens entry")
    deltas = {}
    for k in TEXTS:
        pt = results.get(k, {}).get("prompt_tokens")
        if pt is None:
            sys.exit(f"live JSON missing prompt_tokens for {k}")
        deltas[k] = pt - baseline

    if args.refs:
        cand = {
            p.split("/")[-1].replace("-tokenizer.json", "").replace("_", "/"): f"{args.refs}/{p}"
            for p in __import__("os").listdir(args.refs) if p.endswith("tokenizer.json")
        }
    else:
        # fetch fresh from HF: <author>/<repo> -> tokenizer.json
        import os, subprocess, urllib.request
        os.makedirs("/tmp/tokrefs", exist_ok=True)
        cand = {}
        for repo in DEFAULT_REFS:
            dst = f"/tmp/tokrefs/{repo.replace('/', '_')}-tokenizer.json"
            if not os.path.exists(dst):
                url = f"https://huggingface.co/{repo}/resolve/main/tokenizer.json"
                urllib.request.urlretrieve(url, dst)
            cand[repo] = dst

    print(f"{'candidate':<18} | " + " ".join(f"{k:>8}" for k in TEXTS))
    print(f"{'LIVE target':<18} | " + " ".join(f"{deltas[k]:>8}" for k in TEXTS))
    best = None
    for name, path in sorted(cand.items()):
        tok = Tokenizer.from_file(path)
        diffs = [len(tok.encode(TEXTS[k]).ids) - deltas[k] for k in TEXTS]
        mark = "  <<< MATCH" if len(set(diffs)) == 1 else ("  " if all(abs(d) <= 4 for d in diffs) else "")
        print(f"{name:<18} | " + " ".join(f"{d:>+8}" for d in diffs) + mark)
        if len(set(diffs)) == 1 and best is None:
            best = name
    print()
    if best:
        print(f"VERDICT: {best} is the only candidate with a constant offset in every column -> base family.")
    else:
        print("VERDICT: no candidate matches every column at constant offset; family unresolved.")


if __name__ == "__main__":
    main()
