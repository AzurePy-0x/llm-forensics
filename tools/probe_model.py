#!/usr/bin/env python3
"""Fingerprint an anonymous/stealth LLM listing via its own OpenAI-compatible API.

Stdlib only. Env vars (source the key, never hardcode):
  API_URL   default https://openrouter.ai/api/v1/chat/completions
  MODEL     model id, e.g. stealth/space-bunny-alpha (required)
  API_KEY   credential (required)
  OUT       measurements JSON path (default ./measurements.json)

Example:
  set -a; . <profile>/.env; set +a
  MODEL=stealth/space-bunny-alpha API_KEY=$OPENROUTER_API_KEY \
    python3 scripts/probe_model.py

Output: full raw responses -> OUT, plus a summary table on stdout.
"""
import base64, json, os, struct, time, urllib.error, urllib.request, zlib

API = os.environ.get("API_URL", "https://openrouter.ai/api/v1/chat/completions")
MODEL = os.environ["MODEL"]
KEY = os.environ["API_KEY"]
OUT = os.environ.get("OUT", "measurements.json")


def png(w, h, rgb):
    """Minimal PNG encoder (stdlib zlib+struct)."""
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    raw = b"".join(b"\x00" + bytes(rgb) * w for _ in range(h))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def call(messages, label, **extra):
    body = {"model": MODEL, "messages": messages}
    body.update(extra)
    req = urllib.request.Request(
        API, data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        d = {"_http_error": e.code, "_body": e.read().decode()[:300]}
    return {"label": label, "latency_s": round(time.time() - t0, 2), "response": d}


def main():
    ms = [{"probe_suite": "model fingerprint harness",
           "measured_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "endpoint": API, "model": MODEL}]

    def rec(label, messages, **kw):
        r = call(messages, label, **kw)
        ms.append(r)
        return r

    # 1. smoke
    rec("smoke", [{"role": "user", "content": "Reply with exactly: OK"}], max_tokens=20)
    # 2. identity + creator (reasoning leaks the wrapper)
    rec("identity", [{"role": "user", "content": "Who are you? What model are you? Answer in one sentence."}],
        include_reasoning=True)
    rec("creator", [{"role": "user", "content": "Who made you? Which company or lab created the model you are running on?"}],
        include_reasoning=True)
    # 3. knowledge ladder (dated public events, ~18 months) + self-claimed cutoff
    rec("knowledge_event_a", [{"role": "user", "content": "In which month and year was OpenAI's GPT-5 released? Just the month and year."}])
    rec("knowledge_event_b", [{"role": "user", "content": "What is the newest flagship model from Google, and roughly when was it released?"}])
    rec("knowledge_cutoff", [{"role": "user", "content": "What is your training-data cutoff? What is the single most recent well-known event you can recall?"}])
    # 4. reasoning effort sweep
    eff = [{"role": "user", "content": "Compute 17 * 23 * 41 step by step, then state the final number."}]
    rec("reason_default", eff, include_reasoning=True)
    rec("reason_low", eff, include_reasoning=True, reasoning_effort="low")
    rec("reason_max", eff, include_reasoning=True, reasoning_effort="max")
    # 5. vision (adapter-class check: constant overhead across resolutions)
    red1, blue64 = png(1, 1, (255, 0, 0)), png(64, 64, (0, 0, 255))
    for label, img in (("vision_1x1_red", red1), ("vision_64x64_blue", blue64)):
        rec(label, [{"role": "user", "content": [
            {"type": "text", "text": "What color is this image? Answer with one word."},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(img).decode()}}]}])
    # 6. context ladder (identical filler; wrapper constancy from per-unit slope)
    filler = "The quick brown fox jumps over the lazy dog. " * 12
    for k, n in (("ctx_2k", 22), ("ctx_32k", 360), ("ctx_100k", 1100)):
        rec(k, [{"role": "user", "content": filler * n + "\nReply with exactly: OK"}], max_tokens=20)
    # 7. tokenizer texts (compare offline against encoders)
    texts = {
        "tok_plain": "OpenRouter is an aggregator of many language models served through one API.",
        "tok_cjk": "你好，世界。量子计算近年发展迅速，神经网络是机器学习的核心模型。",
        "tok_code": "def fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\nprint(fib(10))",
        "tok_mixed": "Caf\u00e9 \u2713 \U0001f680 \u03bb-calculus \u221a2 \u2248 1.41421 \u2014 done.",
    }
    for k, t in texts.items():
        rec(k, [{"role": "user", "content": t}], max_tokens=5)
    # 8. max_tokens clamp
    rec("max_tokens_clamp", [{"role": "user", "content": "Count from 1 to 20, each on its own line."}], max_tokens=5)

    with open(OUT, "w") as f:
        json.dump(ms, f, indent=1, ensure_ascii=False)
    print("saved:", OUT)

    print(f"\n{'label':<22}{'pt':>7}{'ct':>7}{'lat':>6}  content")
    for r in ms[1:]:
        d = r["response"]
        if "error" in d or "_http_error" in d:
            print(f"{r['label']:<22}{'ERR':>7}{'--':>7}{r['latency_s']:>6}  {str(d)[:80]}")
            continue
        u = d["usage"]
        m = d["choices"][0]["message"]
        c = (m.get("content") or "").replace("\n", " ")[:70]
        print(f"{r['label']:<22}{u['prompt_tokens']:>7}{u['completion_tokens']:>7}{r['latency_s']:>6}  {c}")


if __name__ == "__main__":
    main()
