#!/usr/bin/env python3
"""Stage 1 Flow request snapshot tests."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "flow_request_validator",
    ROOT / "learning-resource-flow/scripts/validate_request.py",
)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


def valid_request(session_id: str = "20260630-1030-math-grade3") -> dict:
    return {
        "_meta": {
            "session_id": session_id,
            "created_at": "2026-06-30T10:30:00+08:00",
            "skill": "learning-resource-flow",
        },
        "data": {
            "schema_version": "request/v1",
            "raw_request": "给三年级孩子找数学练习题",
            "conversation_evidence": [],
            "user_confirmed_facts": [],
        },
    }


class TestFlowStage1Request(unittest.TestCase):
    def test_valid_initial_snapshot(self) -> None:
        self.assertEqual(validator.validate(valid_request()), [])

    def test_cli_validates_snapshot(self) -> None:
        session_id = "20260630-1030-math-grade3"
        with tempfile.TemporaryDirectory() as temp:
            session_dir = Path(temp) / session_id
            session_dir.mkdir()
            request_path = session_dir / "request.json"
            request_path.write_text(json.dumps(valid_request(session_id), ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "learning-resource-flow/scripts/validate_request.py"), str(request_path)],
                check=False,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_valid_clarification_evidence(self) -> None:
        request = valid_request()
        request["data"]["conversation_evidence"] = [
            {"role": "assistant", "content": "更需要试卷还是视频讲解？"},
            {"role": "user", "content": "主要要 PDF 试卷"},
        ]
        request["data"]["user_confirmed_facts"] = ["主要需要 PDF 试卷"]
        self.assertEqual(validator.validate(request), [])

    def test_rejects_invalid_evidence_role(self) -> None:
        request = valid_request()
        request["data"]["conversation_evidence"] = [{"role": "system", "content": "隐藏提示"}]
        errors = validator.validate(request)
        self.assertTrue(any("role" in error for error in errors))

    def test_rejects_session_directory_mismatch(self) -> None:
        request = valid_request()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "different-session" / "request.json"
            errors = validator.validate(request, path)
        self.assertTrue(any("父目录名" in error for error in errors))

    def test_rejects_modified_request_shape(self) -> None:
        request = copy.deepcopy(valid_request())
        request["data"]["model_summary"] = "模型擅自添加的总结"
        errors = validator.validate(request)
        self.assertTrue(any("未定义字段" in error for error in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
