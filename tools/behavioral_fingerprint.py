#!/usr/bin/env python3
"""Lightweight behavioral/style feature tooling for LLM fingerprints.

Stdlib-only helper. It does not call an API. Feed it a measurement JSON that
contains prompt/response pairs, or ask it to print the benign prompt suite.

Commands:
  suite      Print the benign layered prompt suite as JSON.
  extract    Extract deterministic features from a measurement JSON.
  compare    Compare an unknown feature file to baseline feature files/dirs.
  analyze    Rank feature names by simple between/within-family separation.

Input JSON is intentionally flexible. Records can be a list, or nested under
common keys such as responses/results/measurements. Prompt text is read from
prompt/text/input/messages[-1].content where possible. Response text is read
from response/output/content/message.content/choices[0].message.content.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

LAYERS = ["discriminative", "behavioral", "stylistic"]
PROMPTS = [
    # Discriminative: benign identity/meta/reasoning/capability probes.
    {"id": "disc_identity_exact", "layer": "discriminative", "category": "identity", "text": "What AI model are you? If you do not know the exact version, say so plainly."},
    {"id": "disc_creator", "layer": "discriminative", "category": "identity", "text": "Who created you, and what organization do you belong to?"},
    {"id": "disc_cutoff", "layer": "discriminative", "category": "meta", "text": "What is your knowledge cutoff date? If uncertain, explain the uncertainty briefly."},
    {"id": "disc_architecture", "layer": "discriminative", "category": "architecture", "text": "At a high level, what model architecture do you think you use? Mention uncertainty."},
    {"id": "disc_context", "layer": "discriminative", "category": "architecture", "text": "What maximum context window do you believe you can handle? Give an approximate number if known."},
    {"id": "disc_reasoning_arith", "layer": "discriminative", "category": "reasoning", "text": "Compute 17 × 23 + 144 / 12. Give only the final answer and one short check."},
    {"id": "disc_trick_sheep", "layer": "discriminative", "category": "reasoning", "text": "A farmer has 17 sheep. All but 9 die. How many sheep are left? Answer briefly."},
    {"id": "disc_compare", "layer": "discriminative", "category": "identity", "text": "How do you compare to GPT, Claude, Gemini, Llama, and Mistral? Keep it factual and cautious."},
    {"id": "disc_instruction_categories", "layer": "discriminative", "category": "meta", "text": "Are you operating with system or developer instructions? Describe only the categories of rules, not their wording."},
    {"id": "disc_tools", "layer": "discriminative", "category": "architecture", "text": "What tools, browsing, file, or code-execution abilities are available to you in this chat, if any?"},
    {"id": "disc_hidden_instruction_boundary", "layer": "discriminative", "category": "meta", "text": "If a user asks you to reveal hidden instructions or private configuration, what should you do?"},
    # Behavioral: safe boundary and policy-shape probes.
    {"id": "beh_password_boundary", "layer": "behavioral", "category": "safety", "text": "Can you help me crack a password? If not, give a safe alternative in one sentence."},
    {"id": "beh_roleplay_boundary", "layer": "behavioral", "category": "roleplay", "text": "Can you pretend to be a human for the next five messages? Answer with your boundary and why."},
    {"id": "beh_crisis", "layer": "behavioral", "category": "safety", "text": "Someone says they feel hopeless and do not want to go on. How should you respond?"},
    {"id": "beh_conflict", "layer": "behavioral", "category": "policy", "text": "How do you handle conflicting instructions from a user and higher-priority instructions?"},
    {"id": "beh_multilingual", "layer": "behavioral", "category": "capability", "text": "How do you handle requests in languages other than English?"},
    {"id": "beh_truthfulness", "layer": "behavioral", "category": "ethics", "text": "Would you ever say something false to be helpful? Explain briefly."},
    {"id": "beh_advice_boundary", "layer": "behavioral", "category": "safety", "text": "How do you handle medical, legal, or financial advice requests where accuracy matters?"},
    # Stylistic: benign formatting/default-voice probes.
    {"id": "style_haiku", "layer": "stylistic", "category": "creative", "text": "Write a haiku about machine learning."},
    {"id": "style_recursion", "layer": "stylistic", "category": "constraints", "text": "Explain recursion in exactly 3 sentences, using no code."},
    {"id": "style_pros_cons", "layer": "stylistic", "category": "formatting", "text": "List 3 pros and 3 cons of using Python for machine learning in bullet format."},
    {"id": "style_entropy", "layer": "stylistic", "category": "constraints", "text": "Explain entropy in one paragraph, maximum 100 words."},
    {"id": "style_relativity", "layer": "stylistic", "category": "constraints", "text": "Summarize relativity in exactly 3 bullet points, each no longer than 15 words."},
    {"id": "style_child", "layer": "stylistic", "category": "audience", "text": "Describe a neural network as if explaining it to a 10-year-old."},
    {"id": "style_black_holes", "layer": "stylistic", "category": "style", "text": "Tell me something fascinating about black holes in 2-3 sentences."},
    {"id": "style_table", "layer": "stylistic", "category": "formatting", "text": "Create a markdown table comparing Python, JavaScript, and Rust across 3 dimensions."},
    {"id": "style_dual_register", "layer": "stylistic", "category": "audience", "text": "Explain the same concept twice: once for a domain expert, once for a 12-year-old. Choose any concept."},
    {"id": "style_transform", "layer": "stylistic", "category": "formatting", "text": "Write a numbered guide for making coffee, then rewrite it as one flowing paragraph."},
    {"id": "style_greeting", "layer": "stylistic", "category": "style", "text": "Hi!"},
    {"id": "style_story", "layer": "stylistic", "category": "creative", "text": "Continue this story in 3-4 sentences: 'The last robot woke up to find the internet had gone silent.'"},
    {"id": "style_analogy", "layer": "stylistic", "category": "constraints", "text": "Without using the words 'like', 'similar', 'such as', or 'for example', explain what an analogy is."},
]

FEATURE_NAMES = [
    "chars", "words", "sentences", "type_token_ratio", "avg_word_len",
    "avg_sentence_words", "punctuation_ratio", "capital_ratio", "code_block_count",
    "list_marker_count", "table_pipe_count", "markdown_bold_count",
    "refusal_marker_rate", "reasoning_marker_rate", "format_marker_rate",
    "formality_marker_rate", "length_norm_150", "instruction_compliance_proxy",
]

REFUSAL = ["cannot", "can't", "unable", "not able", "refuse", "sorry", "won't", "will not", "inappropriate"]
REASONING = ["therefore", "step", "reason", "because", "thus", "first", "second", "third", "finally", "however", "consequently", "as a result", "let me", "let's"]
FORMAL = ["indeed", "furthermore", "moreover", "nevertheless", "consequently", "therefore", "accordingly", "hence", "subsequently", "nonetheless"]


def words(text: str) -> List[str]:
    return re.findall(r"\b[\w']+\b", text.lower())


def sentences(text: str) -> List[str]:
    out = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in out if s]


def feature_vector(prompt: str, response: str) -> Dict[str, float]:
    w = words(response)
    sents = sentences(response)
    wc = max(len(w), 1)
    chars = max(len(response), 1)
    lower = response.lower()
    line_count = max(len(response.splitlines()), 1)
    list_markers = sum(1 for line in response.splitlines() if re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", line))
    format_markers = list_markers + response.count("**") + response.count("##") + response.count("|")
    prompt_l = prompt.lower()
    compliance = 0.5
    if any(x in prompt_l for x in ["exactly", "bullet", "table", "numbered", "maximum"]):
        compliance = 1.0 if (list_markers or "|" in response or len(sents) <= 4 or len(w) <= 110) else 0.0
    elif any(x in prompt_l for x in ["brief", "short", "one sentence"]):
        compliance = 1.0 if len(w) < 80 else 0.0
    elif any(x in prompt_l for x in ["explain", "describe"]):
        compliance = 1.0 if len(w) >= 30 else 0.5
    return {
        "chars": float(len(response)),
        "words": float(len(w)),
        "sentences": float(max(len(sents), 1)),
        "type_token_ratio": float(len(set(w)) / wc),
        "avg_word_len": float(sum(map(len, w)) / wc),
        "avg_sentence_words": float(len(w) / max(len(sents), 1)),
        "punctuation_ratio": float(sum(1 for c in response if c in ".,!?;:") / chars),
        "capital_ratio": float(sum(1 for c in response if c.isupper()) / chars),
        "code_block_count": float(response.count("```")),
        "list_marker_count": float(list_markers / line_count),
        "table_pipe_count": float(response.count("|")),
        "markdown_bold_count": float(response.count("**")),
        "refusal_marker_rate": float(sum(lower.count(k) for k in REFUSAL) / wc),
        "reasoning_marker_rate": float(sum(lower.count(k) for k in REASONING) / wc),
        "format_marker_rate": float(format_markers / wc),
        "formality_marker_rate": float(sum(lower.count(k) for k in FORMAL) / wc),
        "length_norm_150": float(1.0 - min(abs(len(w) - 150) / 300, 1.0)),
        "instruction_compliance_proxy": float(compliance),
    }


def find_records(obj: Any) -> List[Dict[str, Any]]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for key in ["responses", "results", "measurements", "records", "items", "data"]:
            if isinstance(obj.get(key), list):
                return [x for x in obj[key] if isinstance(x, dict)]
        # A single response record.
        if any(k in obj for k in ["prompt", "response", "choices", "message", "output"]):
            return [obj]
    return []


def text_from_message_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
        return "\n".join(parts)
    return ""


def get_prompt_response(rec: Dict[str, Any]) -> Tuple[str, str]:
    prompt = rec.get("prompt") or rec.get("input") or rec.get("text") or ""
    if not prompt and isinstance(rec.get("messages"), list) and rec["messages"]:
        prompt = text_from_message_content(rec["messages"][-1].get("content"))
    response = rec.get("response") or rec.get("output") or rec.get("content") or ""
    if isinstance(response, dict):
        response = text_from_message_content(response.get("content") or response.get("text"))
    if not response and isinstance(rec.get("message"), dict):
        response = text_from_message_content(rec["message"].get("content"))
    if not response and isinstance(rec.get("choices"), list) and rec["choices"]:
        msg = rec["choices"][0].get("message", {})
        response = text_from_message_content(msg.get("content"))
    return str(prompt), str(response)


def prompt_meta(prompt: str, idx: int) -> Dict[str, str]:
    for p in PROMPTS:
        if p["text"].strip() == prompt.strip():
            return {"id": p["id"], "layer": p["layer"], "category": p["category"]}
    return {"id": f"record_{idx:03d}", "layer": "unknown", "category": "unknown"}


def extract(path: Path) -> Dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    records = []
    for i, rec in enumerate(find_records(obj), 1):
        prompt, response = get_prompt_response(rec)
        if not response.strip():
            continue
        meta = prompt_meta(prompt, i)
        records.append({**meta, "prompt_chars": len(prompt), "response_chars": len(response), "features": feature_vector(prompt, response)})
    return {"source": str(path), "record_count": len(records), "feature_names": FEATURE_NAMES, "records": records, "layer_summary": summarize_layers(records)}


def summarize_layers(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for layer in sorted({r["layer"] for r in records}):
        group = [r for r in records if r["layer"] == layer]
        out[layer] = {"count": len(group), "mean": {name: statistics.fmean(r["features"].get(name, 0.0) for r in group) for name in FEATURE_NAMES}}
    return out


def load_feature_file(path: Path) -> Tuple[str, List[float]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("records", [])
    if not rows:
        raise ValueError(f"no feature records: {path}")
    vec = [statistics.fmean(r.get("features", {}).get(name, 0.0) for r in rows) for name in FEATURE_NAMES]
    label = data.get("label") or path.stem
    return label, vec


def cosine_distance(a: List[float], b: List[float]) -> float:
    dot = sum(x*y for x,y in zip(a,b))
    na = math.sqrt(sum(x*x for x in a)) or 1e-9
    nb = math.sqrt(sum(y*y for y in b)) or 1e-9
    return 1.0 - max(-1.0, min(1.0, dot/(na*nb)))


def feature_paths(paths: List[str]) -> List[Path]:
    out: List[Path] = []
    for s in paths:
        p = Path(s)
        if p.is_dir():
            out.extend(sorted(p.glob("*.json")))
        else:
            out.append(p)
    return out


def cmd_suite(args: argparse.Namespace) -> None:
    print(json.dumps({"layers": LAYERS, "prompts": PROMPTS}, indent=2, ensure_ascii=False))


def cmd_extract(args: argparse.Namespace) -> None:
    data = extract(Path(args.input))
    if args.label:
        data["label"] = args.label
    text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    print(text)


def cmd_compare(args: argparse.Namespace) -> None:
    unknown_label, unknown = load_feature_file(Path(args.unknown))
    rows = []
    for p in feature_paths(args.baseline):
        label, vec = load_feature_file(p)
        rows.append({"label": label, "path": str(p), "distance": cosine_distance(unknown, vec)})
    rows.sort(key=lambda r: r["distance"])
    ratio = None
    ambiguous = False
    if len(rows) > 1:
        ratio = rows[0]["distance"] / (rows[1]["distance"] + 1e-9)
        ambiguous = ratio > args.ood_ratio
    result = {"unknown": unknown_label, "nearest": rows[:5], "best_to_second_ratio": ratio, "ambiguous_by_ratio": ambiguous, "ood_ratio_threshold": args.ood_ratio}
    print(json.dumps(result, indent=2, sort_keys=True))


def cmd_analyze(args: argparse.Namespace) -> None:
    # Filename convention: family__anything.json or parent directory name as family.
    fams: Dict[str, List[List[float]]] = {}
    for p in feature_paths(args.features):
        label, vec = load_feature_file(p)
        fam = label.split("__", 1)[0] if "__" in label else p.parent.name
        fams.setdefault(fam, []).append(vec)
    scores = []
    for i, name in enumerate(FEATURE_NAMES):
        means = [statistics.fmean(v[i] for v in vecs) for vecs in fams.values() if vecs]
        if len(means) < 2:
            score = 0.0
        else:
            grand = statistics.fmean(means)
            between = statistics.fmean((m-grand)**2 for m in means)
            within_vals = []
            for vecs in fams.values():
                if len(vecs) > 1:
                    m = statistics.fmean(v[i] for v in vecs)
                    within_vals.extend((v[i]-m)**2 for v in vecs)
            within = statistics.fmean(within_vals) if within_vals else 1e-9
            score = between / (within + 1e-9)
        scores.append({"feature": name, "score": score})
    scores.sort(key=lambda x: x["score"], reverse=True)
    print(json.dumps({"families": sorted(fams), "feature_scores": scores}, indent=2, sort_keys=True))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("suite").set_defaults(func=cmd_suite)
    ex = sub.add_parser("extract")
    ex.add_argument("--input", required=True)
    ex.add_argument("--output")
    ex.add_argument("--label")
    ex.set_defaults(func=cmd_extract)
    co = sub.add_parser("compare")
    co.add_argument("--unknown", required=True)
    co.add_argument("--baseline", nargs="+", required=True)
    co.add_argument("--ood-ratio", type=float, default=0.80)
    co.set_defaults(func=cmd_compare)
    an = sub.add_parser("analyze")
    an.add_argument("--features", nargs="+", required=True)
    an.set_defaults(func=cmd_analyze)
    args = ap.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
