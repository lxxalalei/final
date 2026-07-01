#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def load_module(name: str, filename: str):
    path = ROOT / "resource-selector/scripts" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


prepare = load_module("selector_prepare", "prepare_candidates.py")
validate = load_module("selector_validate", "validate_review.py")
finalize = load_module("selector_finalize", "finalize_selection.py")
render = load_module("selector_render", "render_review.py")


class TestSelectorWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.session = Path(self.temp.name)
        intent = {
            "_meta": {"session_id": "s1"},
            "data": {"clarified_need": "测试学习资源需求", "evidence": [], "requirements": []},
        }
        stage3 = {
            "_meta": {"session_id": "s1"},
            "data": {
                "resources": [
                    {"resource_id": "a:1", "platform": "a", "title": "四年级数学课程", "source_url": "https://example.test/a?utm_source=x"},
                    {"resource_id": "a:2", "platform": "a", "title": "四年级数学课程", "source_url": "https://example.test/a", "description": "完整课程"},
                    {"resource_id": "b:1", "platform": "b", "title": "高等数学", "source_url": "https://example.test/b"},
                ],
                "errors": [],
            },
        }
        (self.session / "stage1_intent.json").write_text(json.dumps(intent), encoding="utf-8")
        (self.session / "stage3_search_results.json").write_text(json.dumps(stage3), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_prepare_exact_dedup_keeps_more_complete_resource(self) -> None:
        result = prepare.prepare(self.session)
        self.assertEqual(result["_summary"]["raw_count"], 3)
        self.assertEqual(result["_summary"]["candidate_count"], 2)
        self.assertEqual(result["data"]["candidates"][0]["resource_id"], "a:2")

    def test_validate_review_requires_every_candidate(self) -> None:
        selector_input = prepare.prepare(self.session)
        review = {
            "_meta": {"schema_version": "selector-review/v1", "session_id": "s1"},
            "data": {
                "candidates": [{"resource_id": "a:2", "relevance": "high", "quality_score": 80, "resource_role": "核心课程", "reasons": ["匹配"], "notes": []}],
                "excluded": [{"resource_id": "b:1", "reason": "学段不匹配"}],
            },
        }
        self.assertEqual(validate.validate(selector_input, review), [])

    def test_finalize_only_uses_reviewed_candidates(self) -> None:
        review = {
            "data": {"candidates": [
                {"resource_id": "a:2", "quality_score": 80, "resource_role": "核心课程", "notes": ["版本未知"]},
                {"resource_id": "c:1", "quality_score": 70, "resource_role": "练习", "notes": []},
            ]}
        }
        selected = finalize.selected_from_review(review, [2], [], False)
        self.assertEqual(selected, [{"resource_id": "c:1", "quality_score": 70}])
        with self.assertRaises(ValueError):
            finalize.selected_from_review(review, [], ["unknown"], False)

    def test_render_uses_review_order_as_display_numbers(self) -> None:
        selector_input = prepare.prepare(self.session)
        prepare.atomic_write(self.session / "selector_input.json", selector_input)
        review = {
            "_meta": {"schema_version": "selector-review/v1", "session_id": "s1"},
            "data": {
                "candidates": [{"resource_id": "a:2", "relevance": "high", "quality_score": 80, "resource_role": "核心课程", "reasons": ["匹配"], "notes": []}],
                "excluded": [{"resource_id": "b:1", "reason": "学段不匹配"}],
            },
        }
        (self.session / "selector_review.json").write_text(json.dumps(review), encoding="utf-8")
        text = render.render(self.session, 0, 10)
        self.assertIn("1. [A级 · 80分] 四年级数学课程", text)
        lines = text.splitlines()
        title_index = lines.index("1. [A级 · 80分] 四年级数学课程")
        self.assertEqual(lines[title_index + 1], "   链接：https://example.test/a")
        self.assertIn("   用途：核心课程", lines)

    def test_review_order_can_diversify_instead_of_sorting_by_score(self) -> None:
        selector_input = prepare.prepare(self.session)
        review = {
            "_meta": {"schema_version": "selector-review/v1", "session_id": "s1"},
            "data": {
                "candidates": [
                    {"resource_id": "a:2", "relevance": "high", "quality_score": 75, "resource_role": "可复用材料", "reasons": ["可直接使用"], "notes": []},
                    {"resource_id": "b:1", "relevance": "medium", "quality_score": 85, "resource_role": "补充说明", "reasons": ["提供不同用途"], "notes": []},
                ],
                "excluded": [],
            },
        }
        self.assertEqual(validate.validate(selector_input, review), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
