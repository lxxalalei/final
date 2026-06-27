#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
共享文件同步工具
从源目录（shared/）同步文件到各个 Skill 的 references/ 目录

使用方法：
    python scripts/sync-shared.py                    # 同步所有 Skill
    python scripts/sync-shared.py --skills resource-search resource-downloader  # 只同步指定 Skill
    python scripts/sync-shared.py --dry-run          # 预览模式，不实际复制
"""

import os
import shutil
import argparse

# ============================================================
# 配置：哪些 Skill 需要哪些文件
# ============================================================
SYNC_CONFIG = {
    "resource-intent": {
        "schemas": ["skill-contract.md", "session-io-spec.md", "resource-schema.md"]
    },
    "resource-selector": {
        "schemas": ["skill-contract.md", "session-io-spec.md", "resource-schema.md"]
    },
    "resource-search": {
        "config": ["platform-mapping.md", "platform-advantages.md"],
        "schemas": ["skill-contract.md", "session-io-spec.md", "resource-schema.md", "quality-rubric.md"]
    },
    "resource-downloader": {
        "config": ["platform-mapping.md"],
        "schemas": ["skill-contract.md", "session-io-spec.md", "resource-schema.md", "error-codes.md"]
    },
    "library-manager": {
        "schemas": ["skill-contract.md", "session-io-spec.md", "resource-schema.md"]
    },
    "learning-resource-flow": {
        "schemas": ["skill-contract.md", "session-io-spec.md", "resource-schema.md"]
    },
    "resource-platforms": {
        "config": ["platform-mapping.md"],
        "schemas": ["resource-schema.md", "error-codes.md"]
    },
}


def sync_file(source_path, target_path, dry_run=False):
    """同步单个文件"""
    if dry_run:
        print(f"  [预览] 将复制: {os.path.basename(target_path)}")
        return True
    
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.copy2(source_path, target_path)
    print(f"  ✓ {os.path.basename(target_path)}")
    return True


def sync_skill(skill_name, source_base, project_root, dry_run=False):
    """同步一个 Skill 的所有共享文件"""
    if skill_name not in SYNC_CONFIG:
        print(f"⚠️  未找到 {skill_name} 的同步配置，跳过")
        return False
    
    skill_path = os.path.join(project_root, skill_name)
    if not os.path.exists(skill_path):
        print(f"⚠️  Skill 目录不存在: {skill_path}，跳过")
        return False
    
    print(f"\n📦 同步 {skill_name}...")
    
    config = SYNC_CONFIG[skill_name]
    total = 0
    success = 0
    
    for category, files in config.items():
        target_dir = os.path.join(skill_path, "references", category)
        source_dir = os.path.join(source_base, category)
        
        for filename in files:
            total += 1
            source_file = os.path.join(source_dir, filename)
            target_file = os.path.join(target_dir, filename)
            
            if os.path.exists(source_file):
                if sync_file(source_file, target_file, dry_run):
                    success += 1
            else:
                print(f"  ⚠️  源文件不存在: {source_file}")
    
    print(f"   完成: {success}/{total} 个文件")
    return success == total


def main():
    parser = argparse.ArgumentParser(description="共享文件同步工具 - 将 shared/ 目录的文件同步到各个 Skill")
    parser.add_argument("--source", default="shared/", help="源目录（默认: shared/）")
    parser.add_argument("--project-root", default=".", help="项目根目录（默认: .）")
    parser.add_argument("--skills", nargs="*", help="指定要同步的 Skill（默认全部）")
    parser.add_argument("--dry-run", action="store_true", help="预览模式，不实际复制文件")
    parser.add_argument("--list", action="store_true", help="列出所有可同步的 Skill")
    
    args = parser.parse_args()
    
    # 列出模式
    if args.list:
        print("📋 可同步的 Skill 列表：")
        for skill_name in sorted(SYNC_CONFIG.keys()):
            files_count = sum(len(files) for files in SYNC_CONFIG[skill_name].values())
            print(f"  - {skill_name} ({files_count} 个文件)")
        return
    
    source_base = os.path.abspath(args.source)
    project_root = os.path.abspath(args.project_root)
    
    if not os.path.exists(source_base):
        print(f"❌ 源目录不存在: {source_base}")
        print(f"   请使用 --source 指定正确的源目录")
        return
    
    skills_to_sync = args.skills if args.skills else SYNC_CONFIG.keys()
    
    print(f"🚀 {'[预览模式] ' if args.dry_run else ''}开始同步共享文件...")
    print(f"   源目录: {source_base}")
    print(f"   项目根目录: {project_root}")
    print(f"   待同步 Skill: {', '.join(skills_to_sync)}")
    
    success_count = 0
    for skill_name in skills_to_sync:
        if sync_skill(skill_name, source_base, project_root, args.dry_run):
            success_count += 1
    
    print(f"\n{'='*50}")
    print(f"✅ 同步完成！成功: {success_count}/{len(skills_to_sync)} 个 Skill")
    if args.dry_run:
        print(f"   （预览模式，未实际复制文件）")


if __name__ == "__main__":
    main()
