import json
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from scripts.localization_qa import (
    extract_simple_yaml_keys,
    flatten,
    placeholders,
    validate_catalogs,
    validate_yaml_pair,
)


ROOT = Path(__file__).resolve().parents[1]


class I18nKeyParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.keys = set()
        self.asset_paths = []

    def handle_starttag(self, _tag, attrs):
        attributes = dict(attrs)
        if "data-i18n" in attributes:
            self.keys.add(attributes["data-i18n"])
        for attribute in ("href", "src"):
            value = attributes.get(attribute)
            if value and not value.startswith(("#", "http://", "https://", "mailto:")):
                self.asset_paths.append(value)


class LocalizationQATests(unittest.TestCase):
    def test_portfolio_catalogs_pass_without_findings(self):
        en = json.loads((ROOT / "locales/en.json").read_text(encoding="utf-8"))
        ja = json.loads((ROOT / "locales/ja.json").read_text(encoding="utf-8"))
        self.assertEqual(validate_catalogs(en, ja), [])

    def test_flatten_builds_dotted_keys(self):
        self.assertEqual(flatten({"a": {"b": "value"}}), {"a.b": "value"})

    def test_placeholder_extraction_is_deduplicated(self):
        self.assertEqual(placeholders("{name}: {count}, {name}"), {"name", "count"})

    def test_missing_extra_and_placeholder_mismatch_are_errors(self):
        findings = validate_catalogs(
            {"kept": "Hello {name}", "missing": "Missing"},
            {"kept": "こんにちは、{user}さん", "extra": "追加"},
        )
        codes = {item.code for item in findings}
        self.assertTrue({"missing-key", "extra-key", "placeholder-mismatch"} <= codes)

    def test_control_and_replacement_characters_are_rejected(self):
        findings = validate_catalogs({"a": "A", "b": "B"}, {"a": "あ\u0007", "b": "い\ufffd"})
        self.assertEqual([item.code for item in findings].count("invalid-character"), 2)

    def test_suspicious_japanese_style_is_a_warning(self):
        findings = validate_catalogs({"message": "Your order"}, {"message": "あなたの注文を確認することができます"})
        self.assertIn("style-review", {item.code for item in findings})
        self.assertTrue(all(item.severity == "warning" for item in findings))

    def test_untranslated_english_is_flagged(self):
        findings = validate_catalogs({"message": "Save changes"}, {"message": "Save changes"})
        self.assertIn("untranslated-text", {item.code for item in findings})

    def test_yaml_pair_has_matching_keys(self):
        findings = validate_yaml_pair(ROOT / "locales/en.yaml", ROOT / "locales/ja.yaml")
        self.assertEqual(findings, [])

    def test_yaml_missing_key_is_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root / "en.yaml", root / "ja.yaml"
            source.write_text('group:\n  one: "One"\n  two: "Two"\n', encoding="utf-8")
            target.write_text('group:\n  one: "一"\n', encoding="utf-8")
            findings = validate_yaml_pair(source, target)
            self.assertEqual([item.code for item in findings], ["yaml-missing-key"])

    def test_every_html_translation_key_exists_in_both_catalogs(self):
        parser = I18nKeyParser()
        parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
        for locale in ("en", "ja"):
            catalog = json.loads((ROOT / f"locales/{locale}.json").read_text(encoding="utf-8"))
            missing = parser.keys - set(flatten(catalog))
            self.assertEqual(missing, set(), f"Missing {locale} UI keys: {sorted(missing)}")

    def test_displayed_key_count_matches_catalog(self):
        en = json.loads((ROOT / "locales/en.json").read_text(encoding="utf-8"))
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn(f">{len(flatten(en))}/{len(flatten(en))}<", html)

    def test_site_assets_are_safe_for_github_pages_subpath(self):
        parser = I18nKeyParser()
        parser.feed((ROOT / "index.html").read_text(encoding="utf-8"))
        absolute_paths = [path for path in parser.asset_paths if path.startswith("/")]
        self.assertEqual(absolute_paths, [], f"Root-absolute paths break project Pages: {absolute_paths}")
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn('fetch(`locales/${locale}.json`)', app)


if __name__ == "__main__":
    unittest.main()
