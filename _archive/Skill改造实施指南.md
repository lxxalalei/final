# Skill 独立封装改造实施指南

> **版本**：v1.0
> **适用对象**：需要进行 Skill 改造的开发者
> **示例 Skill**：resource-intent（最简单，作为入门示例）

---

## 一、快速开始：5 步完成一个 Skill 的改造

我们以 `resource-intent` 为例，展示完整的改造过程。

### 第 1 步：梳理依赖清单

先找出这个 Skill 引用了哪些外部文件：

```bash
# 在 resource-intent/SKILL.md 中查找所有 ../shared/ 引用
grep "../shared/" resource-intent/SKILL.md
```

**resource-intent 的依赖清单**：
- `../shared/schemas/skill-contract.md`
- `../shared/schemas/session-io-spec.md`
- `../shared/schemas/resource-schema.md`

### 第 2 步：创建目录结构

在 Skill 内部创建 references 目录：

```bash
cd resource-intent
mkdir -p references/schemas
```

改造后的目录结构：
```
resource-intent/
├── SKILL.md
├── references/
│   └── schemas/
│       ├── skill-contract.md
│       ├── session-io-spec.md
│       └── resource-schema.md
└── ... （其他原有文件）
```

### 第 3 步：复制共享文件

将需要的文件从 shared/ 复制到 Skill 内部：

```bash
# 复制 schemas 文件
cp ../shared/schemas/skill-contract.md references/schemas/
cp ../shared/schemas/session-io-spec.md references/schemas/
cp ../shared/schemas/resource-schema.md references/schemas/
```

### 第 4 步：修改 SKILL.md 中的引用路径

将所有 `../shared/` 开头的路径，改为 `./references/` 开头。

**改造前**：
```markdown
## 参考资料
- `../shared/schemas/skill-contract.md` - 跨 Skill 上下文传递契约
- `../shared/schemas/session-io-spec.md` - 会话上下文读写规范
- `../shared/schemas/resource-schema.md` - 资源元数据规范
```

**改造后**：
```markdown
## 参考资料
- `./references/schemas/skill-contract.md` - 跨 Skill 上下文传递契约
- `./references/schemas/session-io-spec.md` - 会话上下文读写规范
- `./references/schemas/resource-schema.md` - 资源元数据规范
```

### 第 5 步：验证

1. 检查所有引用路径是否都修改了
2. 确认复制的文件都存在
3. 测试 Skill 是否能正常工作

✅ 完成！这个 Skill 现在已经可以独立运行了。

---

## 二、各 Skill 改造详细指南

### 2.1 resource-intent（最简单，推荐先做）

**依赖文件**：
- schemas/skill-contract.md
- schemas/session-io-spec.md
- schemas/resource-schema.md

**改造难度**：⭐（最简单）

**改造要点**：
- 只需要复制 3 个 schema 文件
- 没有 Python 代码依赖
- 没有跨 Skill 调用

---

### 2.2 resource-selector（简单）

**依赖文件**：
- schemas/skill-contract.md
- schemas/session-io-spec.md
- schemas/resource-schema.md

**改造难度**：⭐

**改造要点**：
- 和 resource-intent 类似
- 只需要复制 schema 文件

---

### 2.3 resource-search（中等难度）

**依赖文件**：
- config/platform-mapping.md
- config/platform-advantages.md
- schemas/skill-contract.md
- schemas/session-io-spec.md
- schemas/resource-schema.md
- schemas/quality-rubric.md

**改造难度**：⭐⭐

**改造要点**：
1. 需要复制 config 和 schemas 两类文件
2. 需要处理平台发现机制
3. 原来直接调用 resource-platforms 的脚本，需要改为通过注册表

**目录结构**：
```
resource-search/
├── SKILL.md
├── references/
│   ├── config/
│   │   ├── platform-mapping.md
│   │   └── platform-advantages.md
│   └── schemas/
│       ├── skill-contract.md
│       ├── session-io-spec.md
│       ├── resource-schema.md
│       └── quality-rubric.md
└── scripts/
    └── platform_discovery.py  # 平台发现模块
```

**平台发现机制改造**：

改造前（直接调用）：
```python
# 直接知道平台脚本的位置
bilibili_script = "../resource-platforms/scripts/bilibili/bilibili_search.py"
```

改造后（通过注册表发现）：
```python
import json
import os

def discover_platforms():
    """从注册表发现可用平台"""
    workspace = find_workspace()
    registry_path = os.path.join(workspace, "registry", "platforms.json")
    
    if os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = json.load(f)
        return registry["platforms"]
    else:
        # 兜底：使用内置的默认配置
        return get_default_platforms()

def get_default_platforms():
    """内置的默认平台配置（兜底用）"""
    return {
        "bilibili": {
            "name": "B站",
            "status": "available",
            # ... 其他默认配置
        }
    }
```

---

### 2.4 resource-downloader（中等难度）

**依赖文件**：
- config/platform-mapping.md
- schemas/skill-contract.md
- schemas/session-io-spec.md
- schemas/resource-schema.md
- schemas/error-codes.md

**改造难度**：⭐⭐

**改造要点**：
- 和 resource-search 类似
- 需要平台发现机制
- 需要处理错误码体系

---

### 2.5 library-manager（中等难度）

**依赖文件**：
- schemas/skill-contract.md
- schemas/session-io-spec.md
- schemas/resource-schema.md
- （重点）dedup.py 去重引擎

**改造难度**：⭐⭐

**改造要点**：
1. 复制 schema 文件
2. 将 dedup.py 复制到 Skill 内部
3. 修改引用路径

**目录结构**：
```
library-manager/
├── SKILL.md
├── references/
│   └── schemas/
│       ├── skill-contract.md
│       ├── session-io-spec.md
│       └── resource-schema.md
└── scripts/
    ├── __init__.py
    └── dedup.py  ← 从 resource-platforms/scripts/shared/ 复制过来
```

**代码修改**：

改造前：
```python
# 跨目录引用
import sys
sys.path.append("../resource-platforms/scripts/shared")
from dedup import DedupEngine
```

改造后：
```python
# 使用 Skill 内部的模块
from .scripts.dedup import DedupEngine
```

---

### 2.6 learning-resource-flow（中等难度）

**依赖文件**：
- schemas/skill-contract.md
- schemas/session-io-spec.md
- schemas/resource-schema.md

**改造难度**：⭐⭐

**改造要点**：
1. 复制 schema 文件
2. 实现工作区发现机制
3. 实现会话管理

**新增功能：工作区发现**

```python
import os

def find_workspace() -> str:
    """
    按优先级查找工作区根目录：
    1. 环境变量 LRS_WORKSPACE
    2. 当前目录下的 .learning-resource-work
    3. 用户主目录下的 .learning-resource-work
    """
    # 1. 环境变量
    env_workspace = os.environ.get('LRS_WORKSPACE')
    if env_workspace and os.path.exists(env_workspace):
        return env_workspace
    
    # 2. 当前目录
    cwd_workspace = os.path.join(os.getcwd(), '.learning-resource-work')
    if os.path.exists(cwd_workspace):
        return cwd_workspace
    
    # 3. 用户主目录
    home_workspace = os.path.join(os.path.expanduser('~'), '.learning-resource-work')
    if os.path.exists(home_workspace):
        return home_workspace
    
    # 都不存在，默认在当前目录创建
    os.makedirs(cwd_workspace, exist_ok=True)
    return cwd_workspace
```

---

### 2.7 平台 Skill（较复杂）

以 bilibili 为例：

**依赖文件**：
- schemas/resource-schema.md
- schemas/error-codes.md
- （重点）shared/ 下的所有 Python 模块

**改造难度**：⭐⭐⭐

**改造要点**：
1. 将 scripts/shared/ 下的模块复制到每个平台的 _shared/ 目录
2. 修改 import 路径
3. 实现平台注册功能

**目录结构**：
```
platform-bilibili/
├── SKILL.md
├── README.md
├── references/
│   └── schemas/
│       ├── resource-schema.md
│       └── error-codes.md
└── scripts/
    ├── _shared/           ← 内嵌的共享模块
    │   ├── __init__.py
    │   ├── platform_base.py
    │   ├── config_loader.py
    │   ├── logger.py
    │   ├── utils.py
    │   └── wbi_sign.py
    ├── __init__.py
    ├── adapter.py
    ├── bilibili_search.py
    └── bilibili_dl.py
```

**代码修改示例**：

改造前（bilibili_search.py）：
```python
from shared.platform_base import CLIBasedPlatformSkill
from shared.utils import safe_filename
from shared.logger import get_logger
```

改造后：
```python
from ._shared.platform_base import CLIBasedPlatformSkill
from ._shared.utils import safe_filename
from ._shared.logger import get_logger
```

**新增：平台注册功能**

每个平台 Skill 都提供一个注册函数：

```python
# scripts/register.py
import json
import os

def register(workspace_path: str = None):
    """将本平台注册到平台注册表"""
    if workspace_path is None:
        # 自动发现工作区
        workspace_path = find_workspace()
    
    registry_dir = os.path.join(workspace_path, "registry")
    os.makedirs(registry_dir, exist_ok=True)
    
    registry_file = os.path.join(registry_dir, "platforms.json")
    
    # 读取现有注册表
    if os.path.exists(registry_file):
        with open(registry_file, "r", encoding="utf-8") as f:
            registry = json.load(f)
    else:
        registry = {"version": "1.0", "platforms": {}}
    
    # 本平台信息
    platform_info = {
        "name": "B站（哔哩哔哩）",
        "status": "available",
        "priority": "P0",
        "resource_types": ["视频"],
        "search_script": os.path.abspath(os.path.join(os.path.dirname(__file__), "bilibili_search.py")),
        "download_script": os.path.abspath(os.path.join(os.path.dirname(__file__), "bilibili_dl.py")),
        "adapter_path": os.path.abspath(os.path.join(os.path.dirname(__file__), "adapter.py")),
        "capabilities": {
            "search": True,
            "download": True,
            "subtitle": True,
            "quality_levels": ["S", "A", "B", "C"]
        }
    }
    
    registry["platforms"]["bilibili"] = platform_info
    
    # 写回注册表
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 平台 bilibili 已注册到 {registry_file}")
    return True
```

---

## 三、数据流转验证方法

改造完成后，如何验证 Skill 之间的数据流转是否正常？

### 3.1 单元测试：单个 Skill 的输入输出

测试每个 Skill 是否能正确读取输入文件并生成输出文件。

**测试步骤**：
1. 准备一个测试用的输入文件（符合契约格式）
2. 调用 Skill 处理
3. 检查输出文件是否符合契约格式

**示例：测试 resource-intent**

```python
import json
import tempfile
import os

def test_resource_intent():
    # 创建临时会话目录
    with tempfile.TemporaryDirectory() as session_dir:
        # 准备输入（intent 是第一个阶段，没有上游文件）
        user_request = "帮我找三年级数学练习题"
        
        # 调用 intent Skill（模拟）
        # ... 执行 intent 逻辑 ...
        
        # 检查输出文件
        output_file = os.path.join(session_dir, "stage1_intent.json")
        assert os.path.exists(output_file)
        
        with open(output_file, "r", encoding="utf-8") as f:
            output = json.load(f)
        
        # 验证三层结构
        assert "_meta" in output
        assert "_summary" in output
        assert "data" in output
        
        # 验证必填字段
        assert "core_topic" in output["data"]
        assert "queries" in output["data"]
        assert "search_mode" in output["data"]
        
        print("✅ resource-intent 输出格式正确")
```

### 3.2 集成测试：两个 Skill 的数据传递

测试两个相邻 Skill 之间能否正确传递数据。

**示例：测试 intent → search**

```python
def test_intent_to_search():
    with tempfile.TemporaryDirectory() as session_dir:
        # 1. 运行 intent，生成 stage1
        run_intent(session_dir, "三年级数学练习题")
        
        # 2. 检查 stage1 文件
        stage1_file = os.path.join(session_dir, "stage1_intent.json")
        assert os.path.exists(stage1_file)
        
        # 3. 运行 search，读取 stage1，生成 stage2
        run_search(session_dir)
        
        # 4. 检查 stage2 文件
        stage2_file = os.path.join(session_dir, "stage2_search.json")
        assert os.path.exists(stage2_file)
        
        # 5. 验证数据是否正确传递
        with open(stage2_file, "r", encoding="utf-8") as f:
            stage2 = json.load(f)
        
        assert stage2["_meta"]["input_from"] == "stage1_intent.json"
        assert "resources" in stage2["data"]
        
        print("✅ intent → search 数据传递正常")
```

### 3.3 端到端测试：完整流程

测试整个工作流能否跑通。

```python
def test_full_workflow():
    with tempfile.TemporaryDirectory() as session_dir:
        # 阶段 1：intent
        run_intent(session_dir, "小学三年级数学练习题")
        
        # 阶段 2：search
        run_search(session_dir)
        
        # 阶段 3：selector（模拟用户选择）
        run_selector(session_dir, selection="all")
        
        # 阶段 4：downloader
        run_downloader(session_dir)
        
        # 阶段 5：library
        run_library(session_dir)
        
        # 验证所有阶段文件都存在
        for i in range(1, 6):
            stage_file = os.path.join(session_dir, f"stage{i}_*.json")
            assert len(glob.glob(stage_file)) > 0, f"阶段 {i} 文件不存在"
        
        print("✅ 完整流程测试通过")
```

---

## 四、维护工具：同步脚本

为了解决"代码重复导致维护困难"的问题，我们提供一个同步脚本。

### 4.1 sync-shared.py

```python
#!/usr/bin/env python3
"""
共享文件同步工具
从源目录（shared/）同步文件到各个 Skill 的 references/ 目录
"""

import os
import shutil
import argparse

# 配置：哪些 Skill 需要哪些文件
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
}

def sync_file(source_path, target_path):
    """同步单个文件"""
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    shutil.copy2(source_path, target_path)
    print(f"  ✓ {os.path.basename(target_path)}")

def sync_skill(skill_name, source_base, project_root):
    """同步一个 Skill 的所有共享文件"""
    if skill_name not in SYNC_CONFIG:
        print(f"⚠️  未找到 {skill_name} 的同步配置")
        return
    
    skill_path = os.path.join(project_root, skill_name)
    if not os.path.exists(skill_path):
        print(f"⚠️  Skill 目录不存在: {skill_path}")
        return
    
    print(f"\n📦 同步 {skill_name}...")
    
    config = SYNC_CONFIG[skill_name]
    
    for category, files in config.items():
        target_dir = os.path.join(skill_path, "references", category)
        source_dir = os.path.join(source_base, category)
        
        for filename in files:
            source_file = os.path.join(source_dir, filename)
            target_file = os.path.join(target_dir, filename)
            
            if os.path.exists(source_file):
                sync_file(source_file, target_file)
            else:
                print(f"  ⚠️  源文件不存在: {source_file}")

def main():
    parser = argparse.ArgumentParser(description="共享文件同步工具")
    parser.add_argument("--source", default="shared/", help="源目录")
    parser.add_argument("--project-root", default=".", help="项目根目录")
    parser.add_argument("--skills", nargs="*", help="指定要同步的 Skill（默认全部）")
    
    args = parser.parse_args()
    
    source_base = os.path.abspath(args.source)
    project_root = os.path.abspath(args.project_root)
    
    if not os.path.exists(source_base):
        print(f"❌ 源目录不存在: {source_base}")
        return
    
    skills_to_sync = args.skills if args.skills else SYNC_CONFIG.keys()
    
    print(f"🚀 开始同步共享文件...")
    print(f"   源目录: {source_base}")
    print(f"   项目根目录: {project_root}")
    
    for skill_name in skills_to_sync:
        sync_skill(skill_name, source_base, project_root)
    
    print(f"\n✅ 同步完成！")

if __name__ == "__main__":
    main()
```

### 4.2 使用方法

```bash
# 同步所有 Skill
python scripts/sync-shared.py

# 只同步特定 Skill
python scripts/sync-shared.py --skills resource-search resource-downloader

# 指定源目录
python scripts/sync-shared.py --source /path/to/shared/
```

**维护工作流**：
1. 修改 shared/ 下的源文件（这是唯一的"真相源"）
2. 运行 `sync-shared.py` 同步到各个 Skill
3. 测试验证
4. 提交代码

---

## 五、向后兼容方案

为了确保改造过程不影响现有功能，我们采用**双路径支持**策略。

### 5.1 文件引用的向后兼容

每个 Skill 同时支持两种路径：
1. 新路径：`./references/xxx.md`（优先）
2. 旧路径：`../shared/xxx.md`（兜底）

**实现方式**：在代码中按优先级查找

```python
def find_reference_file(filename, category="schemas"):
    """查找参考文件，支持新旧两种路径"""
    # 1. 优先找 Skill 内部的
    internal_path = os.path.join("references", category, filename)
    if os.path.exists(internal_path):
        return internal_path
    
    # 2. 兜底找项目共享的
    shared_path = os.path.join("..", "shared", category, filename)
    if os.path.exists(shared_path):
        return shared_path
    
    # 都找不到
    raise FileNotFoundError(f"找不到参考文件: {filename}")
```

### 5.2 渐进式改造策略

不需要一次性改造所有 Skill，可以按以下顺序逐步进行：

1. **第一阶段**：先改造独立的 Skill（intent、selector）
2. **第二阶段**：改造调度器 Skill（search、downloader）
3. **第三阶段**：改造平台 Skill
4. **第四阶段**：改造主流程 Skill（flow）

每个阶段完成后都可以独立运行，不影响其他阶段。

---

## 六、常见问题

### Q1：改造后 Skill 体积变大了，有问题吗？

A：没有问题。虽然有一些文件重复，但换来的是完全的独立性。而且这些都是文本文件，体积很小（总共也就几百 KB）。

### Q2：共享文件修改后，不同步会有问题吗？

A：有风险。所以提供了 sync-shared.py 同步工具，每次修改源文件后运行一下即可。也可以设置 git hook 自动同步。

### Q3：平台注册表机制太复杂，能不能简化？

A：可以。初期可以不用注册表，直接把平台路径写死在配置文件里。等需要动态扩展时再加上注册表机制。

### Q4：能不能只改造部分 Skill？

A：可以。这就是渐进式改造的好处。你可以先改造 1-2 个 Skill 试试效果，没问题再推广。

### Q5：Python 的 import 路径怎么处理？

A：有几种方式：
1. 相对导入：`from ._shared.xxx import yyy`（推荐，最规范）
2. 绝对导入：把 Skill 目录加入 sys.path
3. 直接复制代码：把需要的函数直接复制到文件里（最简单，但维护成本高）

---

## 七、检查清单

改造完成后，用这个清单检查：

- [ ] 所有 `../shared/` 引用都改成了 `./references/`
- [ ] 所有需要的文件都复制到了 Skill 内部
- [ ] Python 模块的 import 路径都修改正确
- [ ] Skill 可以在独立目录中运行（不依赖项目根目录）
- [ ] 数据输入输出格式符合契约
- [ ] 向后兼容（原项目结构下仍然可用）
- [ ] SKILL.md 文档更新完成
- [ ] 测试用例通过

---

*文档版本：v1.0 | 编写日期：2026-06-27*
