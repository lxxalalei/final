# 儿童学习资源 Skill 套件

> 一套面向儿童学习资源获取与归档的 AI Skill 工具集 —— 从需求理解、多平台搜索、候选选择、下载获取到本地归档的完整闭环。

---

## 三层架构概览

```
┌─────────────────────────────────────────────────────┐
│          流程编排层 (Orchestration Layer)              │
│     learning-resource-flow · 总调度入口 · 6阶段闭环    │
└──────────────────────┬──────────────────────────────┘
                       │ 调度
         ┌─────────────┼─────────────────────┐
         ▼             ▼                     ▼
┌──────────────┬───────────────┬──────────────────────┐
│  业务能力层 (Business Capability Layer)                │
│                      │                                 │
│  resource-intent   resource-search   resource-selector │
│  需求理解           全域搜索调度        候选展示与选择    │
│                      │                                 │
│  resource-downloader   library-manager                 │
│  下载调度              资料库归档管理                    │
└──────────────────────┬──────────────────────────────┘
                       │ 调度
         ┌──────┬──────┼──────┬──────┐
         ▼      ▼      ▼      ▼      ▼
┌──────────────────────────────────────────────────────┐
│             平台执行层 (Platform Execution Layer)        │
│                                                        │
│  bilibili   smartedu   zhihu   douyin   weibo         │
│  B站视频    国家中小学   知乎    抖音     微博            │
│             智慧教育平台                                  │
└──────────────────────────────────────────────────────┘
```

### 6 阶段工作流

| 阶段 | 负责Skill | 说明 |
|------|----------|------|
| ① 需求理解 | resource-intent | 自然语言 → 结构化多维度查询指令组 |
| ② 搜索召回 | resource-search | 平台路由 + 多端搜索 + 质量筛选 |
| ③ 候选选择 | resource-selector | 结构化展示 + 用户选定 |
| ④ 下载获取 | resource-downloader | 分级调度 + 重试降级 + 错误处理 |
| ⑤ 归档入库 | library-manager | 本地资料库 + 索引维护 + 检索复用 |
| ⑥ 结果反馈 | learning-resource-flow | 汇总报告 + 下一步建议 |

---

## 目录结构

```
learning-resource-suite/
│
├── learning-resource-flow/          # 🔵 流程编排层 — 总调度入口
│   ├── SKILL.md
│   └── references/
│       └── workflow-guide.md         # 6阶段工作流指南
│
├── resource-intent/                 # 🟢 业务能力层 — 需求理解
│   ├── SKILL.md
│   └── references/
│       ├── 主题扩展词表.md
│       ├── 澄清话术库.md
│       └── 需求拆解规则.md
│
├── resource-search/                 # 🟢 业务能力层 — 搜索调度
│   ├── SKILL.md
│   └── references/
│       ├── 搜索执行规则.md
│       └── 优质站点白名单.md
│
├── resource-selector/               # 🟢 业务能力层 — 候选展示
│   ├── SKILL.md
│   └── references/
│       ├── display-templates.md
│       └── quality-rubric.md
│
├── resource-downloader/             # 🟢 业务能力层 — 下载调度
│   ├── SKILL.md
│   └── references/
│       ├── download-methods.md
│       └── troubleshooting.md
│
├── library-manager/                 # 🟢 业务能力层 — 资料库管理
│   ├── SKILL.md
│   └── references/
│       └── library-structure.md
│
├── resource-platforms/              # 🟠 平台执行层 — 所有平台 Skill 的统一 Skill 包
│   ├── SKILL.md                      # 平台总入口（路由 + 共享规范）
│   ├── references/                   # 各平台 SKILL 说明 + 架构文档
│   │   ├── bilibili.md               # B站（搜索+下载+字幕+WBI签名）
│   │   ├── smartedu.md               # 国家中小学智慧教育平台
│   │   ├── zhihu.md                  # 知乎（搜索+Markdown导出）
│   │   ├── douyin.md                 # 抖音（f2引擎搜索+无水印下载）
│   │   ├── weibo.md                  # 微博（ajax搜索+用户图文下载）
│   │   ├── ximalaya.md               # 喜马拉雅（搜索）
│   │   ├── open163.md                # 网易公开课（搜索）
│   │   ├── architecture.md           # smartedu 架构说明
│   │   ├── smartedu-resource-schema.md
│   │   └── test-cases.md
│   └── scripts/                      # 各平台脚本 + 共享代码
│       ├── bilibili/                 # adapter + 下载脚本
│       ├── smartedu/
│       ├── zhihu/
│       ├── douyin/
│       ├── weibo/
│       ├── ximalaya/
│       ├── open163/
│       └── shared/                   # 共享 Python 模块（已从 shared/ 迁入）
│           ├── __init__.py
│           ├── platform_base.py      # 平台 Skill 基类（输出标准化层）
│           ├── utils.py              # 通用工具函数
│           ├── logger.py             # 统一日志模块
│           ├── wbi_sign.py           # B站 WBI 签名工具
│           ├── config_loader.py      # 统一配置加载器
│           └── dedup.py              # 跨平台内容级去重引擎
│
├── shared/                          # ⚙️ 共享规范与配置（.md 文档，无 .py）
│   ├── logging-convention.md         # 日志规范
│   ├── schemas/                      # 数据契约与规范
│   │   ├── resource-schema.md
│   │   ├── error-codes.md
│   │   ├── skill-contract.md
│   │   ├── platform-search-contract.md
│   │   ├── platform-download-contract.md
│   │   └── quality-rubric.md          # 全系统统一质量评估标准（权威）
│   └── config/                       # 共享配置
│       ├── platform-mapping.md
│       └── platform-advantages.md
│
├── _templates/                      # 📋 标准模板
│   └── platform-skill-template.md    # 新建平台 Skill 的标准模板
│
├── .gitignore
└── 系统架构说明.md
```

---

## 共享规范索引（`shared/`）

| 文件 | 说明 |
|------|------|
| `schemas/resource-schema.md` | 资源元数据规范 —— 定义学习资源统一数据格式，确保各 Skill 互通 |
| `schemas/error-codes.md` | 统一错误码体系 —— 7大类前缀（NETWORK_/ANTI_CRAWL_/AUTH_/CONTENT_/PARSE_/DOWNLOAD_/SYSTEM_） |
| `schemas/skill-contract.md` | 跨 Skill 上下文传递契约 —— 定义各 Skill 间输入输出字段规范 |
| `schemas/platform-search-contract.md` | 平台搜索接口契约 —— search 调度器 ↔ platform skill 搜索接口 |
| `schemas/platform-download-contract.md` | 平台下载接口契约 —— downloader 调度器 ↔ platform skill 下载接口 |
| `config/platform-mapping.md` | 平台-Skill 映射表 —— 路由判断的核心依据 |
| `config/platform-advantages.md` | 平台优势图谱 —— 全系统权威配置，指导平台路由选择 |
| `platform_base.py` | 平台 Skill 基类（CLIBasedPlatformSkill）—— 已迁至 `resource-platforms/scripts/shared/` |
| `utils.py` | 通用工具函数 —— 已迁至 `resource-platforms/scripts/shared/` |
| `logger.py` | 统一日志模块 —— 已迁至 `resource-platforms/scripts/shared/` |
| `wbi_sign.py` | B站 WBI 签名工具 —— 已迁至 `resource-platforms/scripts/shared/` |
| `config_loader.py` | 统一配置加载器 —— 已迁至 `resource-platforms/scripts/shared/` |
| `dedup.py` | 跨平台内容级去重引擎 —— 已迁至 `resource-platforms/scripts/shared/` |

---

## Skill 清单

### 业务 Skill（6个）

| Skill | 层级 | 职责 |
|-------|------|------|
| `learning-resource-flow` | 流程编排层 | 总调度入口，协调6阶段闭环工作流 |
| `resource-intent` | 业务能力层 | 需求理解：自然语言 → 结构化多维度查询指令组 |
| `resource-search` | 业务能力层 | 搜索调度：平台路由 + 多端搜索 + 质量筛选 |
| `resource-selector` | 业务能力层 | 候选展示：结构化展示 + 用户选定 + 输出列表 |
| `resource-downloader` | 业务能力层 | 下载调度：分级调度 + 重试降级 + 错误处理 |
| `library-manager` | 业务能力层 | 资料库管理：归档 + 索引维护 + 检索复用 |

### 平台 Skill（7个，合并为 1 个 Skill 包）

> 以下 7 个平台已合并为 `resource-platforms` 一个 Skill 包，统一管理。

| 平台 | 优先级 | 能力 | 说明 |
|------|--------|------|------|
| `bilibili` | P0 | 搜索 + 下载 + 字幕 | B站视频，集成 bilibili-api-python，WBI签名鉴权 |
| `ximalaya` | P0 | 搜索（下载待实现） | 喜马拉雅音频，OAuth 开放平台 API |
| `smartedu` | P1 | 搜索 + 下载 | 国家中小学智慧教育平台，支持 PDF/m3u8/音频/图片 |
| `zhihu` | P2 | 搜索 + 内容导出 | 知乎问答与文章，导出 Markdown |
| `douyin` | P2 | 搜索 + 无水印下载 | 抖音短视频，f2引擎驱动 |
| `weibo` | P2 | 搜索 + 用户图文下载 | 微博 ajax搜索 + 用户图文 |
| `open163` | P2 | 搜索（下载待实现） | 网易公开课，HTML 解析 |

---

## 快速开始

```bash
# 1️⃣ 确保依赖就绪
#    Python 3.10+，各平台 scripts/ 下的依赖按需安装

# 2️⃣ 理解架构
#    先读 learning-resource-flow/SKILL.md 了解6阶段工作流
#    再读 shared/schemas/skill-contract.md 了解跨Skill数据契约

# 3️⃣ 按需使用
#    用户交互：直接通过 learning-resource-flow 总入口发起请求
#    单 Skill 调用：可独立调用 resource-search / resource-downloader 等
#    新增平台：复制 _templates/platform-skill-template.md，实现标准接口
```

---

## 关键约定

- **download_status** 统一三态：`success` / `degraded` / `failed`
- **降级计数** 字段用 `degraded_count`，降级等级用字符串 `"Level 0"` ~ `"Level 3"`
- **错误码** 必须使用 `error-codes.md` 中的标准命名（如 `CONTENT_PREMIUM_ONLY`、`CONTENT_NOT_FOUND`）
- **平台 Skill 路径** 统一写 `resource-platforms/scripts/xxx`（平台脚本）或 `resource-platforms/references/xxx.md`（平台 SKILL 说明），不写 `platforms/xxx`
- **平台优势图谱** 全系统权威位置为 `shared/config/platform-advantages.md`
- **新建平台 Skill** 一律基于 `_templates/platform-skill-template.md`，必须含搜索/下载/反爬/登录四大模块
