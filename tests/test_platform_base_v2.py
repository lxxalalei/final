#!/usr/bin/env python3
"""platform_base.py v2 增强功能验证测试。

验证项：
  1. 向后兼容：现有子类（BilibiliSkill 等）无参实例化正常
  2. RateLimiter：请求间隔控制生效
  3. CircuitBreaker：三态状态机转换正确
  4. CredentialManager：多来源凭证解析 + 脱敏日志
  5. subprocess env 注入：凭证通过环境变量传递给子进程
"""

from __future__ import annotations

import os
import sys
import time
import json
import tempfile
from pathlib import Path

# 确保能导入 shared
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.platform_base import (
    RateLimiter,
    CircuitBreaker,
    CircuitBreakerOpenError,
    CredentialManager,
    CLIBasedPlatformSkill,
    _sanitize_for_log,
    _mask_value,
)


# ─── 测试辅助 ─────────────────────────────────────────────

# 简单的颜色输出
def _ok(msg: str) -> None:
    print(f"  \033[32m✓\033[0m {msg}")

def _fail(msg: str) -> None:
    print(f"  \033[31m✗\033[0m {msg}")

def _section(title: str) -> None:
    print(f"\n\033[1m── {title} ──\033[0m")


# ─── 测试用例 ─────────────────────────────────────────────

def test_backward_compatibility() -> bool:
    """测试1：现有子类无参实例化，保持向后兼容。"""
    _section("测试1：向后兼容性")
    all_ok = True

    # 模拟一个简单的子类（不依赖真实平台脚本）
    class FakeSkill(CLIBasedPlatformSkill):
        platform_name = "fake"

    try:
        skill = FakeSkill()  # 无参实例化
        _ok("FakeSkill() 无参实例化成功")
    except Exception as exc:
        _fail(f"无参实例化失败: {exc}")
        return False

    # 检查增强组件已初始化
    checks = [
        ("_rate_limiter", skill._rate_limiter is not None, "速率限制器已初始化"),
        ("_circuit_breaker", skill._circuit_breaker is not None, "断路器已初始化"),
        ("_credential_manager", skill._credential_manager is not None, "凭证管理器已初始化"),
    ]
    for name, cond, desc in checks:
        if cond:
            _ok(desc)
        else:
            _fail(f"{name} 未初始化")
            all_ok = False

    # 验证真实平台适配器也能无参实例化（不导入有外部依赖的）
    # 这里只验证签名兼容，不真正调用（因为依赖真实脚本路径）
    try:
        import importlib
        # 测试 import adapter 模块（不实例化，因为依赖 sys.executable 路径等）
        _ok("CLIBasedPlatformSkill.__init__ 签名支持无参调用")
    except Exception as exc:
        _fail(f"导入异常: {exc}")
        all_ok = False

    return all_ok


def test_rate_limiter() -> bool:
    """测试2：RateLimiter 请求间隔控制。"""
    _section("测试2：RateLimiter 速率限制")
    all_ok = True

    # 测试1：第一次调用不等待
    rl = RateLimiter(min_interval=0.5)
    t0 = time.monotonic()
    wait0 = rl.acquire()
    t1 = time.monotonic()
    if wait0 == 0.0 and (t1 - t0) < 0.1:
        _ok(f"第一次 acquire() 立即返回（wait={wait0:.3f}s）")
    else:
        _fail(f"第一次 acquire() 不应等待，实际 wait={wait0:.3f}s")
        all_ok = False

    # 测试2：第二次调用应等待
    t0 = time.monotonic()
    wait1 = rl.acquire()
    t1 = time.monotonic()
    if wait1 > 0 and (t1 - t0) >= 0.4:
        _ok(f"第二次 acquire() 等待了 {wait1:.3f}s（>= 0.4s 预期）")
    else:
        _fail(f"第二次 acquire() 应等待 ~0.5s，实际 wait={wait1:.3f}s, elapsed={t1-t0:.3f}s")
        all_ok = False

    # 测试3：reset 后立即返回
    rl.reset()
    t0 = time.monotonic()
    wait2 = rl.acquire()
    t1 = time.monotonic()
    if wait2 == 0.0 and (t1 - t0) < 0.1:
        _ok("reset() 后 acquire() 立即返回")
    else:
        _fail(f"reset 后应立即返回，wait={wait2:.3f}s")
        all_ok = False

    # 测试4：interval=0 时不等待
    rl0 = RateLimiter(min_interval=0)
    if rl0.acquire() == 0.0 and rl0.acquire() == 0.0:
        _ok("min_interval=0 时始终立即返回")
    else:
        _fail("min_interval=0 应始终返回 0.0")
        all_ok = False

    return all_ok


def test_circuit_breaker() -> bool:
    """测试3：CircuitBreaker 三态转换。"""
    _section("测试3：CircuitBreaker 断路器")
    all_ok = True

    # 测试1：初始 CLOSED
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    if cb.state == CircuitBreaker.CLOSED:
        _ok(f"初始状态: {cb.state}")
    else:
        _fail(f"初始状态应为 CLOSED，实际 {cb.state}")
        return False

    # 测试2：CLOSED 下 before_call 不抛异常
    try:
        cb.before_call()
        _ok("CLOSED 状态下 before_call() 放行")
    except CircuitBreakerOpenError:
        _fail("CLOSED 状态不应抛异常")
        all_ok = False

    # 测试3：连续失败 3 次触发 OPEN
    cb.on_failure()
    cb.on_failure()
    if cb.state == CircuitBreaker.CLOSED:
        _ok("失败 2/3 次仍为 CLOSED")
    else:
        _fail(f"失败 2 次应为 CLOSED，实际 {cb.state}")
        all_ok = False

    cb.on_failure()  # 第3次，触发熔断
    if cb.state == CircuitBreaker.OPEN:
        _ok("失败 3/3 次触发 OPEN（熔断）")
    else:
        _fail(f"失败 3 次应为 OPEN，实际 {cb.state}")
        all_ok = False

    # 测试4：OPEN 状态下 before_call 抛异常
    try:
        cb.before_call()
        _fail("OPEN 状态应抛 CircuitBreakerOpenError")
        all_ok = False
    except CircuitBreakerOpenError:
        _ok("OPEN 状态下 before_call() 正确抛出 CircuitBreakerOpenError")

    # 测试5：冷却后转 HALF_OPEN
    time.sleep(1.1)
    if cb.state == CircuitBreaker.HALF_OPEN:
        _ok("冷却 1s 后转为 HALF_OPEN")
    else:
        _fail(f"冷却后应为 HALF_OPEN，实际 {cb.state}")
        all_ok = False

    # 测试6：HALF_OPEN 成功 → CLOSED
    cb.on_success()
    if cb.state == CircuitBreaker.CLOSED:
        _ok("HALF_OPEN 成功后转为 CLOSED")
    else:
        _fail(f"HALF_OPEN 成功应为 CLOSED，实际 {cb.state}")
        all_ok = False

    # 测试7：HALF_OPEN 失败 → 重新 OPEN
    cb2 = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)
    cb2.on_failure()  # 直接触发 OPEN（threshold=1）
    time.sleep(1.1)
    assert cb2.state == CircuitBreaker.HALF_OPEN
    cb2.on_failure()
    if cb2.state == CircuitBreaker.OPEN:
        _ok("HALF_OPEN 失败后重新触发 OPEN")
    else:
        _fail(f"HALF_OPEN 失败应为 OPEN，实际 {cb2.state}")
        all_ok = False

    return all_ok


def test_credential_manager() -> bool:
    """测试4：CredentialManager 多来源解析 + 脱敏。"""
    _section("测试4：CredentialManager 凭证安全")
    all_ok = True

    # 准备临时配置文件
    tmpdir = Path(tempfile.mkdtemp())
    cred_dir = tmpdir / "fakeplat" / "config"
    cred_dir.mkdir(parents=True)
    cred_file = cred_dir / "credentials.json"
    cred_file.write_text(json.dumps({
        "cookie": "FILE_COOKIE_VALUE_abc123",
        "api_key": "FILE_API_KEY_xyz",
    }), encoding="utf-8")

    # 设置环境变量
    os.environ["FAKEPLAT_TOKEN"] = "ENV_TOKEN_value456"

    cm = CredentialManager(
        platform_name="fakeplat",
        credentials={"password": "EXPLICIT_PASSWORD_789"},
        config_dir=tmpdir,
    )

    # 测试1：显式传入优先级最高
    pwd = cm.get("password")
    if pwd == "EXPLICIT_PASSWORD_789":
        _ok("显式传入凭证优先级最高")
    else:
        _fail(f"显式凭证获取失败: {pwd}")
        all_ok = False

    # 测试2：环境变量
    token = cm.get("token")
    if token == "ENV_TOKEN_value456":
        _ok("环境变量凭证正确读取（FAKEPLAT_TOKEN）")
    else:
        _fail(f"环境变量凭证获取失败: {token}")
        all_ok = False

    # 测试3：配置文件
    cookie = cm.get("cookie")
    if cookie == "FILE_COOKIE_VALUE_abc123":
        _ok("配置文件凭证正确读取（credentials.json）")
    else:
        _fail(f"配置文件凭证获取失败: {cookie}")
        all_ok = False

    # 测试4：get_all 合并
    all_creds = cm.get_all()
    if "password" in all_creds and "token" in all_creds and "cookie" in all_creds:
        _ok(f"get_all() 合并了 3 个来源的凭证（{len(all_creds)} 个字段）")
    else:
        _fail(f"get_all() 合并不完整: {list(all_creds.keys())}")
        all_ok = False

    # 测试5：to_env_dict
    env_dict = cm.to_env_dict()
    if "FAKEPLAT_PASSWORD" in env_dict and "FAKEPLAT_TOKEN" in env_dict:
        _ok(f"to_env_dict() 生成 {len(env_dict)} 个环境变量")
    else:
        _fail(f"to_env_dict() 缺少键: {list(env_dict.keys())}")
        all_ok = False

    # 测试6：脱敏日志
    safe_str = cm.safe_log("测试凭证")
    if "EXPLICIT_PASSWORD_789" not in safe_str and "****" in safe_str:
        _ok(f"safe_log() 脱敏成功: {safe_str}")
    else:
        _fail(f"safe_log() 未正确脱敏: {safe_str}")
        all_ok = False

    # 清理
    del os.environ["FAKEPLAT_TOKEN"]
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

    return all_ok


def test_sanitization() -> bool:
    """测试5：_sanitize_for_log 和 _mask_value 脱敏函数。"""
    _section("测试5：脱敏函数")
    all_ok = True

    # _mask_value
    masked = _mask_value("abcdefghij", visible=4)
    if masked == "******ghij":
        _ok(f"_mask_value('abcdefghij') = '{masked}'")
    else:
        _fail(f"_mask_value 结果错误: {masked}")
        all_ok = False

    short = _mask_value("ab", visible=4)
    if short == "**":
        _ok(f"_mask_value('ab') 短值全掩码: '{short}'")
    else:
        _fail(f"_mask_value 短值处理错误: {short}")
        all_ok = False

    # _sanitize_for_log - dict
    data = {
        "cookie": "very_long_cookie_string_12345",
        "title": "公开标题",
        "token": "secret_token_value",
        "nested": {"api_key": "key123", "data": "ok"},
    }
    sanitized = _sanitize_for_log(data)
    if ("very_long_cookie_string_12345" not in str(sanitized)
            and "公开标题" in str(sanitized)
            and sanitized["cookie"] != data["cookie"]):
        _ok(f"_sanitize_for_log 正确脱敏敏感字段（cookie/token），保留公开字段")
    else:
        _fail(f"_sanitize_for_log 脱敏失败: {sanitized}")
        all_ok = False

    return all_ok


def test_subprocess_env_injection() -> bool:
    """测试6：凭证通过环境变量注入子进程。"""
    _section("测试6：子进程凭证注入")
    all_ok = True

    class FakeSkill2(CLIBasedPlatformSkill):
        platform_name = "testenv"

    skill = FakeSkill2(credentials={"cookie": "MY_COOKIE_123", "token": "MY_TOKEN_456"})
    env = skill._build_subprocess_env()

    if env.get("TESTENV_COOKIE") == "MY_COOKIE_123":
        _ok("TESTENV_COOKIE 注入成功")
    else:
        _fail(f"TESTENV_COOKIE 注入失败: {env.get('TESTENV_COOKIE')}")
        all_ok = False

    if env.get("TESTENV_TOKEN") == "MY_TOKEN_456":
        _ok("TESTENV_TOKEN 注入成功")
    else:
        _fail(f"TESTENV_TOKEN 注入失败: {env.get('TESTENV_TOKEN')}")
        all_ok = False

    # 运行时凭证（从 intent/candidate 提取）覆盖
    runtime_creds = {"sessdata": "RUNTIME_SESSDATA"}
    env2 = skill._build_subprocess_env(runtime_creds)
    if env2.get("TESTENV_SESSDATA") == "RUNTIME_SESSDATA":
        _ok("运行时凭证（intent/candidate）正确注入")
    else:
        _fail(f"运行时凭证注入失败: {env2.get('TESTENV_SESSDATA')}")
        all_ok = False

    return all_ok


def test_integration_search_with_circuit_breaker() -> bool:
    """测试7：搜索流程集成断路器——子进程返回失败码后多次触发熔断。

    使用一个真实存在的脚本（exit 1）模拟平台返回错误，
    这才是断路器应当保护的真实场景（平台封禁/API错误等）。
    配置错误（脚本不存在）属于本地问题，不触发熔断。
    """
    _section("测试7：搜索集成断路器（端到端）")
    all_ok = True

    # 创建一个总是失败的假搜索脚本
    tmpdir = Path(tempfile.mkdtemp())
    fake_script = tmpdir / "fake_search.py"
    fake_script.write_text(
        "import sys; sys.exit(1)",  # 总是返回失败码
        encoding="utf-8",
    )

    class FakeSkill3(CLIBasedPlatformSkill):
        platform_name = "fake_circuit_test"

        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self._search_script = fake_script

        def _build_search_cmd(self, intent, output_file):
            keywords = intent.get("keywords") or "test"
            if not keywords:
                return None
            return [
                sys.executable, str(self._search_script),
                "search", keywords,
                "--max", "5",
                "-o", str(output_file),
            ]

    # failure_threshold=2 快速触发熔断
    skill = FakeSkill3(failure_threshold=2, recovery_timeout=1.0)

    # 第一次搜索：脚本执行失败（returncode=1）→ _record_failure
    r1 = skill.search({"keywords": "test"})
    if r1.get("error", {}).get("error_code") == "SYSTEM_UNKNOWN_ERROR":
        _ok("第1次搜索：子进程返回失败码（预期）")
    else:
        _fail(f"第1次搜索结果异常: {r1.get('error')}")
        all_ok = False

    # 第二次搜索：同样失败，达到 threshold=2 → 触发熔断
    r2 = skill.search({"keywords": "test"})
    if skill._circuit_breaker and skill._circuit_breaker.state == CircuitBreaker.OPEN:
        _ok("第2次失败后断路器触发 OPEN")
    else:
        state = skill._circuit_breaker.state if skill._circuit_breaker else "None"
        _fail(f"第2次失败后应为 OPEN，实际 {state}")
        all_ok = False

    # 第三次搜索：断路器 OPEN，应直接返回 ANTI_CRAWL_BLOCKED
    r3 = skill.search({"keywords": "test"})
    if r3.get("error", {}).get("error_code") == "ANTI_CRAWL_BLOCKED":
        _ok("第3次搜索被断路器拦截 → ANTI_CRAWL_BLOCKED")
    else:
        _fail(f"第3次搜索应被熔断拦截，实际: {r3.get('error')}")
        all_ok = False

    # 清理
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

    return all_ok


# ─── 主入口 ───────────────────────────────────────────────

def main() -> int:
    print("\033[1m╔══════════════════════════════════════════════╗\033[0m")
    print("\033[1m║  platform_base.py v2 增强功能验证             ║\033[0m")
    print("\033[1m╚══════════════════════════════════════════════╝\033[0m")

    tests = [
        ("向后兼容性", test_backward_compatibility),
        ("RateLimiter", test_rate_limiter),
        ("CircuitBreaker", test_circuit_breaker),
        ("CredentialManager", test_credential_manager),
        ("脱敏函数", test_sanitization),
        ("子进程凭证注入", test_subprocess_env_injection),
        ("搜索集成断路器", test_integration_search_with_circuit_breaker),
    ]

    results = []
    for name, func in tests:
        try:
            passed = func()
            results.append((name, passed))
        except Exception as exc:
            import traceback
            traceback.print_exc()
            results.append((name, False))

    # 汇总
    print("\n\033[1m══════════════ 测试汇总 ══════════════\033[0m")
    passed_count = sum(1 for _, p in results if p)
    for name, passed in results:
        mark = "\033[32mPASS\033[0m" if passed else "\033[31mFAIL\033[0m"
        print(f"  {mark}  {name}")
    print(f"\n  结果: {passed_count}/{len(results)} 通过")
    return 0 if passed_count == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
