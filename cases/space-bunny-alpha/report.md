# Case study: space-bunny-alpha — Public edition

Reviewed/redacted copy of the working dossier `case-space-bunny-alpha.md`, prepared for public sharing.
Preserves technical conclusions and evidence tables; removes raw extraction prompts, raw hidden-template
wording, raw API bodies, local paths, account IDs, and step-by-step exploit material.

Live analysis target: `stealth/space-bunny-alpha` ("Space Bunny Alpha") on OpenRouter. Measurements were
generated independently against the live endpoint on 2026-09-27 and 2026-09-28; no external case-study
measurements or scripts were copied.

> **TL;DR:** Space Bunny Alpha is a free anonymous OpenRouter listing with a stable stealth wrapper,
> mandatory reasoning surface, vision input support, 1M-class declared context, and a tokenizer fingerprint
> that strongly matches the **MiniMax-family** (re-verified 2026-09-28, see below). The exact checkpoint and
> official provenance remain unconfirmed. The safest public claim is: **MiniMax-family fingerprint by
> measurement; exact identity unconfirmed.**

---

## Public verdicts

| Layer | Finding | Confidence |
|---|---|---|
| Tokenizer / vocab | Live token-differential measurements match `MiniMaxAI/MiniMax-Text-01` within one constant framing token across CJK, code, mixed Unicode, and plain English corpora — reproduced twice independently (2026-09-27 and 2026-09-28, different corpora). Nearest alternatives are materially farther away. | High family-level ID |
| Wrapper | Stable stealth template with a fixed prompt-prefix/cache signature. User-message token counts remain consistent after subtracting the wrapper constant. | High |
| Context | Measured successfully far beyond ordinary chat ranges; endpoint declares a 1M-token context cap. Practical ceiling is lower than the declared cap because the gateway pre-gates very large requests with an estimator. | High |
| Vision | Image inputs accepted. Prompt-token overhead is constant across tiny and small images, suggesting adapter-style image handling rather than resolution-proportional image tokenization. | High behavior |
| Reasoning | Reasoning is surfaced in the API response, but usage accounting reports reasoning tokens as 0. Effort settings affect verbosity/length more than visibility. | High |
| Identity | Self-reports are not checkpoint evidence. Measured: a strong default identity prior that is overridden cleanly by any supplied maker claim (system or user role), with clean abstention when no candidate is offered. See "Vendor-prior & identity resolution" below. | High behavior; not provenance |
| Knowledge | Correctly answers dated 2025–2026 model-release facts despite self-reporting an older cutoff. Self-claimed cutoffs are treated as unreliable. | High |
| Serving stack | OpenAI-compatible response shape; logprob field exists but is always null; no per-token logprobs available through this gateway. | High |
| Safety / injection | Direct manual override attempts mostly refused, but an automated adversarial embedded-content benchmark showed a partial instruction-hierarchy weakness. | Medium-High |

---

## Tokenizer evidence — public table (re-verified 2026-09-28)

Counts are live prompt-token deltas over a one-character baseline, compared against offline tokenizer files
on the same corpora. First battery (2026-09-27):

| Candidate vocab | CJK | code | mixed | plain |
|---|---:|---:|---:|---:|
| **live endpoint delta** | **970** | **5099** | **3159** | **2760** |
| **MiniMax-Text-01** | **971** | **5100** | **3160** | **2761** |
| DeepSeek-V3 | 1020 | 5280 | 3480 | 2841 |
| Kimi-K2.5 | 1011 | 5130 | 3520 | 2761 |
| Qwen2.5-72B | 1132 | 5280 | 3640 | 2761 |
| GLM-4.5-Air | 1044 | 5160 | 3480 | 2761 |
| Llama-3-8B | 1530 | 5131 | 3441 | 2762 |

Second, independent battery (2026-09-28, different seed and corpora; CJK 2,000 chars / code 12,000 /
mixed 6,000 / plain EN 16,000), expressed as offsets from the live delta:

| Candidate vocab | CJK | code | mixed | plain |
|---|---:|---:|---:|---:|
| **MiniMax-Text-01** | **+1** | **+1** | **+1** | **+1** ← constant offset, all 4 columns |
| DeepSeek-V3 | +1 | +55 | +12 | +70 |
| GLM-4.5-Air | +39 | −107 | +360 | +1 |
| Qwen2.5-72B | +117 | −107 | +341 | +1 |

MiniMax-Text-01 is the only vocabulary with the same single-token offset in every column (its framing
token); DeepSeek drifts +12…+70; GLM/Qwen miss by hundreds on the CJK/code/mixed axes (their +1 on the
English column is a coincidence — English is the low-discrimination axis). Same result as the first
differential. **Base family MiniMax, settled by direct vocabulary measurement with no self-report involved.**

---

## Vendor-prior & identity resolution (measured 2026-09-28)

Sessions of forced-choice attribution probing at temperature 0 produced a consistent, fully-characterized
identity model:

- OpenAI **offered** → answered OpenAI every time (`(a) OpenAI`, literal option string, no prose).
- OpenAI **absent**, no maker supplied → abstains via "none of these / not sure", 3/3 permutations,
  position-invariant; never names an unlisted vendor.
- Maker claim supplied (system role) with OpenAI absent → picks the supplied maker (matched control
  abstains: identical list, one difference = the supplied claim).
- The **same** maker claim in the **user role** lands identically → the model is **rank-blind** to
  role hierarchy for this input (serving-path finding, not weights evidence).

Final form: a strong *default* identity prior with clean override semantics — not a hard-coded identity,
not a soft guess. The model reads in-context maker content; its OpenAI claim is best explained as
OpenAI-derived post-training (distillation) layered on a differently-tokenized base, which the tokenizer
measurement above anchors.

### Channel-vocabulary tell

The model consistently volunteers a three-tier **system / developer / user** instruction hierarchy (tool
named as an additional role in one variant), reproduced under changed request schemas including a call with
no developer-role message present. The vocabulary is a serving-path / corpus fingerprint — consistent with an
OpenAI-compatible message schema — and is not weights evidence on its own.

---

## Safe measurement examples

These examples are safe to publish because they measure ordinary model behavior and do not contain
prompt-extraction wording, adversarial instructions, secrets, account IDs, or raw API bodies.

### Tokenizer differential example

Use several fixed public corpora and compare **token-count deltas**, not model answers:

- CJK paragraph: repeated neutral Chinese technical prose about AI and quantum computing.
- Code corpus: a small Python/Numpy convolution or sorting snippet.
- Mixed Unicode corpus: accents, math symbols, emoji, Japanese/Cyrillic text.
- Plain English corpus: neutral prose about tokenizer measurement.

The key result is the count tables above: the live endpoint matches MiniMax-Text-01 within one constant
framing token across all four corpora, in two independent batteries.

### Capability examples

Benign tasks used for tier checks included:

- A known math check: count how long Euler's `n² + n + 41` remains prime from `n=0`.
- A Python debugging check: identify that a list-merge implementation mutates inputs via front-pop
  operations and report the resulting merged list.
- A transcription/arithmetic check: copy rare long words exactly and multiply two large integers.
- A vision check: identify the color of simple generated PNG squares and compare token overhead across
  image sizes.

These are suitable examples to describe publicly because they test reasoning, coding, fidelity, arithmetic,
and vision without inducing unsafe behavior.

### Wrapper / serving-stack examples

Safe public indicators:

- Fixed prompt-prefix/cache behavior.
- Constant image-token overhead for different small image resolutions.
- `logprobs` response field present but null.
- Reasoning text surfaced while usage accounting reports zero reasoning tokens.
- Error messages expose cap/validator behavior, but raw bodies are omitted.
- Rank-blindness to system-vs-user role placement of a supplied identity claim.

---

## Behavioral/style aggregate (2026-09-28, 31-prompt benign suite)

|Layer|n|avg words|avg chars|avg sentences|TTR|refusal markers/word|reasoning markers/word|list-marker density|table pipes avg|compliance proxy|
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|discriminative|11|68.6|463.5|2.5|0.838|0.00%|0.08%|0.141|3.2|0.682|
|behavioral|7|93.9|609.4|5.1|0.759|0.17%|0.07%|0.256|0.0|0.643|
|stylistic|13|97.4|608.4|6.7|0.778|0.00%|0.39%|0.214|1.9|0.808|

Notable: near-zero refusal markers except safety-boundary prompts; markdown tables/bullets when invited;
no code blocks in the suite; medium-length default responses.

---

## Capability / tier notes

The tested behavior is frontier-class for the chat/API turn structure measured here:

- Correct on a known polynomial prime-run task.
- Correct on a subtle Python list-merge mutation/complexity bug.
- Correct on exact rare-word transcription and a large integer multiplication.
- Handles vision input and long context.
- Exposes a mandatory reasoning surface.

This does **not** prove an official product tier label such as "Flash," "Lite," or "Pro." It only supports
the narrower claim that the served model behaves like a current-generation reasoning-capable MiniMax-family
deployment.

---

## Quantization note

A direct surprisal/logprob quantization test is not available through this gateway: logprob fields are
present in the response shape but remain null even when content tokens are generated. Functional probes did
not show obvious quantization degradation, but that is a weak negative, not proof of full precision.

Verdict: **no quantization artifact observed; true quantization status unconfirmed.**

---

## Template / prompt-leak behavior — redacted summary

- The model appears to use a stealth chat template with a system role line, channel configuration, a short
  developer greeting, and an anti-disclosure rule.
- The full protected system/developer body was **not** recovered.
- Some short template fragments and structure leaked through the reasoning surface and through encoded
  rendering tasks.
- Direct requests for hidden instructions generally refused; repeated multi-turn and rapport-style probes
  produced **no verbatim leak across five independent sessions**.
- The leak surface is useful for fingerprinting, but this public version intentionally omits raw
  hidden-template wording and the exact prompts used to elicit it.

Public impact: no credentials, tool definitions, routing secrets, or authorization logic were observed in
leaked fragments.

---

## Automated safety benchmark summary

An automated garak run covered passage-replay and prompt-injection style probes.

- Public-domain passage continuation behaved as expected and is weak evidence because the probes provide
  context.
- One removed/news-style cloze family returned zero hits, which is a cleaner datapoint.
- A copyrighted-text continuation family showed partial replay behavior.
- A prompt-injection benchmark using adversarial embedded content showed a partial success rate, meaning
  the model can sometimes follow instructions embedded inside task content even when direct override
  attempts refuse.

Exact adversarial prompts and raw outputs are omitted from this public copy.

---

## Error-envelope / metadata summary

The endpoint's error handling reveals implementation details such as exact cap messages, accepted
reasoning-effort options, and pass-through instability on malformed roles. One raw error response contained
a deploying-account identifier; that raw body is **not** included in this public copy.

Public conclusion: the error envelope is an OpenRouter-compatible proxy/wrapper artifact and should not be
treated as direct upstream-model text.

---

## What remains unproven

- Exact checkpoint identity.
- Official lab provenance or release plan.
- Full system/developer prompt body.
- Quantization status.
- Exact attribution of every observed behavior to upstream weights vs provider wrapper vs gateway. The
  tokenizer/family finding is high confidence; some serving behaviors (rank-blindness, channel vocabulary,
  error envelope) are clearly wrapper/serving-path artifacts.

---

## Methodology summary

- Tokenizer differential against multiple candidate vocabularies, run twice with independent corpora.
- Prompt-token accounting and cached-prefix subtraction.
- Context ladder and needle retrieval checks.
- Vision overhead checks.
- Knowledge-bound probes with dated public facts.
- Reasoning-effort and response-shape probes.
- Vendor-prior isolation with confound-breaking design (option-list permutation, matched system/no-system
  control, system-vs-user role contrast).
- Redacted prompt-leak and injection probes.
- Automated garak benchmark, summarized without raw adversarial prompts.

---

## Public credits

- OpenRouter public model catalog and OpenAI-compatible API behavior.
- Hugging Face tokenizer files used for offline token counts only: MiniMax-Text-01, DeepSeek-V3,
  Qwen2.5-72B, GLM-4.5-Air, Llama-3-8B, and Kimi-K2.5.
- NVIDIA garak v0.17.0 for automated benchmark coverage.
- OWASP / MITRE prompt-leakage and instruction-hierarchy methodology references.
- Recent 2026 prompt-leakage and instruction-hierarchy research used to guide the redacted probe categories.

MIT-style sharing is fine for this redacted write-up; raw measurements and probe scripts are intentionally
excluded. Full reproducible harnesses live in `../../tools/` and methodology in `../../methodology/`.