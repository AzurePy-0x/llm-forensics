# Analysis techniques (worked math)

## 1. Cached-prefix subtraction

An anonymous wrapper usually prepends a stable system template. It shows up in
`usage.prompt_tokens_details.cached_tokens` as a constant on every request:

- measured user-message tokens = `pt − cached_tokens` (exact; framing noise gone)
- wrapper overhead = the constant itself (e.g. a 149-token cached system prefix)

The same field doubles as a serving-stack probe: with identical repeated prefixes across
requests, `cached_tokens` grows to the *previous request's full prompt total*. That
cross-request prefix caching is an observable property of the serving path.

Sanity check the subtraction: for a known filler unit, per-unit token rate must be
constant across ladder rungs (e.g. a 541-char unit at 120.00 tok/unit from 22 to 1100
units, drift < 0.3%). A stable slope = single fixed serving path.

## 2. Long-text tokenizer discrimination

Short probe texts drift ±7 tokens between requests (per-request framing variance), so
their counts cannot settle an encoder. Use long texts (1.5–2.5KB) where framing is
negligible, and read the **CJK chars/token rate** — the strongest discriminator between
OpenAI encoders and Chinese-first BPEs:

| encoder / class | CJK chars/token (typical) |
|---|---|
| cl100k_base | ~1.0 (≈ 1 token/char) |
| o200k_base | ~1.45 |
| Chinese-first byte-level BPE (MiniMax/GLM/Qwen-class) | ~2.0 |

Worked example (measured 1,680-char CJK text → 812 tokens):

- cl100k would emit 1,800 → error −988 → refuted
- o200k would emit 1,160 → error −348 → refuted
- English (2,220 chars → 433 tok, 5.13 chars/tok) and code (2,369 chars → 972 tok,
  2.44 chars/tok) are both mainstream BPE rates — no discriminating power

Verdict shape: high-confidence *negative* ("not OpenAI-family"), medium-confidence
*direction* ("Chinese-first BPE class"). Do not claim a family without a vocab file.

## 3. Offline encoder comparison

Install tiktoken in a throwaway venv (PEP 668 on Debian-family hosts):

```bash
python3 -m venv <scratch>/tokvenv
<scratch>/tokvenv/bin/pip install -q tiktoken
```

```python
import tiktoken
for enc_name in ("cl100k_base", "o200k_base"):
    enc = tiktoken.get_encoding(enc_name)
    # compare len(enc.encode(text)) against measured pt − cached on the SAME long texts
```

## 4. Knowledge ladder

Pending facts ladder: correctly-dated public events across ~18 months. Effective
knowledge = newest correctly dated. Self-claimed cutoff = noise when contradicted
(e.g. claimed "mid-2024", correctly dated a Feb-2026 launch).

## 5. Reasoning accounting quirk

`usage.completion_tokens_details.reasoning_tokens` can read 0 while `message.reasoning`
(+ `reasoning_details`, `type: reasoning.text`) carries full chain-of-thought. Reasoning
consumes `max_tokens`: budgets ≤~60 leave `content: null, finish_reason: length` and empty
logprobs — free the content channel with `reasoning_effort: 'low'` + ~250 budget whenever
a probe must produce visible content tokens.
Compare effort rungs by completion-token count on an identical prompt instead
(default/low ≈ equal, `max` measurably longer).

## 6. Vision adapter-class signature

`pt(image) − pt(text)` constant across wildly different resolutions (1x1 == 64x64)
means adapter-class image embedding (fixed video-style patch, no per-token cost). A
degenerate 1x1 solid color misread (red → "Gray") while a 64x64 solid color passes is
the expected failure signature of such adapters.

## 7. Positive vocab-file identification (token sweep)

Settle the FAMILY with a vocab-file match, not just the CJK rate direction:

1. Fix 4 long corpora: ~2K-char CJK prose, ~12K code, ~6K mixed (Unicode/emoji/scripts), ~16K plain English.
2. Live: one call per corpus plus a one-char baseline. Δ = pure content tokens — template framing cancels exactly.
3. Offline: encode the SAME strings with candidate vocab files (`tokenizers.Tokenizer.from_file` for tokenizer.json, `tiktoken` for .tiktoken). A match = every column within the SAME small constant Δ (the chat template's framing token, e.g. +1 in all four columns; additive, so the vocabulary counts are identical). Report the nearest runner-up gap (tens to hundreds of tokens) — it is the discrimination power.
4. Candidate URLs (HF, fresh): `MiniMaxAI/MiniMax-Text-01`, `deepseek-ai/DeepSeek-V3`, `Qwen/Qwen2.5-72B-Instruct`, `zai-org/GLM-4.5-Air`, `NousResearch/Meta-Llama-3-8B` tokenizer.json; `moonshotai/Kimi-K2.5` tiktoken.model + tokenization_kimi.py (build the Encoding with its pat_str — extract the list literal with `ast.literal_eval`, not regex). Newer Qwen repos dropped qwen.tiktoken — use tokenizer.json.
5. Pitfalls: (a) lone-surrogate escapes (`\ud83d\ude80`) in corpus strings crash tokenizers' Rust encode — write astral chars as `\U0001F680`; (b) a vocab match proves the FAMILY only — MiniMax/other vendors share one tokenizer across generations, so still narrow the checkpoint with context ceiling, knowledge window, and reasoning behavior.

Worked verdict: MiniMax-Text-01 vocab matched stealth/space-bunny-alpha 4/4 within a constant +1 (970/5099/3159/2760 live vs 971/5100/3160/2761); DeepSeek-V3 runner-up off by +50..+321 → positive MiniMax-family ID from a single 5-call battery.
