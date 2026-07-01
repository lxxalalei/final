#!/usr/bin/env python3
"""Validate intent-brief/v1 output."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


STATUSES = {"ready", "needs_clarification"}
STRENGTHS = {"must", "prefer", "exclude"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("根节点必须是 object")
    return value


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(document) != {"_meta", "_summary", "data"}:
        errors.append("根节点只能包含 _meta、_summary 和 data")

    meta = document.get("_meta")
    summary = document.get("_summary")
    data = document.get("data")
    if not isinstance(meta, dict):
        return ["缺少 object: _meta"]
    if not isinstance(summary, dict):
        return ["缺少 object: _summary"]
    if not isinstance(data, dict):
        return ["缺少 object: data"]

    if set(meta) != {"schema_version", "session_id", "created_at"}:
        errors.append("_meta 只能包含 schema_version、session_id、created_at")
    if meta.get("schema_version") != "intent-brief/v1":
        errors.append("_meta.schema_version 必须为 intent-brief/v1")
    for key in ("session_id", "created_at"):
        if not _nonempty_string(meta.get(key)):
            errors.append(f"_meta.{key} 必须是非空字符串")

    allowed_data = {
        "status", "raw_request", "clarified_need", "evidence",
        "requirements", "assumptions", "clarification",
    }
    extra = set(data) - allowed_data
    if extra:
        errors.append(f"data 存在未定义字段: {sorted(extra)}")

    status = data.get("status")
    if status not in STATUSES:
        errors.append("data.status 必须为 ready 或 needs_clarification")
    for key in ("raw_request", "clarified_need"):
        if not _nonempty_string(data.get(key)):
            errors.append(f"data.{key} 必须是非空字符串")

    evidence = data.get("evidence")
    if not isinstance(evidence, list):
        errors.append("data.evidence 必须是 array")
    else:
        if status == "ready" and not evidence:
            errors.append("ready 状态必须至少提供一条 evidence")
        for index, item in enumerate(evidence):
            if not isinstance(item, dict) or set(item) != {"statement", "quote"}:
                errors.append(f"data.evidence[{index}] 必须仅含 statement、quote")
                continue
            for key in ("statement", "quote"):
                if not _nonempty_string(item.get(key)):
                    errors.append(f"data.evidence[{index}].{key} 必须是非空字符串")

    requirements = data.get("requirements")
    if not isinstance(requirements, list):
        errors.append("data.requirements 必须是 array")
    else:
        for index, item in enumerate(requirements):
            if not isinstance(item, dict) or set(item) != {"text", "strength", "evidence"}:
                errors.append(f"data.requirements[{index}] 必须仅含 text、strength、evidence")
                continue
            if not _nonempty_string(item.get("text")):
                errors.append(f"data.requirements[{index}].text 必须是非空字符串")
            if item.get("strength") not in STRENGTHS:
                errors.append(f"data.requirements[{index}].strength 非法")
            if not _nonempty_string(item.get("evidence")):
                errors.append(f"data.requirements[{index}].evidence 必须是非空字符串")

    assumptions = data.get("assumptions")
    if assumptions is not None and (
        not isinstance(assumptions, list)
        or not assumptions
        or any(not _nonempty_string(item) for item in assumptions)
    ):
        errors.append("data.assumptions 必须是非空字符串数组")

    clarification = data.get("clarification")
    if status == "needs_clarification":
        if not isinstance(clarification, dict) or set(clarification) != {"question", "reason"}:
            errors.append("needs_clarification 必须提供仅含 question、reason 的 clarification")
        else:
            for key in ("question", "reason"):
                if not _nonempty_string(clarification.get(key)):
                    errors.append(f"clarification.{key} 必须是非空字符串")
    elif clarification is not None:
        errors.append("ready 状态不得输出 clarification")

    if summary.get("status") != status:
        errors.append("_summary.status 必须与 data.status 一致")
    if status == "ready":
        if set(summary) != {"status"}:
            errors.append("ready 状态的 _summary 只能包含 status")
    elif status == "needs_clarification":
        question = clarification.get("question") if isinstance(clarification, dict) else None
        if set(summary) != {"status", "question"} or summary.get("question") != question:
            errors.append("needs_clarification 的 _summary.question 必须与 clarification.question 一致")

    for forbidden in ("slots", "constraints", "search_concepts", "queries", "search_tasks"):
        if forbidden in data:
            errors.append(f"Intent brief 不得输出旧槽位或搜索执行字段: data.{forbidden}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 intent-brief/v1 输出")
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        errors = validate(load_json(args.file))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors = [str(exc)]
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
