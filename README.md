# 儿童学习资源 Skill 套件 · 架构说明书

> **版本**：v10.1（精简版·6 阶段流程）
> **面向**：3-12 岁儿童学习资源的 AI Skill 工具集

从家长一句模糊的自然语言需求出发，经过**需求理解 → 搜索策略 → 平台执行 → 质量筛选 → 下载获取 → 归档入库**六个阶段，完成"从听懂到拿到再到管好"的完整闭环。覆盖 B 站、国家中小学智慧教育平台、知乎、抖音、微博、喜马拉雅、网易公开课共 7 大内容平台。

---

## 目录

- [一、整体架构](#一整体架构)
- [二、Skill 清单与职责](#二skill-清单与职责)
- [三、数据流转机制](#三数据流转机制)
- [四、各 Skill 详细说明](#四各-skill-详细说明)
  - [4.1 learning-resource-flow（总调度入口）](#41-learning-resource-flow总调度入口)
  - [4.2 resource-intent（需求理解 · 阶段一）](#42-resource-intent需求理解--阶段一)
  - [4.3 resource-search（搜索策略 · 阶段二）](#43-resource-search搜索策略--阶段二)
  - [4.4 resource-platforms（搜索执行 · 阶段三）](#44-resource-platforms搜索执行--阶段三)
  - [4.5 resource-selector（质量筛选与选择 · 阶段四）](#45-resource-selector质量筛选与选择--阶段四)
  - [4.6 resource-downloader（下载调度 · 阶段五）](#46-resource-downloader下载调度--阶段五)
  - [4.7 library-manager（归档管理 · 阶段六）](#47-library-manager归档管理--阶段六)
- [五、已接入平台](#五已接入平台)
- [六、项目目录结构](#六项目目录结构)
- [七、配置系统](#七配置系统)
- [八、开发工具](#八开发工具)

---

## 一、整体架构

### 设计原则

| 原则 | 说明 |
|------|------|
| **每个 Skill 自包含** | 安装后独立可用，不依赖其他 Skill 的目录文件 |
| **文件驱动数据流转** | 各阶段输出通过 JSON 文件持久化到会话目录，不堆积在上下文中 |
| **三层分离** | 总调度（flow）、业务能力层（intent/search/selector/downloader/library）、平台执行层（platforms） |
| **内联优先** | 必要的 schema/规范直接内联到 SKILL.md；只有需要按需查阅时才放 references/ |
| **儿童友好** | 默认只保留中文、免费、适龄的内容 |

### 六阶段流程总览

```
用户自然语言需求
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    learning-resource-flow（总调度）            │
│                  创建会话 → 依次调度 6 个阶段                   │
└──────────────────────────┬───────────────────────────────────┘
                           │
     ┌─────────────────────┼─────────────────────────────┐
     ▼                     ▼                             ▼
 阶段一                 阶段二          阶段三          阶段四        阶段五        阶段六
 resource-intent    resource-search  resource-       resource-     resource-    library-
                   │                 platforms       selector      downloader   manager
 需求理解            搜索策略          搜索执行         质量筛选       下载调度      归档管理
 │                  │                 │               │             │            │
 ▼                  ▼                 ▼               ▼             ▼            ▼
stage1_           stage2_           stage3_         stage4_       stage5_      stage6_
intent.json       search_plan.json  candidates.json select.json   download.json archive.json
```

每个阶段的输出都是一个 JSON 文件，写入会话目录 `.learning-resource-work/sessions/{session_id}/`，下一阶段读取上一阶段的 `data` 部分作为输入。

### 分层职责

```
┌─────────────────────────────────────────────────────────┐
│  调度层     learning-resource-flow                        │
│            创建会话、阶段编排、上下文管理、异常处理            │
├─────────────────────────────────────────────────────────┤
│  业务能力层  resource-intent   → 需求翻译为结构化描述        │
│            resource-search   → 多维度查询生成+平台选择       │
│            resource-selector → 五维质量评估+过滤+用户选择    │
│            resource-downloader → 下载路由+重试+四级降级       │
│            library-manager   → 归档+索引+去重+检索          │
├─────────────────────────────────────────────────────────┤
│  平台执行层  resource-platforms                           │
│            7 个平台的 Python 搜索/下载脚本 + 跨平台去重引擎   │
└─────────────────────────────────────────────────────────┘
```

---

## 二、Skill 清单与职责

| Skill | 层 | 阶段 | 核心职责 |
|-------|-----|------|---------|
| `learning-resource-flow` | 调度层 | 全流程 | 总入口，创建会话并依次调度 6 个阶段，管理上下文和异常 |
| `resource-intent` | 业务能力层 | 阶段一 | 把家长的自然语言需求翻译成结构化需求描述（最多 2 轮澄清） |
| `resource-search` | 业务能力层 | 阶段二 | 五维拆解生成差异化查询，选择最佳平台组合，优化各平台关键词 |
| `resource-platforms` | 平台执行层 | 阶段三 | 调度 7 个平台脚本执行搜索，汇总结果并跨平台去重 |
| `resource-selector` | 业务能力层 | 阶段四 | 五维体系评估打分（S/A/B/C），过滤低质量内容，展示候选供用户选择 |
| `resource-downloader` | 业务能力层 | 阶段五 | 平台路由+通用兜底，重试策略，四级降级（完整→预览→摘要→链接） |
| `library-manager` | 业务能力层 | 阶段六 | 按学科/年龄/主题归档，维护索引，跨平台内容级去重，检索复用 |

---

## 三、数据流转机制

### 会话目录结构

每次用户请求创建一个会话目录：

```
.learning-resource-work/sessions/{session_id}/
├── manifest.json              ← flow 创建并维护（状态索引）
├── stage1_intent.json         ← resource-intent 写入
├── stage2_search_plan.json    ← resource-search 写入
├── stage3_candidates.json     ← resource-platforms 写入
├── stage4_select.json         ← resource-selector 写入
├── stage5_download.json       ← resource-downloader 写入
├── stage6_archive.json        ← library-manager 写入
└── downloads/                 ← 下载的文件临时存放
```

- **session_id** 命名：`{日期}-{时间}-{主题英文缩写}`，如 `20260626-1441-math-grade3`
- 所有会话平铺在 `sessions/` 下，不按对话分组

### 文件三层结构

每个阶段文件统一采用三层 JSON 结构：

```
┌─────────────────────────────────────────────────────────────┐
│  _meta     元数据（阶段号 / Skill 名 / 时间 / 上游来源）         │
├─────────────────────────────────────────────────────────────┤
│  _summary  摘要（≤10 个字段，flow 只读这个做调度决策）           │
├─────────────────────────────────────────────────────────────┤
│  data      完整业务数据（下游 Skill 读这个执行）                │
└─────────────────────────────────────────────────────────────┘
```

- **flow** 只读每个文件的 `_summary`，不读 `data`
- **下游 Skill** 读上游文件的 `data`，写入自己的 `data`
- **上下文** 中只保留 session_id + 当前阶段 + 各阶段 summary

### 数据累积管道

数据沿管道单向流动，每个阶段只增不删：

```
stage1 (intent)     data: summary, core_topic, target_age, difficulty,
  │                       format_preferences, search_mode, assumptions[]
  │
  ▼ +搜索计划
stage2 (search)     data: search_tasks[]（各平台的查询任务列表）
  │
  ▼ +搜索结果
stage3 (platforms)  data: resources[]（去重后的资源列表）
  │                 resources[]: resource_id, title, type, platform,
  │                              source_url, platform_quality_score,
  │                              download_feasibility, (+ 可选元数据)
  │
  ▼ 筛选（用户选择，不增字段）
stage4 (select)     data: selected resources[]（用户选中的子集）
  │                 resources[] 新增: quality_level, quality_score
  │
  ▼ +下载结果
stage5 (download)   data: resources[]
  │                 resources[] 新增: download_status, degraded_level,
  │                              file_path, file_size, fetch_time,
  │                              fetch_method, error_code（失败时）
  │
  ▼ +归档信息
stage6 (archive)    data: resources[]
                    resources[] 新增: library_path, archive_time,
                                     dedup_status
```

到 stage6 结束时，每个资源对象累积了从 intent 到 archive 的完整生命周期数据，flow 据此生成最终汇总报告。

### 读写规则

- **读**：只读取上游阶段文件的 `data` 部分，不修改上游文件
- **写**：只写自己的阶段文件，完整覆盖写入
- **不碰**：不修改其他阶段的文件，不修改 manifest.json（flow 负责）

---

## 四、各 Skill 详细说明

### 4.1 learning-resource-flow（总调度入口）

**定位**：整个套件的唯一入口，不直接执行搜索或下载，而是调度 6 个 Skill 协同完成任务。

**核心职责**：
1. **创建会话**：生成 session_id，创建目录结构，写入 manifest.json
2. **阶段调度**：依次执行阶段一→六，每个阶段 skill 自行读取 manifest.json 获取路径和文件名信息
3. **上下文管理**：只读各阶段 `_summary`，不把完整 data 拉入上下文
4. **需求路由**：判断用户意图——新搜索、继续上次、查资料库等
5. **异常处理**：用户取消、结果太少、下载全失败等场景的友好处理
6. **最终汇总**：阶段六完成后生成完整报告

**调度流程**：

```
收到新需求
    │
    ▼
创建会话 → manifest.json
    │
    ▼
阶段一：intent → 读 summary → 向用户确认需求 → 用户确认
    │
    ▼
阶段二：search → 读 summary → 展示搜索计划 → 用户确认
    │
    ▼
阶段三：platforms → 读 summary → has_results? 
    │                                        ├─ 否 → 询问是否放宽条件
    │                                        └─ 是 ↓
    ▼
阶段四：selector → 读 summary → 用户选择资源
    │                                ├─ 未选 → 结束
    │                                └─ 选了 ↓
    ▼
阶段五：downloader → 读 summary → 有成功/降级? 
    │                                  ├─ 全失败 → 告知原因+换资源
    │                                  └─ 有结果 ↓
    ▼
阶段六：library → 读 summary → 展示最终汇总 → 完成
```

**参考资料**：
- `references/workflow-guide.md` — 详细工作流指南与异常处理策略
- `references/output-templates.md` — 结构化输出模板规范

---

### 4.2 resource-intent（需求理解 · 阶段一）

**定位**：需求翻译器——把家长模糊、口语化的需求，翻译成结构化的需求描述。不负责生成搜索查询词（那是 search 的职责）。

**输入**：用户的自然语言需求文本（无上游文件）
**输出**：`stage1_intent.json`

**执行流程**：

```
第一步：判断需求清晰度
    ├─ 足够具体（主题+年龄+类型 ≥2 项）→ 直接抽取
    └─ 不够具体 → 第二步

第二步：需求澄清（最多 2 轮）
    ├─ 第 1 轮：开放式问题引导核心主题
    └─ 第 2 轮（可选）：补充最关键的一个信息

第三步：语义理解与槽位抽取
    → core_topic, target_age, grade_level, difficulty,
      format_preferences, source_preference, use_scenario

第四步：默认补全
    → 未明确的维度按通用最优策略补全，假设记入 assumptions[]

第五步：写入 stage1_intent.json
```

**输出 data 核心字段**：

| 字段 | 必选 | 说明 |
|------|:----:|------|
| `core_topic` | ✅ | 核心主题（如"三年级数学"） |
| `target_age` | ✅ | 目标年龄范围（如"8-9岁"） |
| `grade_level` | ⚠️ | 年级 |
| `difficulty` | ✅ | 难度偏好（入门/进阶/系统） |
| `format_preferences` | ✅ | 资源形态偏好（视频/音频/文档/图文） |
| `source_preference` | ✅ | 来源偏好（不限/官方优先/视频平台优先） |
| `search_mode` | ✅ | 搜索模式（standard/exhaustive） |
| `assumptions` | ⚠️ | 默认假设清单（必须告知用户） |

**参考资料**：
- `references/requirement-decomposition-rules.md` — 完整执行手册（判断标准、槽位定义、补全规则）
- `references/clarification-phrases.md` — 各场景澄清话术参考

---

### 4.3 resource-search（搜索策略 · 阶段二）

**定位**：搜索的军师——不负责实际去搜，而是负责"想清楚怎么搜效果最好"。拿到需求后生成多角度查询词，判断什么需求该去哪个平台、每个平台该搜什么、搜多少。

**输入**：`stage1_intent.json` 的 data
**输出**：`stage2_search_plan.json`

**执行流程**：

```
第一步：查询指令生成（五维拆解法）
    ├─ 核心主题维度 → 精确查询
    ├─ 资源形态维度 → 按视频/音频/文档/图文分别生成
    ├─ 受众难度维度 → 结合年龄+难度
    ├─ 来源倾向维度 → 官方优先/视频优先定向
    └─ 使用场景维度 → 场景化查询
    → 生成 ≥10 个差异化查询，分 4 级：core/official/format/longtail

第二步：需求分析与平台选择
    ├─ 用户指定优先（官方优先→smartedu，视频优先→bilibili）
    ├─ 主题匹配（科普→bilibili+zhihu，学科→smartedu，古诗→bilibili+ximalaya）
    └─ 形态补充（视频→bilibili，音频→ximalaya，文档→smartedu，图文→zhihu+weibo）
    → 标准模式 3-5 个平台，穷尽模式 5-7 个平台

第三步：各平台关键词优化
    → 同一主题不同平台搜法不同（B站加"动画/讲解"，知乎加"推荐/经验"等）
    → 年龄适配（低幼加"启蒙/宝宝"，高年级加"进阶/提高"）

第四步：生成搜索任务清单
    → 每个平台的任务含：platform_id, priority, queries[], target_count

第五步：写入 stage2_search_plan.json
```

**输出 data 核心字段**：

| 字段 | 必选 | 说明 |
|------|:----:|------|
| `search_tasks` | ✅ | 各平台搜索任务列表 |
| `search_tasks[].platform_id` | ✅ | 平台标识（如 bilibili） |
| `search_tasks[].priority` | ✅ | 优先级（P0/P1/P2） |
| `search_tasks[].queries` | ✅ | 该平台的查询列表（含 text/tier/format_hint） |
| `search_tasks[].target_count` | ✅ | 预期召回数量 |
| `intent_data` | ✅ | 透传上游 intent 的完整 data |
| `core_topic` | ✅ | 透传核心主题 |
| `search_mode` | ✅ | 搜索模式 |

**参考资料**：
- `references/主题扩展词表.md` — 各主题的扩展关键词
- `references/guides/query-generation.md` — 五维拆解完整指南
- `references/config/platform-advantages.md` — 平台优势图谱
- `references/config/platform-mapping.md` — 平台能力映射
- `references/guides/search-strategy.md` — 完整搜索策略指南

---

### 4.4 resource-platforms（搜索执行 · 阶段三）

**定位**：搜索的执行者——拿到搜索任务后，实际去各个平台搜，把结果收回来、去重、标准化，原样输出。**不做质量评估、不做过滤精选**，把判断权交给下游 selector。

**输入**：`stage2_search_plan.json` 的 data
**输出**：`stage3_candidates.json`

**执行流程**：

```
第一步：确认可用平台与脚本路径
    → 检查 scripts/{platform_id}/ 是否存在
    → 不可用的平台跳过并记录

第二步：按优先级调度各平台搜索
    → P0 平台优先 → P1 → P2
    → 每个平台调用 adapter.py 统一接口
    → 结果标准化为统一资源元数据格式
    → 每条结果附带 platform_quality_score（平台自评粗筛分）

第三步：跨平台去重（三级策略）
    ├─ resource_id 完全一致（最强信号）
    ├─ URL 结构化去重（去除追踪参数后比较）
    └─ 标题相似度去重（编辑距离+TF-IDF，阈值 0.85）
    → 保留 platform_quality_score 最高的版本

第四步：写入 stage3_candidates.json（不做过滤，原样输出）
```

**输出 data 核心字段**：

| 字段 | 必选 | 说明 |
|------|:----:|------|
| `resources` | ✅ | 去重后的资源列表（每个含完整元数据） |
| `resources[].resource_id` | ✅ | 唯一标识（格式：`平台名:平台内ID`） |
| `resources[].platform_quality_score` | ✅ | 平台自评原始分（0-100，粗筛信号） |
| `resources[].download_feasibility` | ✅ | 下载可行性（高/中/低） |
| `intent_data` | ✅ | 透传 intent data（selector 评估需要） |
| `total_count` | ✅ | 去重后总数 |

**脚本结构**：

```
resource-platforms/scripts/
├── shared/              ← 共享工具模块
│   ├── platform_base.py ← 平台基类（统一接口）
│   ├── dedup.py         ← 跨平台去重引擎（DedupEngine）
│   ├── config_loader.py ← 配置加载器
│   ├── logger.py        ← 日志模块
│   ├── utils.py         ← 通用工具
│   └── wbi_sign.py      ← B站 WBI 签名
├── bilibili/            ← B站适配器+下载
├── smartedu/            ← 国家中小学智慧教育平台
├── zhihu/               ← 知乎
├── douyin/              ← 抖音
├── weibo/               ← 微博
├── ximalaya/            ← 喜马拉雅
└── open163/             ← 网易公开课
```

**参考资料**：
- `references/schemas/resource-schema.md` — 统一资源元数据格式
- `references/schemas/platform-search-contract.md` — 平台搜索接口规范
- `references/platforms/{platform_id}.md` — 各平台详细文档（7 个）
- `references/schemas/error-codes.md` — 统一错误码体系

---

### 4.5 resource-selector（质量筛选与选择 · 阶段四）

**定位**：质量把关者+用户选择界面——拿到 platforms 返回的去重结果后，按五维体系评估打分，过滤低质量内容，精选排序后展示给用户选择。

**输入**：`stage3_candidates.json` 的 data
**输出**：`stage4_select.json`

**执行流程**：

```
第一步：质量评估与分级（五维评分体系）
    → 平台返回的 platform_quality_score 只是粗筛信号，必须重新评估
    ├─ 内容质量与完整性（25%）
    ├─ 适龄匹配度（25%）
    ├─ 权威可信度（20%）
    ├─ 可获取性（20%）
    └─ 安全与体验（10%）
    → 前置门槛：主题不相关/安全风险 → 直接淘汰
    → 分级：S(≥90) / A(75-89) / B(60-74) / C(<60)

第二步：低质量过滤与精选
    → 移除 C 级（候选不足 10 个时保留）
    → 移除非中文/广告/付费无预览/境外内容
    → 标准模式 20-25 个，穷尽模式 30-40 个

第三步：结构化展示
    → 按平台分类，质量优先排序
    → 每条显示：质量等级、平台、下载难度、播放量、推荐理由

第四步：用户选择与确认
    → 支持编号/全部/按类型/按质量/按平台/按难度选择
    → 选择后确认再下载，防误操作

第五步：写入 stage4_select.json（保留上游全部字段 + 新增评估字段）
```

**输出 data 核心字段**：

| 字段 | 必选 | 说明 |
|------|:----:|------|
| `resources` | ✅ | 用户选中的资源列表 |
| `resources[].quality_level` | ✅ | 质量等级（S/A/B/C） |
| `resources[].quality_score` | ✅ | 综合得分（0-100） |
| `selection_mode` | ✅ | 选择方式（manual/all/by_type/by_quality） |

**参考资料**：
- `references/quality-rubric.md` — 五维质量评估标准（S/A/B/C 评分体系）
- `references/display-templates.md` — 候选展示模板详细说明

---

### 4.6 resource-downloader（下载调度 · 阶段五）

**定位**：下载任务的调度与管理——不直接执行下载，而是根据资源的平台和类型，路由到对应的平台 Skill 或通用下载工具，并管理重试和降级。

**输入**：`stage4_select.json` 的 data
**输出**：`stage5_download.json`（下载文件存入 `{session_dir}/downloads/`）

**执行流程**：

```
第一步：平台路由判断
    → 有对应 platform skill？→ 调用平台脚本下载
    → 否 → 视频音频？→ yt-dlp 通用下载
    → 否 → 直链文件？→ wget/curl
    → 否 → 网页图文？→ 正文提取转 MD/PDF
    → 否 → 降级为保存链接+摘要

第二步：批量调度（按平台分组，并发 2-3 个）

第三步：进度跟踪（等待→下载→成功/失败/降级）

第四步：失败重试（按错误类型决定重试次数）
    ├─ 网络超时 → 重试 3 次（指数退避）
    ├─ 频率限制 → 重试 2 次（线性退避）
    ├─ 付费/DRM/已删除 → 不重试，直接降级
    └─ 累计 3 次失败才降级

第五步：四级降级体系
    Level 0 完整版本（原始文件）
        ↓ 失败
    Level 1 预览版本（低清晰度/部分章节）
        ↓ 失败
    Level 2 核心摘要（目录、简介、要点）
        ↓ 失败
    Level 3 来源链接（标题+链接+简介）

第六步：结果汇总 → 写入 stage5_download.json
```

**输出 data 核心字段**：

| 字段 | 必选 | 说明 |
|------|:----:|------|
| `resources[].download_status` | ✅ | success / degraded / failed |
| `resources[].degraded_level` | ✅ | Level 0-3 |
| `resources[].file_path` | ⚠️ | 本地路径（成功时） |
| `resources[].error_code` | ⚠️ | 错误码（失败时） |
| `resources[].degraded_content` | ⚠️ | 降级内容说明（降级时） |
| `resources[].alternative_recommendations` | ⚠️ | 替代推荐（失败时） |

**参考资料**：
- `references/error-codes.md` — 完整错误码体系（7 类前缀 + 30+ 错误码）
- `references/download-methods.md` — 通用下载工具使用说明
- `references/troubleshooting.md` — 常见下载问题排查

---

### 4.7 library-manager（归档管理 · 阶段六）

**定位**：本地学习资料库的管理者——将下载的资源按学科/年龄/主题分类归档，维护完整索引，提供跨平台内容级去重和检索复用。

**输入**：`stage5_download.json` 的 data
**输出**：`stage6_archive.json`（文件移入 `学习资料库/`）

**资料库结构**：

```
学习资料库/
├── {学科}/                    ← 数学、语文、英语、科普、编程、艺术...
│   ├── 全龄通用/
│   └── {学段}/                ← 小学三年级、6-8岁...
│       └── {主题}/            ← 四则混合运算、拼音启蒙...
│           └── {来源}/        ← B站、K5Learning、人教版...
│               └── 资源文件
├── 综合主题/                  ← 跨学科资源
├── 待确认/                    ← 分类不确定的资源
└── .library/
    ├── index.json             ← 主索引
    ├── tags.json              ← 标签索引
    └── logs/                  ← 操作日志
```

**执行流程**：

```
第零步：归档前去重检查（自动执行）
    → 加载 index.json → DedupEngine 检查
    → 四层去重：resource_id → 内容指纹 → URL → 标题相似度
    → 按策略处理：keep_best_quality / keep_earliest / keep_latest / mark

第一步：资源检查（最终资源？完整性？安全？）

第二步：分类判断（学科/适龄/主题/来源）

第三步：文件整理（创建目录 → 移动文件 → 重命名）

第四步：元数据记录（继承上游全部字段 + 新增归档字段 → 写入索引）

第五步：验证与反馈 → 写入 stage6_archive.json
```

**输出 data 核心字段**：

| 字段 | 必选 | 说明 |
|------|:----:|------|
| `resources[].library_path` | ✅ | 资料库内路径 |
| `resources[].archive_time` | ✅ | 归档时间（ISO） |
| `resources[].dedup_status` | ⚠️ | new / duplicate / skipped |

**去重引擎**：实现在 `resource-platforms/scripts/shared/dedup.py`（`DedupEngine`），配置在 `config/settings.yaml` 的 `dedup` 段。

**参考资料**：
- `references/library-structure.md` — 资料库结构详细规范

---

## 五、已接入平台

| 平台 | 标识 | 搜索能力 | 登录要求 | 反爬等级 | 擅长领域 |
|------|------|---------|---------|---------|---------|
| B站 | `bilibili` | 强 | 无需 | ⭐⭐⭐⭐ | 视频、系统课程、动画 |
| 国家中小学智慧教育平台 | `smartedu` | 强 | 可选 | ⭐⭐⭐ | 官方学科资源、教材 |
| 知乎 | `zhihu` | 中 | Cookie | ⭐⭐⭐ | 图文、方法、经验 |
| 抖音 | `douyin` | 中 | 自动 | ⭐⭐⭐⭐ | 短视频教程 |
| 微博 | `weibo` | 中 | Cookie | ⭐⭐⭐ | 资料整理分享 |
| 喜马拉雅 | `ximalaya` | 强 | 无需 | ⭐ | 音频、故事、磨耳朵 |
| 网易公开课 | `open163` | 中 | 无需 | ⭐ | 公开课、纪录片 |

---

## 六、项目目录结构

```
learning-resource-suite/
│
├── README.md                          ← 本文件（架构说明书）
├── .gitignore
│
├── learning-resource-flow/            ← 总调度 Skill
│   ├── SKILL.md
│   └── references/
│       ├── workflow-guide.md
│       └── output-templates.md
│
├── resource-intent/                   ← 需求理解 Skill（阶段一）
│   ├── SKILL.md
│   └── references/
│       ├── requirement-decomposition-rules.md
│       └── clarification-phrases.md
│
├── resource-search/                   ← 搜索策略 Skill（阶段二）
│   ├── SKILL.md
│   └── references/
│       ├── 主题扩展词表.md
│       ├── config/
│       │   ├── platform-advantages.md
│       │   ├── platform-mapping.md
│       │   └── site-whitelist.md
│       └── guides/
│           ├── query-generation.md
│           ├── platform-search-capabilities.md
│           └── search-strategy.md
│
├── resource-platforms/                ← 平台执行 Skill（阶段三）
│   ├── SKILL.md
│   ├── references/
│   │   ├── download-methods.md
│   │   ├── test-cases.md
│   │   ├── platforms/                 ← 各平台详细文档
│   │   │   ├── architecture.md
│   │   │   ├── bilibili.md
│   │   │   ├── smartedu.md
│   │   │   ├── zhihu.md
│   │   │   ├── douyin.md
│   │   │   ├── weibo.md
│   │   │   ├── ximalaya.md
│   │   │   ├── open163.md
│   │   │   └── smartedu-resource-schema.md
│   │   └── schemas/                   ← 接口契约与规范
│   │       ├── resource-schema.md
│   │       ├── error-codes.md
│   │       ├── platform-search-contract.md
│   │       └── platform-download-contract.md
│   └── scripts/                       ← 7 平台 Python 脚本
│       ├── shared/                    ← 共享工具模块
│       ├── bilibili/
│       ├── smartedu/
│       ├── zhihu/
│       ├── douyin/
│       ├── weibo/
│       ├── ximalaya/
│       └── open163/
│
├── resource-selector/                 ← 质量筛选 Skill（阶段四）
│   ├── SKILL.md
│   └── references/
│       ├── quality-rubric.md
│       └── display-templates.md
│
├── resource-downloader/               ← 下载调度 Skill（阶段五）
│   ├── SKILL.md
│   └── references/
│       ├── error-codes.md
│       ├── download-methods.md
│       └── troubleshooting.md
│
├── library-manager/                   ← 归档管理 Skill（阶段六）
│   ├── SKILL.md
│   └── references/
│       └── library-structure.md
│
├── config/                            ← 项目配置
│   ├── settings.yaml                  ← 实际配置（已 gitignore）
│   └── settings.example.yaml          ← 示例配置
│
├── scripts/                           ← 开发工具
│   └── healthcheck.py                 ← 项目健康检查
│
└── tests/                             ← 测试脚本
    ├── contract_validation.py         ← 契约一致性校验
    ├── e2e_pipeline_test.py           ← 端到端流水线测试
    ├── test_dedup.py                  ← 去重引擎测试
    ├── test_platform_base_v2.py       ← 平台基类测试
    └── test_search_smoke.py           ← 搜索冒烟测试
```

---

## 七、配置系统

主配置文件 `config/settings.yaml`（从 `settings.example.yaml` 复制），包含以下配置段：

| 配置段 | 说明 |
|--------|------|
| `defaults` | 全局默认值（请求间隔、超时、重试、断路器） |
| `platforms` | 各平台专属配置（覆盖 defaults） |
| `download` | 下载设置（输出目录、并发数、大小限制） |
| `log` | 日志设置（级别、输出、轮转） |
| `search` | 搜索设置（最大结果数、去重开关） |
| `dedup` | 去重设置（策略、指纹、URL、标题相似度阈值） |
| `credentials` | 凭证设置（推荐环境变量传递） |

**环境变量覆盖**：前缀 `LRS_`，嵌套层级用双下划线 `__` 分隔。
例如：`LRS_DEDUP__STRATEGY=mark_and_keep_all`、`LRS_LOG__LEVEL=DEBUG`

---

## 八、开发工具

| 工具 | 位置 | 说明 |
|------|------|------|
| 健康检查 | `scripts/healthcheck.py` | 5 类完整性检查（目录结构、文件存在性、契约一致性、Python 依赖、平台映射） |
| 契约校验 | `tests/contract_validation.py` | 校验各 SKILL.md 输出格式的一致性 |
| 端到端测试 | `tests/e2e_pipeline_test.py` | 完整流水线端到端测试 |
| 去重测试 | `tests/test_dedup.py` | 去重引擎单元测试 |
| 搜索冒烟测试 | `tests/test_search_smoke.py` | 各平台搜索接口冒烟测试 |

---

## 快速开始

1. **安装 Skill 套件**：将各 Skill 目录安装到 WorkBuddy 的 Skill 目录中
2. **配置环境**：`cp config/settings.example.yaml config/settings.yaml`，按需修改
3. **发起请求**：对 `learning-resource-flow` 说自然语言需求，如"帮我找三年级数学练习题"
4. **确认与选择**：按提示确认需求、查看搜索计划、选择候选资源
5. **获取资源**：下载完成后资源自动归档到 `学习资料库/`

> 详细工作流指南见 `learning-resource-flow/references/workflow-guide.md`
