"""shared.platform_base — 平台 Skill 基类。

定义 PlatformSkill 接口和 CLIBasedPlatformSkill 默认实现。
调度器（resource-search / resource-downloader）通过此接口无差别调用各平台。

增强功能（v2，2026-06-25）：
  - RateLimiter：请求间隔控制，防触发平台反爬
  - CircuitBreaker：断路器模式，连续失败自动暂停
  - CredentialManager：凭证安全传递（环境变量/配置文件），脱敏日志

配置集成（v3，2026-06-25）：
  - 自动从 config/settings.yaml 读取平台参数（间隔/超时/断路器阈值等）
  - 支持环境变量覆盖（LRS_PLATFORMS__<NAME>__<PARAM>）
  - 显式构造参数始终优先于配置文件（向后兼容）

所有增强默认开启但可通过参数关闭/调整，完全向后兼容。
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ═══════════════════════════════════════════════════════════════
#  模块级 logger（基类内部用，不依赖 shared.logger 避免循环）
# ═══════════════════════════════════════════════════════════════

_log = logging.getLogger("platform_base")
if not _log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"))
    _log.addHandler(_h)
    _log.setLevel(logging.INFO)


def _platforms_base_dir() -> Path:
    """返回 scripts/ 目录的绝对路径（各平台脚本子目录的父目录）。

    目录结构：resource-platforms/scripts/shared/platform_base.py
    所以此文件的 parent.parent = resource-platforms/scripts/
    其下直接是 bilibili/ smartedu/ zhihu/ 等平台子目录。
    """
    return Path(__file__).resolve().parent.parent


# ═══════════════════════════════════════════════════════════════
#  速率限制器
# ═══════════════════════════════════════════════════════════════

class RateLimiter:
    """简单的请求间隔控制器（线程安全）。

    确保任意两次 acquire() 调用之间至少间隔 ``min_interval`` 秒，
    用于防止触发平台反爬（频率限制）。

    用法::

        limiter = RateLimiter(min_interval=1.5)
        limiter.acquire()   # 第一次立即返回
        limiter.acquire()   # 第二次阻塞至距第一次 >= 1.5s
    """

    def __init__(self, min_interval: float = 1.0) -> None:
        self.min_interval = max(0.0, float(min_interval))
        self._last_call: float = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> float:
        """阻塞直到满足最小间隔要求，返回实际等待秒数。"""
        if self.min_interval <= 0:
            return 0.0
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            wait = self.min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
                self._last_call = time.monotonic()
                return wait
            self._last_call = now
            return 0.0

    def reset(self) -> None:
        """重置计时器（下次 acquire 立即返回）。"""
        with self._lock:
            self._last_call = 0.0


# ═══════════════════════════════════════════════════════════════
#  断路器
# ═══════════════════════════════════════════════════════════════

class CircuitBreakerOpenError(Exception):
    """断路器处于 OPEN 状态时抛出，表示该平台当前被熔断保护。"""


class CircuitBreaker:
    """简单的断路器实现（线程安全）。

    三态状态机：
      - CLOSED（正常）：请求正常通过，记录失败次数
      - OPEN（熔断）：连续失败达到阈值后进入，所有请求被拒绝
      - HALF_OPEN（半开）：冷却时间过后进入，放行一次试探请求

    状态转换::

        CLOSED --(连续 failure_threshold 次失败)--> OPEN
        OPEN   --(冷却 recovery_timeout 秒)-------> HALF_OPEN
        HALF_OPEN --(成功)--> CLOSED
        HALF_OPEN --(失败)--> OPEN（重置冷却计时）
    """

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 300.0,
    ) -> None:
        self.failure_threshold = max(1, int(failure_threshold))
        self.recovery_timeout = max(1.0, float(recovery_timeout))
        self._state = self.CLOSED
        self._failure_count = 0
        self._opened_at: float = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        """当前状态（会自动检查是否该从 OPEN 转 HALF_OPEN）。"""
        with self._lock:
            self._maybe_transition_to_half_open()
            return self._state

    def before_call(self) -> None:
        """请求前调用。若断路器开启则抛 CircuitBreakerOpenError。"""
        with self._lock:
            self._maybe_transition_to_half_open()
            if self._state == self.OPEN:
                raise CircuitBreakerOpenError(
                    f"断路器开启中（连续失败 {self._failure_count} 次），"
                    f"平台请求被暂停"
                )
            # CLOSED 或 HALF_OPEN 都放行

    def on_success(self) -> None:
        """请求成功后调用，重置失败计数。"""
        with self._lock:
            self._failure_count = 0
            if self._state in (self.HALF_OPEN, self.OPEN):
                self._state = self.CLOSED
                _log.info("断路器恢复为 CLOSED（请求成功）")

    def on_failure(self) -> None:
        """请求失败后调用，递增失败计数，可能触发熔断。"""
        with self._lock:
            self._failure_count += 1
            if self._state == self.HALF_OPEN:
                # 半开状态下失败，立即重新熔断
                self._trip()
                return
            if self._failure_count >= self.failure_threshold:
                self._trip()

    def reset(self) -> None:
        """手动重置断路器到 CLOSED。"""
        with self._lock:
            self._state = self.CLOSED
            self._failure_count = 0
            self._opened_at = 0.0

    def _trip(self) -> None:
        """触发熔断（调用方需持有锁）。"""
        self._state = self.OPEN
        self._opened_at = time.monotonic()
        _log.warning(
            "断路器触发熔断 OPEN：连续失败 %d/%d 次，暂停 %gs",
            self._failure_count, self.failure_threshold, self.recovery_timeout,
        )

    def _maybe_transition_to_half_open(self) -> None:
        """若冷却期已过，从 OPEN 转 HALF_OPEN（调用方需持有锁）。"""
        if self._state == self.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.recovery_timeout:
                self._state = self.HALF_OPEN
                _log.info("断路器冷却完成，转为 HALF_OPEN（放行一次试探请求）")


# ═══════════════════════════════════════════════════════════════
#  凭证安全管理
# ═══════════════════════════════════════════════════════════════

# 凭证键名到环境变量后缀的映射（value 为环境变量后缀，None 表示不查环境变量）
_CRED_ENV_SUFFIXES = {
    "cookie": "COOKIE",
    "cookies": "COOKIE",
    "cookie_path": "COOKIE_PATH",
    "token": "TOKEN",
    "access_token": "ACCESS_TOKEN",
    "sessdata": "SESSDATA",
    "csrf": "CSRF",
    "api_key": "API_KEY",
    "appkey": "APPKEY",
    "secret": "SECRET",
    "secretkey": "SECRETKEY",
    "username": "USERNAME",
    "password": "PASSWORD",
    "uid": "UID",
}

# 需要脱敏的凭证字段名（模糊匹配）
_SENSITIVE_PATTERNS = re.compile(
    r"(cookie|token|sessdata|csrf|api[_-]?key|appkey|secret|password|passwd)",
    re.IGNORECASE,
)


def _mask_value(val: Any, visible: int = 4) -> str:
    """将敏感值脱敏为 ``****xxxx`` 形式。"""
    s = str(val)
    if len(s) <= visible:
        return "*" * len(s)
    return "*" * (len(s) - visible) + s[-visible:]


def _sanitize_for_log(data: Any, _depth: int = 0) -> Any:
    """递归将 dict/list 中的敏感字段值脱敏，用于安全日志输出。"""
    if _depth > 6:
        return "<...>"
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if _SENSITIVE_PATTERNS.search(str(k)):
                result[k] = _mask_value(v) if v else v
            else:
                result[k] = _sanitize_for_log(v, _depth + 1)
        return result
    if isinstance(data, list):
        return [_sanitize_for_log(item, _depth + 1) for item in data]
    if isinstance(data, str) and _SENSITIVE_PATTERNS.search(data) and len(data) > 20:
        # 字符串本身像凭证（如 Cookie 头）—— 脱敏
        return _mask_value(data)
    return data


class CredentialManager:
    """凭证安全管理器。

    按优先级解析凭证（高 → 低）：
      1. 显式传入的 ``credentials`` 字典
      2. intent / candidate 中携带的凭证字段（如 intent["cookie"]）
      3. 环境变量 ``{PLATFORM}_{KEY}``（如 BILIBILI_COOKIE）
      4. 配置文件 ``platforms/{platform}/config/credentials.json``

    所有凭证绝不硬编码在脚本中。日志输出自动脱敏。
    """

    def __init__(
        self,
        platform_name: str,
        credentials: dict[str, Any] | None = None,
        config_dir: Path | None = None,
    ) -> None:
        self.platform_name = platform_name.upper()
        self._explicit = dict(credentials) if credentials else {}
        self._config_dir = config_dir
        self._file_cache: dict[str, Any] | None = None

    def get(self, key: str, fallback: Any = None) -> Any:
        """获取凭证值。查找顺序：显式 → intent/candidate → 环境变量 → 配置文件。"""
        # 1. 显式传入
        if key in self._explicit:
            return self._explicit[key]

        # 2. 环境变量 {PLATFORM}_{KEY}
        suffix = _CRED_ENV_SUFFIXES.get(key.lower(), key.upper())
        env_name = f"{self.platform_name}_{suffix}"
        env_val = os.environ.get(env_name)
        if env_val:
            return env_val

        # 3. 配置文件
        file_creds = self._load_config_file()
        if file_creds and key in file_creds:
            return file_creds[key]

        return fallback

    def get_all(self) -> dict[str, Any]:
        """合并所有来源的凭证（用于整体传递给子进程）。"""
        merged: dict[str, Any] = {}
        # 配置文件（最低优先级）
        file_creds = self._load_config_file()
        if file_creds:
            merged.update(file_creds)
        # 环境变量
        for key, suffix in _CRED_ENV_SUFFIXES.items():
            env_name = f"{self.platform_name}_{suffix}"
            env_val = os.environ.get(env_name)
            if env_val and key not in merged:
                merged[key] = env_val
        # 显式（最高优先级）
        merged.update(self._explicit)
        return merged

    def to_env_dict(self) -> dict[str, str]:
        """将凭证转为环境变量字典，用于注入子进程 env。

        键名统一为 ``{PLATFORM}_{KEY}``，确保子进程可按约定读取。
        """
        env: dict[str, str] = {}
        for key, val in self.get_all().items():
            if val is None:
                continue
            suffix = _CRED_ENV_SUFFIXES.get(key.lower(), key.upper())
            env_name = f"{self.platform_name}_{suffix}"
            env[env_name] = str(val)
        return env

    def safe_log(self, label: str = "凭证") -> str:
        """返回脱敏后的凭证摘要，可安全输出到日志。"""
        sanitized = _sanitize_for_log(self.get_all())
        return f"{label} [{self.platform_name}]: {sanitized}"

    def _load_config_file(self) -> dict[str, Any] | None:
        """懒加载配置文件 credentials.json。"""
        if self._file_cache is not None:
            return self._file_cache
        self._file_cache = {}
        base = self._config_dir or _platforms_base_dir()
        cred_file = base / self.platform_name.lower() / "config" / "credentials.json"
        if cred_file.exists():
            try:
                raw = json.loads(cred_file.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    self._file_cache = raw
                    _log.debug("已加载配置文件 %s", cred_file)
            except (json.JSONDecodeError, OSError) as exc:
                _log.warning("凭证配置文件解析失败 %s: %s", cred_file, exc)
        return self._file_cache


# ═══════════════════════════════════════════════════════════════
#  配置加载（延迟导入避免循环依赖）
# ═══════════════════════════════════════════════════════════════

# 平台默认配置（配置文件缺失时使用）
_PLATFORM_DEFAULTS: dict[str, Any] = {
    "min_request_interval": 1.0,
    "failure_threshold": 5,
    "recovery_timeout": 300.0,
    "enable_rate_limit": True,
    "enable_circuit_breaker": True,
    "request_timeout": 120,
    "download_timeout": 600,
    "retry_count": 2,
}


def _load_platform_config(platform_name: str) -> dict[str, Any]:
    """从配置文件加载平台参数，回退到代码默认值。

    安全性：ConfigLoader 加载失败或文件不存在时静默回退到默认值，
    不影响平台 Skill 正常工作。
    """
    try:
        from shared.config_loader import get_config

        cfg = get_config()
        params = cfg.get_platform_params_dict(platform_name)
        # 确保所有必需键都存在（回退到代码默认值）
        result = dict(_PLATFORM_DEFAULTS)
        result.update(params)
        return result
    except Exception as exc:
        _log.debug(
            "配置加载失败，使用代码默认值 [%s]: %s",
            platform_name, exc,
        )
        return dict(_PLATFORM_DEFAULTS)


# ═══════════════════════════════════════════════════════════════
#  PlatformSkill 抽象接口（不变）
# ═══════════════════════════════════════════════════════════════

class PlatformSkill:
    """平台 Skill 抽象基类。

    每个平台 Skill 必须实现 search() 和 download() 两个方法。
    """

    platform_name: str = ""

    def search(self, intent: dict[str, Any]) -> dict[str, Any]:
        """搜索模式：接收查询 intent，返回标准候选列表。

        Args:
            intent: 包含 keywords, max_results, age_range 等的查询参数

        Returns:
            符合 platform-search-contract.md 的搜索结果
        """
        raise NotImplementedError

    def download(self, candidate: dict[str, Any], download_dir: str) -> dict[str, Any]:
        """下载模式：接收候选资源，返回下载结果。

        Args:
            candidate: 符合元数据规范的资源对象
            download_dir: 下载保存目录

        Returns:
            符合 platform-download-contract.md 的下载结果
        """
        raise NotImplementedError


# ═══════════════════════════════════════════════════════════════
#  CLIBasedPlatformSkill（增强版）
# ═══════════════════════════════════════════════════════════════

class CLIBasedPlatformSkill(PlatformSkill):
    """基于命令行脚本的平台 Skill 默认实现。

    大多数平台只需提供 CLI 脚本（search/download 子命令），
    本基类自动发现脚本并构建调用命令。

    子类可覆盖以下方法适配平台差异：
    - _build_search_cmd(): 构建搜索命令
    - _build_download_cmd(): 构建下载命令
    - _transform_download_url(): 转换下载 URL（如提取 BV 号）

    增强功能（v2）：
    - 速率限制（min_request_interval）
    - 断路器（failure_threshold / recovery_timeout）
    - 凭证安全传递（credentials 参数）

    配置集成（v3）：
    - 自动从 config/settings.yaml 读取平台参数
    - 显式参数 > 环境变量 > 配置文件 > 代码默认值

    **向后兼容**：所有新参数都有默认值，现有子类无需修改 ``__init__`` 签名即可获得新功能。
    若子类已覆盖 ``__init__``，只需确保调用 ``super().__init__()`` 即可。
    """

    def __init__(
        self,
        *,
        min_request_interval: float | None = None,
        failure_threshold: int | None = None,
        recovery_timeout: float | None = None,
        credentials: dict[str, Any] | None = None,
        enable_rate_limit: bool | None = None,
        enable_circuit_breaker: bool | None = None,
    ) -> None:
        """初始化平台 Skill。

        参数解析优先级（高 → 低）：
          1. 显式传入的非 None 参数
          2. config/settings.yaml 中的平台配置（含 defaults 回退）
          3. 环境变量覆盖（由 ConfigLoader 自动处理）
          4. 代码默认值

        Args:
            min_request_interval: 最小请求间隔（秒）。None 则读配置，最终默认 1.0。
            failure_threshold: 断路器连续失败熔断阈值。None 则读配置，最终默认 5。
            recovery_timeout: 断路器冷却时间（秒）。None 则读配置，最终默认 300。
            credentials: 显式凭证字典，优先级高于环境变量和配置文件。
            enable_rate_limit: 是否启用速率限制。None 则读配置，最终默认 True。
            enable_circuit_breaker: 是否启用断路器。None 则读配置，最终默认 True。
        """
        # ── 从配置文件读取平台参数（合并 defaults + 平台专属） ──
        platform_cfg = _load_platform_config(self.platform_name)

        # 合并：显式参数 > 配置文件 > 代码默认值
        _min_interval = min_request_interval if min_request_interval is not None else platform_cfg["min_request_interval"]
        _fail_threshold = failure_threshold if failure_threshold is not None else platform_cfg["failure_threshold"]
        _recovery = recovery_timeout if recovery_timeout is not None else platform_cfg["recovery_timeout"]
        _enable_rl = enable_rate_limit if enable_rate_limit is not None else platform_cfg["enable_rate_limit"]
        _enable_cb = enable_circuit_breaker if enable_circuit_breaker is not None else platform_cfg["enable_circuit_breaker"]

        # 保存超时/重试参数供子类使用
        self._request_timeout: int = platform_cfg["request_timeout"]
        self._download_timeout: int = platform_cfg["download_timeout"]
        self._retry_count: int = platform_cfg["retry_count"]

        base = _platforms_base_dir()
        self._search_script: Path | None = self._discover_script("*_search.py")
        self._download_script: Path | None = self._discover_script("*_dl.py")
        self._fallback_search_script: Path | None = None

        # 速率限制器
        self._rate_limiter: RateLimiter | None = (
            RateLimiter(min_interval=_min_interval)
            if _enable_rl else None
        )

        # 断路器
        self._circuit_breaker: CircuitBreaker | None = (
            CircuitBreaker(
                failure_threshold=_fail_threshold,
                recovery_timeout=_recovery,
            )
            if _enable_cb else None
        )

        # 凭证管理器
        self._credential_manager = CredentialManager(
            platform_name=self.platform_name,
            credentials=credentials,
        )

    def _discover_script(self, pattern: str) -> Path | None:
        """按命名约定发现脚本。

        目录结构：resource-platforms/scripts/<platform_name>/<script>.py
        _platforms_base_dir() 返回 resource-platforms/scripts/
        所以直接在其下的 platform_name/ 目录中搜索。
        """
        scripts_dir = _platforms_base_dir() / self.platform_name
        matches = list(scripts_dir.glob(pattern))
        return matches[0] if matches else None

    def _build_search_cmd(
        self, intent: dict[str, Any], output_file: Path
    ) -> list[str] | None:
        """构建搜索命令。默认约定：{script} search {keyword} --max {n} -o {file}"""
        script = self._search_script
        if script is None or not script.exists():
            return None
        keywords = intent.get("keywords") or intent.get("query") or ""
        if not keywords:
            return None
        max_results = intent.get("max_results") or 20
        return [
            sys.executable, str(script),
            "search", keywords,
            "--max", str(max_results),
            "-o", str(output_file),
        ]

    def _build_download_cmd(
        self, candidate: dict[str, Any], download_dir: str
    ) -> list[str] | None:
        """构建下载命令。默认约定：{script} download {url} -o {dir}"""
        script = self._download_script
        if script is None or not script.exists():
            return None
        url = candidate.get("source_url") or candidate.get("url") or ""
        if not url:
            return None
        url = self._transform_download_url(url)
        return [
            sys.executable, str(script),
            "download", url,
            "-o", download_dir,
        ]

    def _transform_download_url(self, url: str) -> str:
        """转换下载 URL。默认原样返回，子类可覆盖。"""
        return url

    # ─── 凭证辅助 ──────────────────────────────────────────

    def _resolve_credentials(self, context: dict[str, Any]) -> dict[str, Any]:
        """合并 intent/candidate 中的凭证与 CredentialManager 的凭证。

        intent/candidate 中的凭证优先级最高（运行时动态），其次是 __init__ 配置。
        """
        # 从 context 提取可能的凭证字段
        context_creds: dict[str, Any] = {}
        for key in list(_CRED_ENV_SUFFIXES.keys()):
            if key in context and context[key]:
                context_creds[key] = context[key]
        # CredentialManager 的凭证作为基础
        merged = self._credential_manager.get_all()
        # context 凭证覆盖（最高优先级）
        merged.update(context_creds)
        return merged

    def _build_subprocess_env(
        self, extra_creds: dict[str, Any] | None = None
    ) -> dict[str, str]:
        """构建子进程环境变量：继承父进程 env + 注入凭证环境变量。"""
        env = dict(os.environ)  # 继承父进程
        # CredentialManager 凭证
        cred_env = self._credential_manager.to_env_dict()
        env.update(cred_env)
        # 运行时凭证（intent/candidate 中携带的）覆盖
        if extra_creds:
            platform_upper = self.platform_name.upper()
            for key, val in extra_creds.items():
                if val is None:
                    continue
                suffix = _CRED_ENV_SUFFIXES.get(key.lower(), key.upper())
                env[f"{platform_upper}_{suffix}"] = str(val)
        return env

    # ─── 公开接口 ──────────────────────────────────────────

    def search(self, intent: dict[str, Any]) -> dict[str, Any]:
        """执行搜索：构建命令 → 运行 → 解析输出 JSON。

        集成速率限制、断路器、凭证安全传递。
        """
        # 断路器检查
        if self._circuit_breaker is not None:
            try:
                self._circuit_breaker.before_call()
            except CircuitBreakerOpenError as exc:
                _log.warning("[%s] 搜索被断路器拦截: %s", self.platform_name, exc)
                return self._empty_result(
                    intent, "ANTI_CRAWL_BLOCKED", f"平台熔断保护中：{exc}"
                )

        # 速率限制
        if self._rate_limiter is not None:
            self._rate_limiter.acquire()

        # 先确定输出文件路径，再交给 _build_search_cmd 构建 -o 参数，
        # 不再依赖 cmd[-1] 取路径（更健壮，不假设参数顺序）。
        output_file = Path(tempfile.gettempdir()) / f"{self.platform_name}_search.json"
        cmd = self._build_search_cmd(intent, output_file)
        if cmd is None:
            return self._empty_result(intent, "SYSTEM_TOOL_NOT_FOUND", "搜索脚本不存在")

        # 解析运行时凭证并注入子进程
        runtime_creds = self._resolve_credentials(intent)
        if runtime_creds:
            _log.debug(
                "[%s] 搜索凭证: %s",
                self.platform_name,
                _sanitize_for_log(runtime_creds),
            )
        sub_env = self._build_subprocess_env(runtime_creds)

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._request_timeout, env=sub_env
            )
        except subprocess.TimeoutExpired:
            self._record_failure("搜索超时")
            return self._empty_result(intent, "NETWORK_TIMEOUT", "搜索超时")
        except FileNotFoundError:
            self._record_failure("Python 或脚本不存在")
            return self._empty_result(intent, "SYSTEM_TOOL_NOT_FOUND", "Python 或脚本不存在")

        if proc.returncode != 0:
            err = proc.stderr.strip()[:500] if proc.stderr else "未知错误"
            self._record_failure(f"返回码 {proc.returncode}: {err}")
            return self._empty_result(intent, "SYSTEM_UNKNOWN_ERROR", err)

        # 成功
        self._record_success()

        if output_file.exists():
            try:
                raw = json.loads(output_file.read_text(encoding="utf-8"))
                return self._normalize_search_result(raw, intent)
            except json.JSONDecodeError:
                return self._empty_result(intent, "PARSE_FORMAT_NOT_SUPPORTED", "输出 JSON 解析失败")

        # 某些脚本直接输出到 stdout
        if proc.stdout.strip():
            try:
                raw = json.loads(proc.stdout)
                return self._normalize_search_result(raw, intent)
            except json.JSONDecodeError:
                pass

        return self._empty_result(intent, "PARSE_EMPTY_CONTENT", "无输出")

    def download(self, candidate: dict[str, Any], download_dir: str) -> dict[str, Any]:
        """执行下载：构建命令 → 运行 → 返回结果。

        集成速率限制、断路器、凭证安全传递。
        """
        # 断路器检查
        if self._circuit_breaker is not None:
            try:
                self._circuit_breaker.before_call()
            except CircuitBreakerOpenError as exc:
                _log.warning("[%s] 下载被断路器拦截: %s", self.platform_name, exc)
                return self._download_error(
                    candidate, "ANTI_CRAWL_BLOCKED", f"平台熔断保护中：{exc}"
                )

        # 速率限制
        if self._rate_limiter is not None:
            self._rate_limiter.acquire()

        cmd = self._build_download_cmd(candidate, download_dir)
        if cmd is None:
            return self._download_error(candidate, "SYSTEM_TOOL_NOT_FOUND", "下载脚本不存在")

        # 解析运行时凭证并注入子进程
        runtime_creds = self._resolve_credentials(candidate)
        if runtime_creds:
            _log.debug(
                "[%s] 下载凭证: %s",
                self.platform_name,
                _sanitize_for_log(runtime_creds),
            )
        sub_env = self._build_subprocess_env(runtime_creds)

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._download_timeout, env=sub_env
            )
        except subprocess.TimeoutExpired:
            self._record_failure("下载超时")
            return self._download_error(candidate, "NETWORK_TIMEOUT", "下载超时")
        except FileNotFoundError:
            self._record_failure("Python 或脚本不存在")
            return self._download_error(candidate, "SYSTEM_TOOL_NOT_FOUND", "Python 或脚本不存在")

        if proc.returncode != 0:
            err = proc.stderr.strip()[:500] if proc.stderr else "未知错误"
            self._record_failure(f"返回码 {proc.returncode}: {err}")
            return self._download_error(candidate, "DOWNLOAD_FAILED", err)

        # 成功
        self._record_success()

        return {
            "resource_id": candidate.get("resource_id", ""),
            "platform": self.platform_name,
            "download_status": "success",
            "degraded_level": "Level 0",
            "fetch_method": "cli",
            "fetch_time": _now_iso(),
            "stdout": proc.stdout.strip()[:500] if proc.stdout else "",
        }

    # ─── 断路器/限流器辅助 ────────────────────────────────

    def _record_success(self) -> None:
        """记录一次成功请求，通知断路器。"""
        if self._circuit_breaker is not None:
            self._circuit_breaker.on_success()

    def _record_failure(self, reason: str = "") -> None:
        """记录一次失败请求，通知断路器。"""
        if reason:
            _log.debug("[%s] 请求失败: %s", self.platform_name, reason)
        if self._circuit_breaker is not None:
            self._circuit_breaker.on_failure()

    # ─── 内部辅助 ──────────────────────────────────────────

    def _normalize_search_result(
        self, raw: dict[str, Any], intent: dict[str, Any]
    ) -> dict[str, Any]:
        """将平台脚本原始输出标准化为 platform-search-contract 格式。

        处理两种常见输出格式：
        1. learning-resource-candidate/v1（旧格式，candidates 数组 + source_platform）
        2. 已符合契约的格式（results 数组 + platform）
        """
        # 新旧格式都经过统一归一化，避免平台脚本输出的旧质量字段被误认为
        # selector 的最终评分。
        candidates = raw.get("results") or raw.get("candidates") or raw.get("items") or []
        if not candidates:
            return raw  # 无法识别格式，原样返回

        results = []
        for item in candidates:
            normalized = self._normalize_candidate(item)
            if normalized:
                results.append(normalized)

        normalized_result = dict(raw)
        normalized_result.pop("candidates", None)
        normalized_result.pop("items", None)
        normalized_result.update({
            "platform": raw.get("platform", self.platform_name),
            "query": raw.get("query", intent.get("keywords", "")),
            "total_found": raw.get("total_found", raw.get("total", len(results))),
            "returned_count": len(results),
            "search_method": raw.get("search_method", "api"),
            "results": results,
        })
        return normalized_result

    def _normalize_candidate(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """将单个旧格式候选对象标准化为契约格式。"""
        platform = item.get("source_platform") or item.get("platform") or self.platform_name
        raw_id = item.get("resource_id") or item.get("id") or ""

        # resource_id 格式统一为 平台名:平台内ID
        if ":" not in str(raw_id) and raw_id:
            resource_id = f"{platform}:{raw_id}"
        else:
            resource_id = str(raw_id)

        source_url = item.get("source_url") or item.get("url") or ""
        title = item.get("title") or ""
        if not resource_id or not title or not source_url:
            return None

        # download_feasibility: 中文标准化；未知时保留 None，由 selector 处理。
        feasibility_map = {"high": "高", "medium": "中", "low": "低"}
        feasibility = item.get("download_feasibility") or item.get("downloadable")
        if isinstance(feasibility, bool):
            feasibility = "高" if feasibility else "低"
        elif isinstance(feasibility, str):
            feasibility = feasibility_map.get(feasibility, feasibility)
        else:
            feasibility = None

        # resource_type → type（中文）
        type_val = item.get("resource_type") or item.get("type")

        native_score = item.get("platform_quality_score")
        if native_score is None:
            native_score = item.get("quality_score")
        platform_signals = dict(item.get("platform_signals") or {})
        inferred_signals = {
            "views": item.get("view_count") or _extract_view_count(item),
            "likes": item.get("like_count"),
            "native_score": native_score,
            "native_level": item.get("quality_level"),
            "is_verified": item.get("is_verified"),
        }
        for key, value in inferred_signals.items():
            if value is not None and key not in platform_signals:
                platform_signals[key] = value

        platform_resource_id = str(raw_id)
        if ":" in platform_resource_id:
            platform_resource_id = platform_resource_id.split(":", 1)[1]

        return {
            "resource_id": resource_id,
            "platform_resource_id": platform_resource_id,
            "title": title,
            "type": type_val,
            "subject": item.get("subject"),
            "platform": platform,
            "source_url": source_url,
            "source_name": item.get("source_name") or item.get("provider"),
            "download_feasibility": feasibility,
            "description": item.get("description") or item.get("snippet"),
            "age_range": item.get("age_range"),
            "tags": item.get("tags") or [],
            "duration": item.get("duration"),
            "language": item.get("language"),
            "is_free": item.get("is_free"),
            "author": item.get("author"),
            "publish_time": item.get("publish_time"),
            "thumbnail_url": item.get("thumbnail_url"),
            "platform_signals": platform_signals,
            "raw_metadata": item.get("raw_metadata") or {},
        }

    def _empty_result(self, intent: dict, code: str, msg: str) -> dict:
        return {
            "platform": self.platform_name,
            "query": intent.get("keywords", ""),
            "total_found": 0,
            "returned_count": 0,
            "search_method": "other",
            "results": [],
            "error": {
                "error_code": code,
                "error_message": msg,
                "can_retry": code.startswith("NETWORK_"),
            },
        }

    def _download_error(self, candidate: dict, code: str, msg: str) -> dict:
        return {
            "resource_id": candidate.get("resource_id", ""),
            "platform": self.platform_name,
            "download_status": "failed",
            "fetch_method": "cli",
            "fetch_time": _now_iso(),
            "error": {
                "error_code": code,
                "error_message": msg,
                "can_retry": code.startswith("NETWORK_") or code == "DOWNLOAD_FAILED",
            },
        }


# ═══════════════════════════════════════════════════════════════
#  模块级辅助函数
# ═══════════════════════════════════════════════════════════════

def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _estimate_score(item: dict[str, Any]) -> int:
    """根据已有字段估算 platform_quality_score（0-100）。"""
    score = 60  # 基础分
    confidence = item.get("metadata_confidence")
    if isinstance(confidence, (int, float)):
        score = int(confidence * 100)
    if item.get("downloadable"):
        score = min(score + 10, 100)
    return max(0, min(100, score))


def _extract_view_count(item: dict[str, Any]) -> int | None:
    """从 raw 字段或顶层字段提取播放量。"""
    for key in ("view_count", "play", "views"):
        val = item.get(key)
        if isinstance(val, (int, float)):
            return int(val)
    raw = item.get("raw")
    if isinstance(raw, dict):
        for key in ("play", "view", "views"):
            val = raw.get(key)
            if isinstance(val, (int, float)):
                return int(val)
    return None
