# LLM Forensics

Independent, measurement-based fingerprinting of LLM endpoints — identifying anonymous / stealth /
code-named models, **and** verifying that known, named models are actually what is being served
(catching model-card mismatches, swaps, or wrapper substitutions).

Each case folder documents one model (or code name, when the listing is a stealth release): what was
measured against the **live endpoint only**, which family the evidence points to, and what remains
unproven.

## Status

- [x] `cases/space-bunny-alpha/` — `stealth/space-bunny-alpha` (OpenRouter, free listing) → tokenizer
      matches MiniMax-Text-01 within one constant framing token (reproduced twice); exact checkpoint
      unconfirmed.

## How to read a case

Every case ships:

| File | What it is |
|---|---|
| `report.md` | Redacted public-edition fingerprint dossier (verdicts, evidence tables, limits) |
| `verdicts.json` | Machine-readable layer → verdict → confidence |
| `measurements/` | Sanitized aggregates only — no raw transcripts, no credentials |
| `README.md` | Case summary and reproduction pointers |

Unified tooling lives in `tools/`; the method lives in `methodology/fingerprinting.md`. Cases never
duplicate tooling, so method updates apply repo-wide.

## Ground rules

- Measurements are generated against the live endpoint by this project; no external case-study data is
  copied.
- Self-reports (vendor claims, cutoff dates, identity) are **never treated as provenance**. They are
  measured as behaviors.
- A tokenizer/vocabulary match settles the **family**; it does not settle the exact checkpoint.
- Raw extraction prompts, hidden-template wording, raw API bodies, and credentials never appear in this
  repo.
- Every claim carries a confidence label; "remains unproven" items are listed explicitly per case.

## Reproduction

```bash
# tokenizer differential (needs an API key for the target + offline tokenizer files)
python tools/offline_tokenizer_compare.py --live-labels ...    # see tool --help

# behavioral/style suite
python tools/behavioral_fingerprint.py suite --model <slug>
```

Probe harnesses read the key from the shell environment or a profile `.env` — never from this repo.

## License

MIT (see LICENSE). Reports remain the authors' work; measurements are facts about a public API.