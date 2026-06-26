# 数据流转操作指南

> 本文档说明各 Skill 如何通过文件系统完成数据流转，以及每个阶段实际流转的数据内容。
>
> **适用对象**：阅读和编写 SKILL.md 的开发者 / 审阅数据流转设计的维护者

---

## 目录结构

每次用户请求创建一个会话目录：

```
.learning-resource-work/sessions/{session_id}/
├── manifest.json          ← flow 创建并维护（状态索引）
├── stage1_intent.json     ← resource-intent 写入
├── stage2_search.json     ← resource-search 写入
├── stage3_select.json     ← resource-selector 写入
├── stage4_download.json   ← resource-downloader 写入
├── stage5_archive.json    ← library-manager 写入
└── downloads/             ← 下载的文件临时存放
```

- session_id 命名：`{日期}-{时间}-{主题英文缩写}`，如 `20260626-1441-math-grade3`
- 所有会话平铺在 `sessions/` 下，不按对话分组

---

## 文件三层包装

每个 stage 文件统一用三层结构：

```
┌─────────────────────────────────┐
│  _meta    元数据（阶段号/Skill名/时间/上游来源）   │
├─────────────────────────────────┤
│  _summary  摘要（≤50字，flow 只读这个）          │
├─────────────────────────────────┤
│  data      完整业务数据（下游 Skill 读这个）      │
└─────────────────────────────────┘
```

- **flow** 只读每个文件的 `_summary`，不读 `data`
- **下游 Skill** 读上游文件的 `data`，写入自己的 `data`
- **上下文** 中只保留 session_id + 当前阶段 + 各阶段 summary

---

## 各 Skill 操作详解

### flow（总调度）— 创建会话 + 调度阶段

#### 操作 1：创建会话

收到新需求时：

```
1. 生成 session_id：{日期}-{时间}-{主题英文缩写}
2. 创建目录：.learning-resource-work/sessions/{session_id}/
3. 创建子目录：downloads/
4. 写入 manifest.json
```

manifest.json 内容：

```json
{
  "session_id": "20260626-1441-math-grade3",
  "user_request": "帮我找三年级数学练习题",
  "status": "in_progress",
  "current_stage": 1,
  "stages": {
    "stage1": {"status": "pending", "output": "stage1_intent.json"},
    "stage2": {"status": "pending", "output": "stage2_search.json"},
    "stage3": {"status": "pending", "output": "stage3_select.json"},
    "stage4": {"status": "pending", "output": "stage4_download.json"},
    "stage5": {"status": "pending", "output": "stage5_archive.json"}
  }
}
```

#### 操作 2：调度每个阶段（stage 1→5 循环）

```
对每个阶段：
  1. 更新 manifest.json → 当前阶段标记为 in_progress
  2. 调用对应 Skill，传递：会话目录路径、上游文件名、输出文件名
  3. Skill 返回后 → 只读输出文件的 _summary（前几行）
  4. 更新 manifest.json → 当前阶段标记为 completed，回填 summary
  5. 根据 summary 决定下一步
```

#### 操作 3：需求类型判断

| 用户说的 | 处理方式 |
|---------|---------|
| 新的搜索/下载主题 | 创建新会话，从阶段一开始 |
| "刚才那个""加选几个" | 复用当前 session_id，从指定阶段继续 |
| "我之前存的""上次下载的" | 调用 library-manager 查资料库（不碰 sessions/） |
| "继续上次没下完的" | 列出 sessions/ 目录让用户选，从中断处继续 |

> 搜索结果是时效性数据，每次新需求都重新搜索，不复用旧结果。

---

### 阶段一：resource-intent（需求理解）

#### 流转关系

```
用户自然语言需求
       │
       ▼
  resource-intent
       │
       ▼ 写入
  stage1_intent.json
       │
       ▼ data 被下游读取
  resource-search
```

#### 操作步骤

```
1. 从 flow 参数获取：会话目录 {session_dir}、输出文件名（stage1_intent.json）
   —— 本阶段无上游文件
2. 阅读用户原始需求，生成分级查询列表，做出的假设写入 assumptions
3. 写入结果文件
4. 提示 flow 调用 resource-search，只返回 _summary
```

#### 流转数据：stage1_intent.json

```json
{
  "_meta": {
    "stage": 1,
    "session_id": "{session_id}",
    "skill": "resource-intent",
    "created_at": "ISO时间",
    "input_from": null
  },
  "_summary": {
    "core_topic": "核心主题",
    "query_count": 3,
    "target_age": "8-9岁",
    "search_mode": "standard"
  },
  "data": {
    "summary": "一句话需求总结",
    "core_topic": "核心主题",
    "queries": [
      {"text": "查询关键词", "tier": "core/official/format/longtail", "format_hint": "视频/音频/文档/图文"}
    ],
    "target_age": "目标年龄范围",
    "grade_level": "年级",
    "difficulty": "入门/进阶/系统",
    "format_preferences": ["视频", "文档"],
    "source_preference": "不限/官方优先/视频平台优先",
    "search_mode": "standard / exhaustive",
    "assumptions": ["假设1", "假设2"]
  }
}
```

| 层 | 谁读 | 内容 |
|----|------|------|
| `_summary` | flow | 核心主题、查询数量、目标年龄、搜索模式 |
| `data` | resource-search | 需求总结、核心主题、查询列表、年龄/年级/难度、偏好、假设清单 |

---

### 阶段二：resource-search（搜索调度）

#### 流转关系

```
  stage1_intent.json 的 data
       │
       ▼ 读取 queries 列表
  resource-search
       │
       ├──→ 调度 resource-platforms（各平台搜索）
       │
       ▼ 汇总写入
  stage2_search.json
       │
       ▼ data 被下游读取
  resource-selector
```

#### 操作步骤

```
1. 从 flow 参数获取：会话目录 {session_dir}、上游文件名（stage1_intent.json）、输出文件名（stage2_search.json）
2. 读取 stage1_intent.json 的 data 部分，提取 queries 列表和搜索参数
3. 分发查询给各平台搜索，汇总去重后写入结果文件
4. 提示 flow 调用 resource-selector，只返回 _summary
```

#### 流转数据：stage2_search.json

```json
{
  "_meta": {
    "stage": 2,
    "session_id": "{session_id}",
    "skill": "resource-search",
    "created_at": "ISO时间",
    "input_from": "stage1_intent.json"
  },
  "_summary": {
    "total_count": 22,
    "platforms_searched": ["bilibili", "ximalaya", "smartedu"],
    "quality_dist": {"S": 3, "A": 8, "B": 8, "C": 3}
  },
  "data": {
    "total_count": 22,
    "search_summary": "查询3组/平台4个/召回85条/初筛后40条/去重后22条",
    "resources": [
      {
        "resource_id": "平台名:平台内ID",
        "title": "资源标题",
        "type": "视频/音频/文档/练习题/绘本/课件/图片",
        "subject": "学科/领域",
        "platform": "bilibili",
        "source_url": "来源URL",
        "source_name": "B站",
        "quality_level": "S/A/B/C",
        "download_feasibility": "高/中/低",
        "platform_quality_score": 85,
        "description": "内容简介",
        "age_range": "适龄范围",
        "grade_level": "适用年级",
        "tags": ["标签1"],
        "view_count": 5000000,
        "duration": "时长/集数",
        "language": "中文"
      }
    ]
  }
}
```

| 层 | 谁读 | 内容 |
|----|------|------|
| `_summary` | flow | 候选总数、搜索过的平台、质量分布 |
| `data` | resource-selector | 候选资源列表 |

data.resources[] 字段说明：

| 字段 | 必须 | 说明 |
|------|:----:|------|
| `resource_id` | ✅ | 唯一标识，格式 `平台名:平台内ID` |
| `title` | ✅ | 资源标题 |
| `type` | ✅ | 资源类型（视频/音频/文档/练习题/绘本/课件/图片） |
| `subject` | ✅ | 学科/领域 |
| `platform` | ✅ | 平台标识（bilibili/ximalaya/smartedu 等） |
| `source_url` | ✅ | 来源URL |
| `source_name` | ✅ | 平台显示名（B站/喜马拉雅 等） |
| `quality_level` | ✅ | 质量等级 S/A/B/C |
| `download_feasibility` | ✅ | 下载可行性 高/中/低 |
| `platform_quality_score` | ⚠️ | 平台自评分 0-100 |
| `description` | ⚠️ | 内容简介 |
| `age_range` | ⚠️ | 适龄范围 |
| `grade_level` | ⚠️ | 适用年级 |
| `tags` | ⚠️ | 标签数组 |
| `view_count` | ⚠️ | 播放/浏览量 |
| `duration` | ⚠️ | 时长/集数 |
| `language` | ⚠️ | 语言 |

---

### 阶段三：resource-selector（候选展示与用户选择）

#### 流转关系

```
  stage2_search.json 的 data
       │
       ▼ 读取候选列表 → 展示给用户
  resource-selector
       │
       ▼ 用户选择后写入
  stage3_select.json
       │
       ▼ data 被下游读取
  resource-downloader
```

#### 操作步骤

```
1. 从 flow 参数获取：会话目录 {session_dir}、上游文件名（stage2_search.json）、输出文件名（stage3_select.json）
2. 读取 stage2_search.json 的 data 部分，提取候选资源列表展示给用户
3. 用户确认选择后写入结果文件
4. 提示 flow 调用 resource-downloader，只返回 _summary
```

#### 流转数据：stage3_select.json

```json
{
  "_meta": {
    "stage": 3,
    "session_id": "{session_id}",
    "skill": "resource-selector",
    "created_at": "ISO时间",
    "input_from": "stage2_search.json"
  },
  "_summary": {
    "selected_count": 5,
    "selection_mode": "manual",
    "by_platform": {"bilibili": 2, "ximalaya": 3}
  },
  "data": {
    "selected_count": 5,
    "selection_mode": "manual / all / by_type / by_quality",
    "resources": [
      {
        "// 说明": "保留 stage2 中该资源的全部字段",
        "resource_id": "...",
        "title": "...",
        "type": "...",
        "subject": "...",
        "platform": "...",
        "source_url": "...",
        "source_name": "...",
        "quality_level": "...",
        "download_feasibility": "...",
        "...": "（stage2 的所有字段原样保留）"
      }
    ]
  }
}
```

| 层 | 谁读 | 内容 |
|----|------|------|
| `_summary` | flow | 选中数量、选择方式、平台分布 |
| `data` | resource-downloader | 用户选中的资源列表 |

**保留规则**：selector 只做筛选不做裁剪。用户没选的资源不写，但保留的每个资源要带过来 stage2 的全部字段，一个字段都不能删。

---

### 阶段四：resource-downloader（下载调度）

#### 流转关系

```
  stage3_select.json 的 data
       │
       ▼ 读取选中资源列表
  resource-downloader
       │
       ├──→ 调度 resource-platforms（平台下载）/ 通用工具
       │
       │     下载文件 → {session_dir}/downloads/
       │
       ▼ 写入结果
  stage4_download.json
       │
       ▼ data 被下游读取
  library-manager
```

#### 操作步骤

```
1. 从 flow 参数获取：会话目录 {session_dir}、上游文件名（stage3_select.json）、输出文件名（stage4_download.json）
2. 读取 stage3_select.json 的 data 部分，提取用户选中的资源列表
3. 按平台分组下载，文件存入 {session_dir}/downloads/，下载完成后写入结果文件
4. 提示 flow 调用 library-manager，只返回 _summary
```

#### 流转数据：stage4_download.json

```json
{
  "_meta": {
    "stage": 4,
    "session_id": "{session_id}",
    "skill": "resource-downloader",
    "created_at": "ISO时间",
    "input_from": "stage3_select.json"
  },
  "_summary": {
    "total_count": 5,
    "success_count": 3,
    "degraded_count": 1,
    "failed_count": 1
  },
  "data": {
    "total_count": 5,
    "success_count": 3,
    "degraded_count": 1,
    "failed_count": 1,
    "resources": [
      {
        "// 说明": "保留 stage3 全部字段 + 新增下载结果字段",
        "resource_id": "...",
        "title": "...",
        "platform": "...",
        "source_url": "...",
        "...": "（stage3 的所有字段原样保留）",

        "download_status": "success / degraded / failed",
        "degraded_level": "Level 0 / Level 1 / Level 2 / Level 3",
        "file_path": "{session_dir}/downloads/xxx.mp4",
        "file_size": 156000000,
        "fetch_time": "2026-06-26T15:00:00+08:00",
        "fetch_method": "获取方式说明",

        "// 失败/降级时额外字段": "",
        "error_code": "NETWORK_TIMEOUT / CONTENT_PREMIUM_ONLY / ...",
        "error_message": "错误信息",
        "degraded_content": "降级内容说明",
        "alternative_recommendations": []
      }
    ]
  }
}
```

| 层 | 谁读 | 内容 |
|----|------|------|
| `_summary` | flow | 总数、成功/降级/失败各多少 |
| `data` | library-manager | 每个资源在上游字段基础上新增下载结果 |

data 新增字段（下载阶段独有）：

| 字段 | 必须 | 说明 |
|------|:----:|------|
| `download_status` | ✅ | success / degraded / failed |
| `degraded_level` | ✅ | Level 0（完整）/ Level 1（预览）/ Level 2（摘要）/ Level 3（仅链接） |
| `file_path` | ⚠️ | 本地路径（成功时） |
| `file_size` | ⚠️ | 文件大小，字节（成功时） |
| `fetch_time` | ⚠️ | 获取时间 ISO |
| `fetch_method` | ⚠️ | 获取方式 |
| `error_code` | ⚠️ | 错误码（失败时，遵循 error-codes.md） |
| `error_message` | ⚠️ | 错误信息（失败时） |
| `degraded_content` | ⚠️ | 降级内容说明（降级时） |
| `alternative_recommendations` | ⚠️ | 替代推荐（失败时） |

**保留规则**：上游全部字段原样带过来；`failed` 的资源也要写进文件。

---

### 阶段五：library-manager（归档入库）

#### 流转关系

```
  stage4_download.json 的 data
       │
       ▼ 读取下载结果列表
  library-manager
       │
       ├──→ 归档前去重检查（DedupEngine）
       ├──→ 文件移动 downloads/ → 学习资料库/
       ├──→ 更新索引 index.json
       │
       ▼ 写入结果
  stage5_archive.json
       │
       ▼ data 被 flow 读取生成最终报告
  flow → 汇总报告给用户
```

#### 操作步骤

```
1. 从 flow 参数获取：会话目录 {session_dir}、上游文件名（stage4_download.json）、输出文件名（stage5_archive.json）
2. 读取 stage4_download.json 的 data 部分，提取下载结果列表
3. 执行归档前去重 → 文件移动 → 索引更新，完成后写入结果文件
4. 提示 flow 生成最终汇总报告，只返回 _summary
```

#### 流转数据：stage5_archive.json

```json
{
  "_meta": {
    "stage": 5,
    "session_id": "{session_id}",
    "skill": "library-manager",
    "created_at": "ISO时间",
    "input_from": "stage4_download.json"
  },
  "_summary": {
    "archived_count": 3,
    "skipped_count": 1,
    "dedup_stats": {"new": 3, "duplicate": 1}
  },
  "data": {
    "archived_count": 3,
    "skipped_count": 1,
    "resources": [
      {
        "// 说明": "保留 stage4 全部字段 + 新增归档字段",
        "resource_id": "...",
        "title": "...",
        "platform": "...",
        "download_status": "...",
        "...": "（stage4 的所有字段原样保留）",

        "library_path": "学习资料库/数学/小学三年级/四则混合运算/",
        "archive_time": "2026-06-26T16:00:00+08:00",
        "dedup_status": "new / duplicate / skipped"
      }
    ]
  }
}
```

| 层 | 谁读 | 内容 |
|----|------|------|
| `_summary` | flow | 归档成功数、跳过数、去重统计 |
| `data` | flow（生成汇总报告） | 每个资源在上游字段基础上新增归档信息 |

data 新增字段（归档阶段独有）：

| 字段 | 必须 | 说明 |
|------|:----:|------|
| `library_path` | ✅ | 资料库内路径 |
| `archive_time` | ✅ | 归档时间 ISO |
| `dedup_status` | ⚠️ | new（新资源）/ duplicate（重复标记）/ skipped（跳过归档） |

**保留规则**：上游全部字段（含 download_status/file_path 等）原样带过来，flow 最终汇总报告依赖这些字段。

---

## 全链路数据累积一览

数据沿管道单向流动，每个阶段只增不删：

```
stage1 (intent)
  │  data: summary, core_topic, queries[], target_age, grade_level,
  │        difficulty, format_preferences, source_preference,
  │        search_mode, assumptions[]
  │
  ▼  +搜索结果
stage2 (search)
  │  data: total_count, search_summary, resources[]
  │  resources[] 新增: resource_id, title, type, subject, platform,
  │                   source_url, source_name, quality_level,
  │                   download_feasibility, (+ 可选元数据 8 个字段)
  │
  ▼  筛选（不增字段，只做过滤）
stage3 (select)
  │  data: selected_count, selection_mode, resources[]
  │  resources[]: 同 stage2（选中的子集，字段不变）
  │
  ▼  +下载结果
stage4 (download)
  │  data: total/success/degraded/failed_count, resources[]
  │  resources[] 新增: download_status, degraded_level, file_path,
  │                   file_size, fetch_time, fetch_method,
  │                   (+ error_code/error_message/degraded_content/
  │                     alternative_recommendations)
  │
  ▼  +归档信息
stage5 (archive)
     data: archived_count, skipped_count, resources[]
     resources[] 新增: library_path, archive_time, dedup_status
```

到 stage5 结束时，每个资源对象累积了从 intent 到 archive 的完整生命周期数据，flow 据此生成最终汇总报告。

---

## 文件目录实体流转

除了 JSON 数据文件，还有实际文件的流转：

```
                         互联网资源
                             │
                    ┌────────▼────────┐
                    │  downloader 下载  │
                    └────────┬────────┘
                             │
                    ┌────────▼────────────────┐
                    │ {session_dir}/downloads/ │  ← 临时存放
                    └────────┬────────────────┘
                             │
                    ┌────────▼────────┐
                    │ library 归档移动 │
                    └────────┬────────┘
                             │
              ┌──────────────▼──────────────┐
              │     学习资料库/               │
              │   ├── 数学/小学三年级/...     │  ← 正式资料库
              │   ├── 语文/小学一年级/...     │
              │   └── .library/index.json    │  ← 索引文件
              └─────────────────────────────┘
```

---

*文档版本：v1.0 | 最后更新：2026-06-26*
