#!/usr/bin/env python3
"""Dependency-free localization catalog validator.

The checks are deliberately conservative: structural errors fail CI, while
language-quality heuristics are reported for human review.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


PLACEHOLDER_RE = re.compile(r"\{([A-Za-z][A-Za-z0-9_]*)\}")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
LATIN_WORD_RE = re.compile(r"\b[A-Za-z]{4,}\b")
JAPANESE_RE = re.compile(r"[\u3040-\u30ff\u3400-\u9fff]")
SUSPICIOUS_JA_PATTERNS = (
    (re.compile(r"あなたの(?:注文|商品)"), "Consider omitting 'あなたの' when context is already clear."),
    (re.compile(r"することができます"), "Consider the more concise 'できます'."),
    (re.compile(r"くださいませ[。！!]?$"), "Confirm that this level of formality matches the product voice."),
)


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    key: str
    message: str

    def render(self) -> str:
        location = f" [{self.key}]" if self.key else ""
        return f"{self.severity.upper():7} {self.code}{location}: {self.message}"


def load_json(path: Path) -> Mapping[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Catalog root must be an object: {path}")
    return value


def flatten(value: Mapping[str, Any], prefix: str = "") -> Dict[str, str]:
    result: Dict[str, str] = {}
    for key, child in value.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(child, dict):
            result.update(flatten(child, path))
        elif isinstance(child, str):
            result[path] = child
        else:
            raise ValueError(f"Translation value must be a string or object: {path}")
    return result


def placeholders(message: str) -> Set[str]:
    return set(PLACEHOLDER_RE.findall(message))


def validate_catalogs(source: Mapping[str, Any], target: Mapping[str, Any]) -> List[Finding]:
    source_flat = flatten(source)
    target_flat = flatten(target)
    findings: List[Finding] = []

    for key in sorted(source_flat.keys() - target_flat.keys()):
        findings.append(Finding("error", "missing-key", key, "Target catalog is missing this translation key."))
    for key in sorted(target_flat.keys() - source_flat.keys()):
        findings.append(Finding("error", "extra-key", key, "Target catalog has no matching source key."))

    for key in sorted(source_flat.keys() & target_flat.keys()):
        source_text, target_text = source_flat[key], target_flat[key]
        source_tokens, target_tokens = placeholders(source_text), placeholders(target_text)
        if source_tokens != target_tokens:
            findings.append(Finding(
                "error", "placeholder-mismatch", key,
                f"Expected {sorted(source_tokens)} but found {sorted(target_tokens)}.",
            ))
        if not target_text.strip():
            findings.append(Finding("error", "empty-translation", key, "Translation is empty."))
        if target_text != target_text.strip():
            findings.append(Finding("warning", "outer-whitespace", key, "Translation has leading or trailing whitespace."))
        if CONTROL_RE.search(target_text) or "\ufffd" in target_text:
            findings.append(Finding("error", "invalid-character", key, "Translation contains a control or replacement character."))
        findings.extend(japanese_quality_hints(key, target_text))
    return findings


def japanese_quality_hints(key: str, text: str) -> List[Finding]:
    hints: List[Finding] = []
    visible = PLACEHOLDER_RE.sub("", text)
    latin_words = LATIN_WORD_RE.findall(visible)
    if latin_words and not JAPANESE_RE.search(visible):
        hints.append(Finding("warning", "untranslated-text", key, "Text appears to contain no Japanese characters."))
    elif len(latin_words) >= 3:
        hints.append(Finding("warning", "latin-heavy", key, "Several Latin words remain; confirm they are intentional."))
    for pattern, message in SUSPICIOUS_JA_PATTERNS:
        if pattern.search(text):
            hints.append(Finding("warning", "style-review", key, message))
    return hints


def extract_simple_yaml_keys(path: Path) -> Set[str]:
    """Extract dotted keys from the intentionally simple sample YAML files.

    This is not a general YAML parser; it avoids presenting a partial parser as
    production-ready while still checking that the portfolio's paired YAML
    examples have the same structure without adding a dependency.
    """
    keys: Set[str] = set()
    stack: List[Tuple[int, str]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        match = re.match(r'^\s*([A-Za-z0-9_-]+):(?:\s+(.*))?$', raw)
        if not match:
            raise ValueError(f"Unsupported sample YAML syntax at {path}:{number}")
        name, scalar = match.groups()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if scalar is None:
            stack.append((indent, name))
        else:
            keys.add(".".join([item[1] for item in stack] + [name]))
    return keys


def validate_yaml_pair(source_path: Path, target_path: Path) -> List[Finding]:
    source_keys, target_keys = extract_simple_yaml_keys(source_path), extract_simple_yaml_keys(target_path)
    findings: List[Finding] = []
    for key in sorted(source_keys - target_keys):
        findings.append(Finding("error", "yaml-missing-key", key, "Japanese YAML sample is missing this key."))
    for key in sorted(target_keys - source_keys):
        findings.append(Finding("error", "yaml-extra-key", key, "Japanese YAML sample has no matching English key."))
    return findings


def summarize(findings: Sequence[Finding]) -> Tuple[int, int]:
    errors = sum(item.severity == "error" for item in findings)
    warnings = sum(item.severity == "warning" for item in findings)
    return errors, warnings


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Validate English and Japanese localization catalogs.")
    parser.add_argument("--source", type=Path, default=Path("locales/en.json"))
    parser.add_argument("--target", type=Path, default=Path("locales/ja.json"))
    parser.add_argument("--source-yaml", type=Path, default=Path("locales/en.yaml"))
    parser.add_argument("--target-yaml", type=Path, default=Path("locales/ja.yaml"))
    parser.add_argument("--warnings-as-errors", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        findings = validate_catalogs(load_json(args.source), load_json(args.target))
        findings.extend(validate_yaml_pair(args.source_yaml, args.target_yaml))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR   catalog-read: {exc}", file=sys.stderr)
        return 2

    for finding in findings:
        print(finding.render())
    errors, warnings = summarize(findings)
    print(f"Checked localization catalogs: {errors} error(s), {warnings} warning(s).")
    if errors or (warnings and args.warnings_as_errors):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
