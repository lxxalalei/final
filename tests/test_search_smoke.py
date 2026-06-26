#!/usr/bin/env python3
"""搜索冒烟测试 — 验证 7 个平台的 adapter import + 脚本发现机制。

不执行实际搜索（不联网），仅验证：
1. 每个平台的 adapter.py 可正常 import
2. adapter 的 platform_name 属性正确
3. 脚本发现机制能找到搜索脚本文件
4. platform_base.py 基类功能正常

运行方式：
    cd resource-platforms/scripts
    python ../../tests/test_search_smoke.py

或从项目根目录：
    python tests/test_search_smoke.py
"""

import sys
from pathlib import Path

# 确保 resource-platforms/scripts/ 在 sys.path 中
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "resource-platforms" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

# ═══════════════════════════════════════════════════════════════
#  测试结果收集
# ═══════════════════════════════════════════════════════════════

results = []

def check(name: str, condition: bool, detail: str = ""):
    status = "✅ PASS" if condition else "❌ FAIL"
    msg = f"  {status} · {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    results.append((name, condition))


def test_platform(plat_name: str, adapter_class_name: str):
    """测试单个平台。"""
    print(f"\n{'='*50}")
    print(f"平台：{plat_name}")
    print(f"{'='*50}")

    # 1. import adapter
    try:
        adapter_mod = __import__(f"{plat_name}.adapter", fromlist=["adapter"])
    except ImportError as e:
        check(f"{plat_name} import adapter", False, str(e))
        return
    check(f"{plat_name} import adapter", True)

    # 2. 获取 adapter 类
    try:
        cls = getattr(adapter_mod, adapter_class_name)
    except AttributeError as e:
        check(f"{plat_name} class {adapter_class_name}", False, str(e))
        return
    check(f"{plat_name} class {adapter_class_name}", True)

    # 3. 实例化
    try:
        instance = cls()
    except Exception as e:
        check(f"{plat_name} instantiate", False, str(e))
        return
    check(f"{plat_name} instantiate", True)

    # 4. platform_name 属性
    actual_name = getattr(instance, "platform_name", None)
    check(f"{plat_name} platform_name", actual_name == plat_name,
          f"expected={plat_name}, got={actual_name}")

    # 5. 脚本发现
    search_script = getattr(instance, "_search_script", None)
    if search_script is None:
        # 尝试自动发现
        search_script = instance._discover_script("*_search.py")
        if search_script is None and plat_name in ("bilibili", "smartedu", "douyin", "weibo"):
            # 这些平台用自定义脚本名（非 *_search.py 约定）
            # bilibili: bilibili_dl.py, smartedu: smartedu_resources.py
            # douyin: douyin_dl.py, weibo: weibo_dl.py
            known_scripts = {
                "bilibili": "bilibili_dl.py",
                "smartedu": "smartedu_resources.py",
                "douyin": "douyin_dl.py",
                "weibo": "weibo_dl.py",
            }
            script_name = known_scripts.get(plat_name)
            if script_name:
                script_path = SCRIPTS_DIR / plat_name / script_name
                search_script = script_path if script_path.exists() else None

    check(f"{plat_name} search script found", search_script is not None,
          str(search_script) if search_script else "NOT FOUND")

    if search_script:
        check(f"{plat_name} search script exists",
              Path(search_script).exists(),
              str(search_script))

    # 6. platform_base 基类
    from shared.platform_base import CLIBasedPlatformSkill
    check(f"{plat_name} inherits CLIBasedPlatformSkill",
          isinstance(instance, CLIBasedPlatformSkill))


def test_shared_modules():
    """测试共享模块 import。"""
    print(f"\n{'='*50}")
    print("共享模块")
    print(f"{'='*50}")

    modules = [
        ("shared.platform_base", "CLIBasedPlatformSkill"),
        ("shared.config_loader", "get_config"),
        ("shared.dedup", "DedupEngine"),
        ("shared.logger", "getLogger"),
        ("shared.utils", "safe_filename"),
        ("shared.wbi_sign", "wbi_sign"),
    ]

    for mod_name, attr_name in modules:
        try:
            mod = __import__(mod_name, fromlist=[attr_name])
            has_attr = hasattr(mod, attr_name)
            check(f"import {mod_name}.{attr_name}", has_attr,
                  "" if has_attr else f"missing attr {attr_name}")
        except ImportError as e:
            check(f"import {mod_name}.{attr_name}", False, str(e))


# ═══════════════════════════════════════════════════════════════
#  主函数
# ═══════════════════════════════════════════════════════════════

def main():
    print("╔══════════════════════════════════════════════╗")
    print("║   搜索冒烟测试 — 7 平台 adapter + 脚本发现   ║")
    print("╚══════════════════════════════════════════════╝")
    print(f"\nscripts_dir: {SCRIPTS_DIR}")
    print(f"exists: {SCRIPTS_DIR.exists()}")

    # 先测试共享模块
    test_shared_modules()

    # 测试 7 个平台
    platforms = [
        ("bilibili", "BilibiliSkill"),
        ("smartedu", "SmartEduSkill"),
        ("zhihu", "ZhihuSkill"),
        ("douyin", "DouyinSkill"),
        ("weibo", "WeiboSkill"),
        ("ximalaya", None),   # 搜索专用平台，无 adapter
        ("open163", None),    # 搜索专用平台，无 adapter
    ]

    for plat_name, class_name in platforms:
        if class_name is None:
            # 搜索专用平台：只检查脚本存在
            print(f"\n{'='*50}")
            print(f"平台：{plat_name}（搜索专用，无 adapter）")
            print(f"{'='*50}")
            script_dir = SCRIPTS_DIR / plat_name
            check(f"{plat_name} script dir exists", script_dir.exists(), str(script_dir))
            scripts = list(script_dir.glob("*.py")) if script_dir.exists() else []
            check(f"{plat_name} has scripts", len(scripts) > 0,
                  f"{len(scripts)} files")
        else:
            test_platform(plat_name, class_name)

    # 汇总
    print(f"\n{'='*50}")
    print("汇总")
    print(f"{'='*50}")
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed
    print(f"  总计：{total}  通过：{passed}  失败：{failed}")

    if failed > 0:
        print("\n失败项：")
        for name, ok in results:
            if not ok:
                print(f"  ❌ {name}")

    return 1 if failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
