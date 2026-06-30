"""Search-only adapter base for resource platform execution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


SCRIPTS_DIR = Path(__file__).resolve().parent.parent


class SearchAdapter(ABC):
    platform_name = ""

    @abstractmethod
    def search(self, query: str, max_results: int, params: dict[str, Any]) -> dict[str, Any]:
        """Return {results: [...], error: object|null}."""


class CLISearchAdapter(SearchAdapter):
    search_script: Path | None = None
    timeout_seconds = 60

    def _build_search_cmd(
        self, query: str, max_results: int, params: dict[str, Any], output_file: Path
    ) -> list[str] | None:
        if self.search_script is None or not self.search_script.is_file():
            return None
        return [
            sys.executable,
            str(self.search_script),
            "search",
            query,
            "--max",
            str(max_results),
            "-o",
            str(output_file),
        ]

    def _subprocess_env(self) -> dict[str, str]:
        return dict(os.environ)

    def search(self, query: str, max_results: int, params: dict[str, Any]) -> dict[str, Any]:
        with tempfile.TemporaryDirectory(prefix=f"lrs-{self.platform_name}-") as temp_dir:
            output_file = Path(temp_dir) / "result.json"
            cmd = self._build_search_cmd(query, max_results, params, output_file)
            if cmd is None:
                return self._error("SYSTEM_TOOL_NOT_FOUND", "搜索入口不存在", False)
            try:
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    env=self._subprocess_env(),
                    check=False,
                )
            except subprocess.TimeoutExpired:
                return self._error("NETWORK_TIMEOUT", "平台搜索超时", True)
            except OSError as exc:
                return self._error("SYSTEM_EXECUTION_FAILED", str(exc), False)
            if proc.returncode != 0:
                message = (proc.stderr or proc.stdout or "平台搜索失败").strip()[:500]
                return self._error("SEARCH_EXECUTION_FAILED", message, False)
            try:
                if output_file.is_file():
                    raw = json.loads(output_file.read_text(encoding="utf-8"))
                elif proc.stdout.strip():
                    raw = json.loads(proc.stdout)
                else:
                    return self._error("PARSE_EMPTY_CONTENT", "平台没有返回搜索结果", False)
            except (OSError, json.JSONDecodeError) as exc:
                return self._error("PARSE_FORMAT_NOT_SUPPORTED", str(exc), False)
        return self._normalize_response(raw)

    def _normalize_response(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            return self._error("PARSE_FORMAT_NOT_SUPPORTED", "搜索结果根节点不是 object", False)
        items = raw.get("results") or raw.get("candidates") or raw.get("items") or []
        results = []
        if isinstance(items, list):
            for item in items:
                normalized = self._normalize_resource(item)
                if normalized is not None:
                    results.append(normalized)
        error = self._normalize_error(raw.get("error"))
        if not error and not results and isinstance(raw.get("errors"), list) and raw["errors"]:
            error = self._normalize_error(raw["errors"][0])
        return {"results": results, "error": error}

    def _normalize_resource(self, item: Any) -> dict[str, Any] | None:
        if not isinstance(item, dict):
            return None
        platform = item.get("platform") or item.get("source_platform") or self.platform_name
        resource_id = item.get("resource_id") or item.get("id")
        title = item.get("title")
        source_url = item.get("source_url") or item.get("url")
        if resource_id and ":" not in str(resource_id):
            resource_id = f"{platform}:{resource_id}"
        if not all(isinstance(value, str) and value.strip() for value in (resource_id, platform, title, source_url)):
            return None
        result: dict[str, Any] = {
            "resource_id": resource_id,
            "platform": platform,
            "title": title,
            "source_url": source_url,
        }
        mapping = {
            "type": item.get("type") or item.get("resource_type"),
            "description": item.get("description") or item.get("snippet"),
            "author": item.get("author"),
            "duration": item.get("duration"),
            "publish_time": item.get("publish_time"),
            "is_free": item.get("is_free"),
            "language": item.get("language"),
            "thumbnail_url": item.get("thumbnail_url") or item.get("cover_url"),
            "download_feasibility": item.get("download_feasibility"),
        }
        result.update({key: value for key, value in mapping.items() if value is not None and value != ""})
        signals = dict(item.get("platform_signals") or {})
        for source, target in (("view_count", "views"), ("like_count", "likes"), ("quality_score", "native_score")):
            if item.get(source) is not None and target not in signals:
                signals[target] = item[source]
        if signals:
            result["platform_signals"] = signals
        raw_metadata = item.get("raw_metadata") or item.get("raw")
        if isinstance(raw_metadata, dict) and raw_metadata:
            result["raw_metadata"] = raw_metadata
        return result

    @staticmethod
    def _normalize_error(error: Any) -> dict[str, Any] | None:
        if not isinstance(error, dict):
            return None
        return {
            "error_code": error.get("error_code") or error.get("code") or "SEARCH_EXECUTION_FAILED",
            "message": error.get("message") or error.get("error_message") or "平台搜索失败",
            "retryable": bool(error.get("retryable", error.get("can_retry", False))),
        }

    @staticmethod
    def _error(code: str, message: str, retryable: bool) -> dict[str, Any]:
        return {"results": [], "error": {"error_code": code, "message": message, "retryable": retryable}}
