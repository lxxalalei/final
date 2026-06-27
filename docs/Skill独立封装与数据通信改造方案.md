# Skill 独立封装与数据通信改造方案

> **版本**：v1.0
> **日期**：2026-06-27
> **适用范围**：儿童学习资源 Skill 套件全量改造

---

## 一、现状分析与问题总结

### 1.1 当前架构概述

当前项目采用三层架构设计：
- **流程编排层**：learning-resource-flow（总调度入口）
- **业务能力层**：resource-intent、resource-search、resource-selector、resource-downloader、library-manager
- **平台执行层**：resource-platforms（包含7个平台的搜索+下载能力）

数据流转通过文件系统（JSON文件）实现，这是很好的解耦设计。

### 1.2 核心问题

当前各个 Skill 无法独立安装到 Agent 中使用，主要存在以下耦合问题：

#### 问题一：共享配置/规范文件依赖（最严重）

各个 Skill 都通过相对路径 `../shared/` 引用共享文件：

| 依赖文件 | 被哪些 Skill 引用 | 类型 |
|---------|------------------|------|
| `shared/config/platform-mapping.md` | resource-search、resource-downloader | 配置数据 |
| `shared/config/platform-advantages.md` | resource-search | 配置数据 |
| `shared/schemas/resource-schema.md` | 所有业务 Skill | 规范文档 |
| `shared/schemas/quality-rubric.md` | resource-search | 规范文档 |
| `shared/schemas/error-codes.md` | resource-downloader、resource-platforms | 规范文档 |
| `shared/schemas/skill-contract.md` | 所有业务 Skill | 契约文档 |
| `shared/schemas/session-io-spec.md` | 所有业务 Skill | 契约文档 |
| `shared/logging-convention.md` | resource-platforms | 规范文档 |

**问题**：当 Skill 被独立安装后，`../shared/` 路径失效，无法找到这些文件。

#### 问题二：Python 共享模块依赖

`resource-platforms/scripts/shared/` 目录下的 Python 模块被多处引用：

| 模块 | 被引用位置 |
|------|-----------|
| `platform_base.py` | 所有平台脚本（bilibili、zhihu等） |
| `config_loader.py` | 所有平台脚本 |
| `dedup.py` | 所有平台脚本 + library-manager |
| `logger.py` | 所有平台脚本 |
| `utils.py` | 所有平台脚本 |
| `wbi_sign.py` | bilibili 平台脚本 |

**问题**：library-manager 跨目录引用 `../resource-platforms/scripts/shared/dedup.py`，独立安装后路径失效。

#### 问题三：跨 Skill 文档引用

| 引用方 | 被引用方 | 引用内容 |
|--------|---------|---------|
| resource-search | resource-platforms | 平台搜索技巧文档 |
| resource-downloader | resource-platforms | 下载方法文档 |
| library-manager | resource-platforms | dedup.py 去重引擎 |

**问题**：独立安装后，无法通过相对路径找到其他 Skill 的文档和脚本。

### 1.3 好的设计（保留并增强）

✅ **数据流转机制**：通过 session 文件系统传递数据（JSON 文件），这是非常好的解耦设计

✅ **统一接口规范**：各阶段输入输出有明确的契约定义

✅ **调度与执行分离**：调度层只负责路由，不关心具体实现

---

## 二、改造目标与原则

### 2.1 改造目标

1. **完全自包含**：每个 Skill 安装后可以独立运行，不依赖项目根目录的其他文件
2. **松耦合通信**：Skill 之间只通过文件系统传递数据，不直接调用对方的内部代码
3. **可独立安装**：每个 Skill 可以单独安装到 Agent 中使用
4. **可组合使用**：多个 Skill 可以组合在一起协同工作
5. **向后兼容**：改造后的 Skill 仍然可以在原项目结构中正常工作

### 2.2 设计原则

| 原则 | 说明 |
|------|------|
| **自包含原则** | 每个 Skill 打包所有依赖的配置、规范、工具代码 |
| **文件通信原则** | Skill 之间只通过约定好的文件格式通信，不直接调用 |
| **约定优于配置** | 统一的目录结构、文件命名、数据格式约定 |
| **渐进式改造** | 可以逐个 Skill 改造，不影响其他 Skill |
| **重复优于耦合** | 宁可有少量代码/文档重复，也要保证完全独立 |

---

## 三、具体改造方案

### 3.1 方案一：共享配置/规范内嵌化

#### 改造思路
将 `shared/` 目录下的配置和规范文件，复制到每个需要的 Skill 内部。

#### 目录结构调整

**改造前**：
```
learning-resource-suite/
├── shared/
│   ├── config/
│   │   ├── platform-mapping.md
│   │   └── platform-advantages.md
│   └── schemas/
│       ├── resource-schema.md
│       ├── quality-rubric.md
│       ├── error-codes.md
│       ├── skill-contract.md
│       └── session-io-spec.md
├── resource-search/
│   └── SKILL.md （引用 ../shared/...）
└── resource-downloader/
    └── SKILL.md （引用 ../shared/...）
```

**改造后**：
```
resource-search/
├── SKILL.md
└── references/
    ├── config/
    │   ├── platform-mapping.md      ← 复制过来
    │   └── platform-advantages.md   ← 复制过来
    └── schemas/
        ├── resource-schema.md       ← 复制过来
        ├── quality-rubric.md        ← 复制过来
        ├── skill-contract.md        ← 复制过来
        └── session-io-spec.md       ← 复制过来
```

#### SKILL.md 引用路径修改

**改造前**：
```markdown
- 平台优势图谱：`../shared/config/platform-advantages.md`
- 质量评估标准：`../shared/schemas/quality-rubric.md`
```

**改造后**：
```markdown
- 平台优势图谱：`./references/config/platform-advantages.md`
- 质量评估标准：`./references/schemas/quality-rubric.md`
```

#### 各 Skill 需要内嵌的文件清单

| Skill | 需要内嵌的文件 |
|-------|--------------|
| **learning-resource-flow** | schemas/skill-contract.md、schemas/session-io-spec.md、schemas/resource-schema.md |
| **resource-intent** | schemas/skill-contract.md、schemas/session-io-spec.md、schemas/resource-schema.md |
| **resource-search** | config/platform-mapping.md、config/platform-advantages.md、schemas/skill-contract.md、schemas/session-io-spec.md、schemas/resource-schema.md、schemas/quality-rubric.md |
| **resource-selector** | schemas/skill-contract.md、schemas/session-io-spec.md、schemas/resource-schema.md |
| **resource-downloader** | config/platform-mapping.md、schemas/skill-contract.md、schemas/session-io-spec.md、schemas/resource-schema.md、schemas/error-codes.md |
| **library-manager** | schemas/skill-contract.md、schemas/session-io-spec.md、schemas/resource-schema.md |
| **resource-platforms** | schemas/resource-schema.md、schemas/error-codes.md、config/platform-mapping.md |

---

### 3.2 方案二：Python 共享模块本地化

#### 改造思路
将 `resource-platforms/scripts/shared/` 下的 Python 模块，复制到每个需要的地方。

#### 平台脚本的改造

**改造前**：
```
resource-platforms/scripts/
├── shared/
│   ├── platform_base.py
│   ├── config_loader.py
│   ├── dedup.py
│   ├── logger.py
│   ├── utils.py
│   └── wbi_sign.py
├── bilibili/
│   ├── adapter.py
│   └── bilibili_search.py （from shared.platform_base import ...）
└── zhihu/
    ├── adapter.py
    └── zhihu_search.py （from shared.platform_base import ...）
```

**改造后（每个平台自包含）**：
```
resource-platforms/scripts/
├── bilibili/
│   ├── _shared/           ← 每个平台都有自己的 _shared 目录
│   │   ├── platform_base.py
│   │   ├── config_loader.py
│   │   ├── logger.py
│   │   ├── utils.py
│   │   └── wbi_sign.py
│   ├── adapter.py
│   └── bilibili_search.py （from ._shared.platform_base import ...）
└── zhihu/
    ├── _shared/           ← 每个平台都有自己的 _shared 目录
    │   ├── platform_base.py
    │   ├── config_loader.py
    │   ├── logger.py
    │   └── utils.py
    ├── adapter.py
    └── zhihu_search.py （from ._shared.platform_base import ...）
```

**优点**：每个平台完全独立，可以单独提取使用
**缺点**：有代码重复（但维护时可以从源头同步）

#### library-manager 的去重引擎

**改造前**：
- library-manager 引用 `../resource-platforms/scripts/shared/dedup.py`

**改造后**：
- 将 `dedup.py` 复制到 `library-manager/scripts/dedup.py`
- library-manager 使用自己内部的 dedup 模块

---

### 3.3 方案三：跨 Skill 调用机制标准化

#### 改造思路
resource-search 和 resource-downloader 不直接依赖 resource-platforms 的代码，而是通过**约定的接口**调用。

#### 平台 Skill 注册机制

**设计一个平台注册表文件**，放在工作区中：

```
.learning-resource-work/
└── registry/
    └── platforms.json   ← 已安装的平台 Skill 注册表
```

**platforms.json 格式**：
```json
{
  "version": "1.0",
  "platforms": {
    "bilibili": {
      "name": "B站",
      "status": "available",
      "priority": "P0",
      "resource_types": ["视频"],
      "search_script": "C:/path/to/resource-platforms/scripts/bilibili/bilibili_search.py",
      "download_script": "C:/path/to/resource-platforms/scripts/bilibili/bilibili_dl.py",
      "adapter_path": "C:/path/to/resource-platforms/scripts/bilibili/adapter.py"
    },
    "zhihu": {
      "name": "知乎",
      "status": "available",
      "priority": "P2",
      "resource_types": ["图文"],
      "search_script": "C:/path/to/resource-platforms/scripts/zhihu/zhihu_search.py",
      "download_script": null,
      "adapter_path": "C:/path/to/resource-platforms/scripts/zhihu/adapter.py"
    }
  }
}
```

#### 平台发现流程

1. **安装时注册**：每个平台 Skill 安装后，自动向注册表添加自己的信息
2. **运行时发现**：resource-search 和 resource-downloader 运行时读取注册表
3. **动态路由**：根据注册表中的可用平台进行路由调度

#### 平台优势图谱的处理

将平台优势图谱内嵌到 resource-search 内部，作为默认配置。
同时支持从注册表中读取各平台的能力信息，动态更新。

---

### 3.4 方案四：数据流转机制增强

#### 保留现有机制（已验证有效）

✅ Session 目录结构
✅ manifest.json 状态管理
✅ 阶段文件三层结构（_meta/_summary/data）
✅ 各阶段数据契约

#### 增强：工作区根目录发现机制

**问题**：各个 Skill 如何知道工作区在哪里？

**解决方案**：按以下优先级查找工作区根目录：

1. **环境变量**：`LRS_WORKSPACE` 指定的路径
2. **当前工作目录**：`./.learning-resource-work/`
3. **用户主目录**：`~/.learning-resource-work/`

**实现方式**：每个 Skill 内部都有一个统一的路径解析工具函数。

#### 增强：Skill 间通信协议

定义标准的 Skill 调用协议：

```
调用方传递 3 个参数：
1. session_dir  - 会话目录路径（绝对路径）
2. input_file   - 上游输入文件名
3. output_file  - 本阶段输出文件名

被调用方：
1. 读取 {session_dir}/{input_file} 的 data 部分
2. 执行业务逻辑
3. 将结果写入 {session_dir}/{output_file}
4. 返回 _summary 部分
```

这与当前的实现基本一致，只是需要标准化。

---

## 四、改造后的 Skill 标准结构

### 4.1 业务 Skill 标准结构

以 resource-search 为例：

```
resource-search/
├── SKILL.md                      # Skill 主文档
├── README.md                     # 使用说明
├── references/                   # 参考文档（内嵌）
│   ├── config/                   # 配置数据
│   │   ├── platform-mapping.md
│   │   └── platform-advantages.md
│   ├── schemas/                  # 规范契约
│   │   ├── resource-schema.md
│   │   ├── quality-rubric.md
│   │   ├── skill-contract.md
│   │   └── session-io-spec.md
│   └── 搜索执行规则.md            # Skill 内部规则
├── scripts/                      # 脚本工具（如有）
│   └── utils.py
└── tests/                        # 测试用例
    └── test_search.py
```

### 4.2 平台 Skill 标准结构

以 bilibili 平台为例：

```
platform-bilibili/
├── SKILL.md                      # Skill 主文档
├── README.md                     # 使用说明
├── references/                   # 参考文档
│   ├── schemas/
│   │   ├── resource-schema.md
│   │   └── error-codes.md
│   └── bilibili使用指南.md
├── scripts/                      # 平台脚本
│   ├── _shared/                  # 内嵌的共享模块
│   │   ├── platform_base.py
│   │   ├── config_loader.py
│   │   ├── logger.py
│   │   ├── utils.py
│   │   └── wbi_sign.py
│   ├── adapter.py                # 适配器（标准接口）
│   ├── bilibili_search.py        # 搜索脚本
│   └── bilibili_dl.py            # 下载脚本
└── tests/
    └── test_bilibili.py
```

### 4.3 主流程 Skill 标准结构

```
learning-resource-flow/
├── SKILL.md
├── README.md
├── references/
│   └── schemas/
│       ├── skill-contract.md
│       ├── session-io-spec.md
│       └── resource-schema.md
├── templates/                    # 模板文件
│   └── manifest.template.json
└── docs/
    └── workflow-guide.md
```

---

## 五、数据流转详细设计

### 5.1 完整数据流转图

```
用户需求
   │
   ▼
┌─────────────────────┐
│ learning-resource-  │
│ flow（总调度）       │
└─────────┬───────────┘
          │ 创建 session 目录
          │ 写 manifest.json
          ▼
┌─────────────────────┐
│ resource-intent     │  ← 读：无（第一个阶段）
│ （需求理解）         │  → 写：stage1_intent.json
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ resource-search     │  ← 读：stage1_intent.json 的 data
│ （搜索调度）         │  → 写：stage2_search.json
└─────────┬───────────┘
          │ 调用各平台 Skill
          │ （通过注册表发现）
          ▼
┌─────────────────────┐
│ resource-selector   │  ← 读：stage2_search.json 的 data
│ （用户选择）         │  → 写：stage3_select.json
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ resource-downloader │  ← 读：stage3_select.json 的 data
│ （下载调度）         │  → 写：stage4_download.json
└─────────┬───────────┘
          │ 调用各平台 Skill
          │ （通过注册表发现）
          ▼
┌─────────────────────┐
│ library-manager     │  ← 读：stage4_download.json 的 data
│ （归档管理）         │  → 写：stage5_archive.json
└─────────┬───────────┘
          │
          ▼
      最终结果
```

### 5.2 阶段文件格式标准

所有阶段文件统一采用三层结构：

```json
{
  "_meta": {
    "stage": 2,
    "session_id": "20260626-1441-math-grade3",
    "skill": "resource-search",
    "created_at": "2026-06-26T14:43:00+08:00",
    "input_from": "stage1_intent.json"
  },
  "_summary": {
    "total_count": 22,
    "platforms": ["bilibili", "ximalaya", "smartedu"],
    "quality_dist": {"S": 3, "A": 8, "B": 8, "C": 3}
  },
  "data": {
    "...": "完整业务数据，遵循各阶段契约"
  }
}
```

**各层职责**：
- `_meta`：元数据，用于调试和审计
- `_summary`：摘要，flow 调度决策用，≤10行
- `data`：完整业务数据，下游 Skill 处理用

### 5.3 manifest.json 标准

```json
{
  "session_id": "20260626-1441-math-grade3",
  "user_request": "帮我找三年级数学练习题",
  "created_at": "2026-06-26T14:41:00+08:00",
  "updated_at": "2026-06-26T14:45:00+08:00",
  "status": "in_progress",
  "current_stage": 3,
  "workspace_version": "1.0",
  "stages": {
    "stage1": {
      "status": "completed",
      "skill": "resource-intent",
      "output": "stage1_intent.json",
      "completed_at": "2026-06-26T14:42:00+08:00",
      "summary": "数学练习题/三年级/查询词3组"
    },
    "stage2": {
      "status": "completed",
      "skill": "resource-search",
      "output": "stage2_search.json",
      "completed_at": "2026-06-26T14:43:00+08:00",
      "summary": "22个候选/S3/A8/B8/C3"
    },
    "stage3": {
      "status": "in_progress",
      "skill": "resource-selector",
      "output": "stage3_select.json",
      "started_at": "2026-06-26T14:44:00+08:00",
      "summary": null
    },
    "stage4": {"status": "pending", "skill": "resource-downloader", "output": "stage4_download.json"},
    "stage5": {"status": "pending", "skill": "library-manager", "output": "stage5_archive.json"}
  }
}
```

---

## 六、实施步骤

### 6.1 第一阶段：准备工作（P0）

| 序号 | 任务 | 产出 |
|------|------|------|
| 1 | 整理 shared/ 目录下的所有文件清单 | 文件清单文档 |
| 2 | 梳理各 Skill 的依赖关系图 | 依赖关系图 |
| 3 | 制定文件复制和路径修改的规范 | 改造规范文档 |
| 4 | 设计平台注册表格式和注册机制 | 注册表规范 |

### 6.2 第二阶段：核心 Skill 改造（P0）

按依赖顺序逐个改造：

| 序号 | Skill | 改造内容 | 优先级 |
|------|-------|---------|--------|
| 1 | resource-intent | 内嵌 schemas 文档，修改引用路径 | P0 |
| 2 | resource-selector | 内嵌 schemas 文档，修改引用路径 | P0 |
| 3 | resource-search | 内嵌 config + schemas，平台发现机制 | P0 |
| 4 | resource-downloader | 内嵌 config + schemas，平台发现机制 | P0 |
| 5 | library-manager | 内嵌 schemas + dedup 模块 | P0 |
| 6 | learning-resource-flow | 内嵌 schemas，工作区发现机制 | P0 |

### 6.3 第三阶段：平台 Skill 改造（P1）

| 序号 | 平台 | 改造内容 | 优先级 |
|------|------|---------|--------|
| 1 | bilibili | _shared 模块本地化，独立打包 | P0 |
| 2 | smartedu | _shared 模块本地化，独立打包 | P1 |
| 3 | zhihu | _shared 模块本地化，独立打包 | P1 |
| 4 | douyin | _shared 模块本地化，独立打包 | P1 |
| 5 | weibo | _shared 模块本地化，独立打包 | P2 |
| 6 | ximalaya | _shared 模块本地化，独立打包 | P2 |
| 7 | open163 | _shared 模块本地化，独立打包 | P2 |

### 6.4 第四阶段：集成与验证（P1）

| 序号 | 任务 | 验证内容 |
|------|------|---------|
| 1 | 端到端流程测试 | 完整流程能否跑通 |
| 2 | 独立安装测试 | 每个 Skill 单独安装能否工作 |
| 3 | 组合测试 | 不同 Skill 组合能否协同工作 |
| 4 | 向后兼容测试 | 原项目结构下是否还能正常工作 |

### 6.5 第五阶段：文档与工具（P2）

| 序号 | 任务 | 产出 |
|------|------|------|
| 1 | 编写 Skill 开发规范 | Skill 开发指南 |
| 2 | 编写平台接入指南 | 新平台接入教程 |
| 3 | 开发同步工具 | 从 shared/ 同步到各 Skill 的脚本 |
| 4 | 编写安装部署文档 | 安装部署指南 |

---

## 七、关键技术细节

### 7.1 工作区发现机制

每个 Skill 内部实现一个统一的路径解析函数：

```python
def find_workspace() -> str:
    """
    按优先级查找工作区根目录：
    1. 环境变量 LRS_WORKSPACE
    2. 当前目录下的 .learning-resource-work
    3. 用户主目录下的 .learning-resource-work
    """
    import os
    
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

### 7.2 平台注册机制

每个平台 Skill 提供一个注册函数：

```python
def register_platform(registry_path: str = None):
    """
    将本平台注册到平台注册表
    """
    import json
    import os
    
    if registry_path is None:
        workspace = find_workspace()
        registry_path = os.path.join(workspace, 'registry', 'platforms.json')
    
    # 确保目录存在
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    
    # 读取现有注册表
    if os.path.exists(registry_path):
        with open(registry_path, 'r', encoding='utf-8') as f:
            registry = json.load(f)
    else:
        registry = {"version": "1.0", "platforms": {}}
    
    # 添加本平台信息
    platform_info = {
        "name": "B站",
        "status": "available",
        "priority": "P0",
        "resource_types": ["视频"],
        "search_script": os.path.abspath("bilibili_search.py"),
        "download_script": os.path.abspath("bilibili_dl.py"),
        "adapter_path": os.path.abspath("adapter.py"),
        "capabilities": {
            "search": True,
            "download": True,
            "subtitle": True,
            "quality_levels": ["S", "A", "B", "C"]
        }
    }
    
    registry["platforms"]["bilibili"] = platform_info
    
    # 写回注册表
    with open(registry_path, 'w', encoding='utf-8') as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)
    
    return True
```

### 7.3 配置同步工具

为了解决"代码重复但维护困难"的问题，开发一个同步脚本：

```bash
# 从 shared/ 源目录同步到所有 Skill 的 references/ 目录
python scripts/sync-shared.py --source shared/ --targets "resource-search/references,resource-downloader/references,..."
```

这样维护时只需要修改源文件，然后一键同步到各个 Skill。

---

## 八、风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|---------|
| 代码/文档重复导致维护困难 | 中 | 开发同步工具，源文件修改后一键同步 |
| 平台注册表机制复杂 | 中 | 提供简化版：默认内置常用平台，注册表作为扩展 |
| 改造周期长 | 中 | 渐进式改造，逐个 Skill 进行，不影响现有功能 |
| 向后兼容性问题 | 高 | 保留原路径引用作为 fallback，双路径支持 |
| 独立 Skill 体积变大 | 低 | 可接受，换取独立性 |

---

## 九、验证标准

### 9.1 独立安装验证

每个 Skill 满足以下条件即为改造完成：

- ✅ 可以单独打包成 zip 文件
- ✅ 解压后可以直接使用，不需要其他文件
- ✅ SKILL.md 中的所有引用路径都有效
- ✅ 所有脚本都能正常运行（依赖都在内部）

### 9.2 协同工作验证

多个 Skill 组合使用时：

- ✅ 可以通过 session 文件传递数据
- ✅ 上游 Skill 的输出可以被下游 Skill 正确读取
- ✅ manifest.json 可以正确记录各阶段状态
- ✅ 完整流程可以端到端跑通

### 9.3 向后兼容验证

- ✅ 原项目结构下，所有 Skill 仍然正常工作
- ✅ 原有的相对路径引用仍然有效（作为 fallback）

---

## 十、总结

### 10.1 改造收益

1. **可独立部署**：每个 Skill 可以单独安装到 Agent 中
2. **松耦合架构**：Skill 之间只通过文件通信，不直接依赖
3. **可组合使用**：可以根据需要选择部分 Skill 组合使用
4. **易于扩展**：新增平台 Skill 只需注册，不需要修改调度器
5. **易于维护**：每个 Skill 职责清晰，边界明确

### 10.2 核心思想

> **通过文件系统实现 Skill 间的解耦通信，每个 Skill 自包含所有依赖，通过约定好的格式交换数据。**

这与 Unix 哲学一致：
- 每个程序只做好一件事
- 程序之间通过文本流通信
- 每个程序的输入输出都有统一格式

### 10.3 下一步行动

1. 先从 resource-intent 和 resource-selector 开始改造（依赖最少）
2. 验证改造后的效果
3. 逐步推广到其他 Skill
4. 最后处理平台 Skill

---

*文档版本：v1.0 | 编写日期：2026-06-27*
