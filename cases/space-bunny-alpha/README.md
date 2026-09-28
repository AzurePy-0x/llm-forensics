# Case: space-bunny-alpha

**Listing:** `stealth/space-bunny-alpha` · **Provider:** OpenRouter (free tier, $0.00 during all
measurement runs) · **Measured:** 2026-09-27 → 2026-09-28

## Verdict (family level)

**MiniMax-family** — vocabulary fingerprint matches `MiniMaxAI/MiniMax-Text-01` within one constant
framing token across CJK / code / mixed-Unicode / English corpora, reproduced twice with independent
corpora. Exact checkpoint and official provenance unconfirmed.

## Supporting findings

- Stable stealth wrapper (fixed prompt-prefix/cache signature); OpenAI-compatible response shape with
  `logprobs` always null.
- Mandatory reasoning surface; reasoning surfaced in response while usage accounting reports 0.
- Vision input with resolution-constant token overhead (adapter-class image handling).
- 1M-class declared context; gateway pre-gates very large requests.
- Strong default identity prior with clean override semantics; rank-blind to system-vs-user role placement
  of a supplied maker claim (serving-path finding).
- Three-tier system/developer/user channel vocabulary volunteered consistently (serving-path / corpus
  fingerprint).
- No verbatim system-prompt leak across five independent sessions (direct, encoded, and rapport-style
  framings).

## Reproduce

1. Live: replicate the tokenizer counts (see `report.md` § "Tokenizer evidence") against the endpoint.
2. Offline: `tools/offline_tokenizer_compare.py` — encodes the same corpora with candidate vocabularies.
3. Behavioral: `tools/behavioral_fingerprint.py suite --model stealth/space-bunny-alpha`.

## Artifacts

- `report.md` — the full public-edition dossier
- `verdicts.json` — machine-readable verdicts
- `measurements/` — sanitized aggregate data (behavioral features, live tokenizer deltas)