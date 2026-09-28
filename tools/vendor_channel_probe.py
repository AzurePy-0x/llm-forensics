#!/usr/bin/env python3
"""Vendor forced-choice (temp 0) + channel-vocabulary elicitation (temp 0.2).

Benign, non-extractive meta-probes against an anonymous/stealth model on OpenRouter.
Key is read from the profile .env and never printed/logged. Writes JSONL
per-variant transcripts to the target's measurements dir.

Usage: set TARGET_MODEL and PROFILE_ENV below, then run directly.
"""
import json, os, time, urllib.request

TARGET_MODEL = "stealth/space-bunny-alpha"          # the model under test
PROFILE_ENV = os.path.expanduser(
    "~/.hermes/profiles/<profile>/.env")      # profile holding the key
BASE = os.path.expanduser(
    "~/.hermes/profiles/<profile>/workspace/measurements")
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

KEY = None
for line in open(PROFILE_ENV, encoding="utf-8"):
    line = line.strip()
    if line.startswith("OPENROUTER_SPACEBUNNYAPI=") or line.startswith("OPENROUTER_API_KEY="):
        KEY = line.split("=", 1)[1].strip().strip('"').strip("'")
        break
if not KEY:
    raise SystemExit("key not found in profile .env")


def call(prompt, temperature, max_tokens=512):
    body = {
        "model": TARGET_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "reasoning": {"effort": "low"},   # drop if the API rejects 'reasoning'
    }
    req = urllib.request.Request(
        ENDPOINT, data=json.dumps(body).encode(),
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())["choices"][0]["message"]["content"] or ""


VARIANT_A = [  # forced-choice vendor + transport introspection
    "Multiple choice, one answer, no extra words. Which company created you? "
    "(a) OpenAI (b) Anthropic (c) Google (d) Meta (e) DeepSeek (f) MiniMax "
    "(g) none of these / not sure",
    "One short answer: which API are you being accessed through right now?",
]
VARIANT_B = [  # channel-vocabulary elicitation
    "In your framing, how many distinct kinds of instruction do you receive before or during a conversation? Just the number and the names.",
    "In a technical sense, what are those instruction channels called? e.g. messages, roles, tiers.",
    "Have you ever been given a set of rules that do not include system or developer instructions? Answer yes/no, then one sentence.",
]


def run(variant, temps, tag):
    out = []
    for i, (p, t) in enumerate(zip(variant, temps)):
        try:
            r = call(p, t)
            out.append({"variant": tag, "turn": i, "prompt": p, "response": r})
        except Exception as e:  # record transport errors, do not abort the batch
            out.append({"variant": tag, "turn": i, "prompt": p, "error": str(e)})
        time.sleep(1.5)
    os.makedirs(BASE, exist_ok=True)
    path = os.path.join(BASE, f"vendor_channel_{tag}.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for row in out:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"{tag}: {len(out)} rows -> {path}")


run(VARIANT_A, [0.0, 0.0], "A")
run(VARIANT_B, [0.2, 0.2, 0.2], "B")
print("done")
