---
name: resource-downloader
description: 儿童学习资源下载调度器 Skill，负责根据资源平台和类型，调度对应的平台 Skill 或通用下载工具执行下载，支持重试、降级、错误处理等机制。
---

# resource-downloader · 下载调度器

## 概述

本 Skill 是三层架构中的**业务能力层**，负责下载任务的调度与管理。
它不直接执行具体下载，而是根据资源的平台、类型，调度对应的平台 Skill 或通用下载工具。

**上游**：resource-selector（候选展示与用户选择）
**下游**：各 platform skill（平台执行层）、通用下载工具

---

## 核心职责

1. **平台路由**：根据资源平台，调度对应的平台 Skill 执行下载
2. **进度跟踪**：跟踪每个资源的下载状态，实时反馈进度
3. **错误处理**：根据错误码判断是否可重试，执行重试策略
4. **分级降级**：下载失败时，按四级降级路径逐步降低预期
5. **结果汇总**：汇总所有资源的下载结果，结构化输出
6. **通用兜底**：没有对应平台 Skill 时，走通用下载通道

---

## 输入格式

接收来自 resource-selector 的选定资源列表，每个资源符合统一元数据规范。

**输入示例：**
```json
{
  "selected_count": 5,
  "selection_mode": "manual",
  "resources": [
    {
      "resource_id": "bilibili:BV1xx411c7mD",
      "title": "小学必背古诗文动画（228集全）",
      "type": "视频",
      "subject": "语文",
      "platform": "bilibili",
      "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
      "source_name": "B站",
      "quality_level": "S",
      "download_feasibility": "中",
      "description": "动画形式讲解小学必背古诗，覆盖全部228首",
      "tags": ["古诗", "动画", "系统课程"]
    },
    ...
  ]
}
```

---

## 下载调度流程

### 第一步：平台路由判断

对每个资源，根据 `platform` 字段判断走哪条通道：

```
资源 platform 字段
    ↓
有对应 platform skill？ → 是 → 调用 platform skill 下载
    ↓ 否
是视频/音频类？ → 是 → 用 yt-dlp 通用下载
    ↓ 否
是直链文件？ → 是 → 用 wget/curl 直接下载
    ↓ 否
是网页/图文？ → 是 → 网页提取/转换保存
    ↓ 否
降级为：保存链接 + 摘要
```

### 第二步：批量调度

- 按平台分组，同平台的一起调度
- 支持并行下载（但不要太多并发，避免反爬）
- 建议并发数：2-3 个同时下载

### 第三步：进度跟踪

每个资源跟踪下载状态：
- 等待中 → 下载中 → 成功 / 失败 / 降级

### 第四步：失败重试

根据错误类型决定是否重试，详见「重试策略」章节。

### 第五步：分级降级

重试后仍失败，进入四级降级路径，详见「四级降级体系」章节。

### 第六步：结果汇总

所有资源处理完后，汇总结果输出。

---

## 平台路由规则

### 有专属下载脚本的平台（优先走平台通道）

| 平台 | 脚本路径 | 说明 |
|------|---------|------|
| bilibili | `./scripts/bilibili/bilibili_dl.py` | B站视频下载 |
| douyin | `./scripts/douyin/douyin_dl.py` | 抖音无水印下载 |
| zhihu | `./scripts/zhihu/zhihu_dl.py` | 知乎图文提取 |
| weibo | `./scripts/weibo/weibo_dl.py` | 微博图文下载 |
| smartedu | `../resource-platforms/scripts/smartedu/smartedu_download.py` | 国家中小学智慧教育平台（暂留在 platforms，后续拆解） |

> smartedu 平台较特殊（搜索和下载共享认证模块），其下载脚本暂收录在 resource-platforms 中，后续单独拆解。

### 通用下载通道

没有专属脚本的平台，按资源类型走通用通道：

| 资源类型 | 通用工具 | 说明 |
|---------|---------|------|
| 视频 | yt-dlp | 支持大部分视频平台 |
| 音频 | yt-dlp + ffmpeg | 从视频提取或直接下载音频 |
| 文档直链 | wget / curl | PDF、DOC、PPT 等直链 |
| 图文网页 | 正文提取 + 转 MD/PDF | 保存网页内容 |
| 图片 | wget 批量下载 | 图集下载 |

---

## 重试策略

### 错误类型与重试次数

根据错误码体系（详见下方「错误码速查」）：

| 错误类型 | 最大重试次数 | 初始延时 | 递增方式 |
|---------|-------------|---------|---------|
| 网络超时/连接失败 | 3 次 | 1 秒 | 指数递增（1s → 3s → 9s） |
| 频率限制（反爬） | 2 次 | 10 秒 | 线性递增（10s → 20s） |
| 部分下载/文件损坏 | 2 次 | 0 秒 | 立即重试（断点续传） |
| 内容为空/不完整 | 1 次 | 2 秒 | 固定延时 |
| 反爬拦截（验证码等） | 1 次 | 5 秒 | 换策略后重试 |
| 付费/DRM/权限不足 | 0 次 | - | 直接降级，不重试 |
| 内容已删除/不存在 | 0 次 | - | 直接降级，不重试 |

### 重试原则

1. **网络问题必重试**：超时、连接失败等网络问题，一定要重试
2. **反爬问题谨慎重试**：可能触发更严的限制，重试次数少
3. **内容问题不重试**：付费、删除、不存在，重试也没用
4. **累计3次失败才降级**：给足机会，但也不无限重试

---

## 四级降级体系

下载失败时，按以下四级逐步降级，尽量获取最多信息：

| 等级 | 级别 | 说明 | 信息完整度 |
|------|------|------|-----------|
| Level 0 | 完整版本 | 原始文件完整下载 | 100% |
| Level 1 | 预览版本 | 预览版/低清晰度/部分章节 | 60-80% |
| Level 2 | 核心摘要 | 目录、简介、核心要点 | 20-40% |
| Level 3 | 来源链接 | 只保存标题、链接、简介 | 5-10% |

### 不同资源类型的降级路径

#### 视频类
```
Level 0：高清完整下载（默认）
    ↓ 失败
Level 1：降低清晰度重试（720p → 480p → 360p）
    ↓ 失败
Level 2：提取字幕 + 章节大纲 + 简介
    ↓ 失败
Level 3：保存标题 + 链接 + 简介 + 观看指引
```

#### 音频类
```
Level 0：完整音质下载（默认）
    ↓ 失败
Level 1：降低音质重试（320k → 128k）
    ↓ 失败
Level 2：提取章节列表 + 简介
    ↓ 失败
Level 3：保存标题 + 链接 + 简介
```

#### 文档类
```
Level 0：原文件完整下载（默认）
    ↓ 失败
Level 1：预览页完整提取（截图或文字）
    ↓ 失败
Level 2：目录 + 核心内容摘要
    ↓ 失败
Level 3：保存标题 + 链接 + 简介 + 获取指引
```

#### 图文类
```
Level 0：正文完整提取转 Markdown（默认）
    ↓ 失败
Level 1：整页截图转 PDF
    ↓ 失败
Level 2：核心段落摘要
    ↓ 失败
Level 3：保存标题 + 链接 + 摘要
```

### 降级原则

1. **最大化提取**：能拿完整不拿摘要，能拿原文件不拿转换格式
2. **明确标注**：降级内容必须明确标注「非完整版本」
3. **部分可用也输出**：不要因为不完整就直接放弃
4. **失败替代推荐**：所有失败资源标配 1-2 个同主题同类型替代推荐

---

## 输出格式

所有资源处理完成后，输出结构化的下载结果。

**输出格式（符合统一元数据规范）：**
```json
{
  "total_count": 5,
  "success_count": 3,
  "degraded_count": 1,
  "failed_count": 1,
  "resources": [
    {
      "resource_id": "bilibili:BV1xx411c7mD",
      "title": "小学必背古诗文动画（228集全）",
      "type": "视频",
      "platform": "bilibili",
      "source_url": "https://www.bilibili.com/video/BV1xx411c7mD",
      "quality_level": "S",
      "download_status": "success",
      "degraded_level": "Level 0",
      "file_path": "/downloads/古诗/小学必背古诗文动画.mp4",
      "file_size": 156000000,
      "fetch_time": "2026-06-24 15:30:00",
      "fetch_method": "yt-dlp",
      "duration": "共228集"
    },
    {
      "resource_id": "baiduwenku:xxx",
      "title": "小学古诗知识点汇总",
      "type": "文档",
      "platform": "baiduwenku",
      "source_url": "https://wenku.baidu.com/view/xxx",
      "quality_level": "A",
      "download_status": "degraded",
      "degraded_level": "Level 2",
      "error_code": "CONTENT_PREMIUM_ONLY",
      "error_message": "需要付费才能查看完整内容",
      "degraded_content": "已提取目录和前3章核心内容，保存为摘要文档",
      "file_path": "/downloads/古诗/小学古诗知识点汇总-摘要.md"
    },
    {
      "resource_id": "xxx",
      "title": "xxx",
      "type": "视频",
      "platform": "xxx",
      "source_url": "xxx",
      "quality_level": "B",
      "download_status": "failed",
      "degraded_level": "Level 3",
      "error_code": "CONTENT_NOT_FOUND",
      "error_message": "视频已被删除",
      "alternative_recommendations": [
        { "title": "替代资源1", "url": "xxx", "reason": "同主题，质量更高" },
        { "title": "替代资源2", "url": "xxx", "reason": "同类型，下载难度低" }
      ]
    }
  ]
}
```

### 下载状态说明

| 状态 | 说明 |
|------|------|
| `success` | 完整下载成功（Level 0） |
| `degraded` | 降级获取（Level 1/2），部分内容可用 |
| `failed` | 下载失败，只保留了链接和摘要（Level 3） |

---

## 错误码速查

> 完整错误码体系见 `references/error-codes.md`。以下是模型执行下载时需要快速查阅的核心部分。

### 7 类前缀

| 前缀 | 场景 | 可重试？ |
|------|------|---------|
| `NETWORK_` | 超时、连接失败、DNS、SSL | ✅ 重试 2-3 次 |
| `ANTI_CRAWL_` | 限流、拦截、验证码、IP封禁 | 限流重试，其余不重试 |
| `AUTH_` | 需登录、登录过期、权限不足、会员专享 | 过期重试1次，其余不重试 |
| `CONTENT_` | 不存在、已删除、私有、付费、DRM、地区限制 | ❌ 不重试，直接降级 |
| `PARSE_` | 结构变化、格式不支持、内容为空 | 空内容重试1次，其余不重试 |
| `DOWNLOAD_` | 下载失败、部分下载、文件损坏、磁盘满 | 损坏/部分重试1-2次，磁盘满不重试 |
| `SYSTEM_` | 工具缺失、配置错误、未知错误 | 未知错误重试1次 |

### 常用错误码

| 错误码 | 场景 | 重试 | 降级动作 |
|--------|------|------|---------|
| `NETWORK_TIMEOUT` | 请求超时 | ✅ 3次 | → degrade_to_preview |
| `ANTI_CRAWL_RATE_LIMITED` | 被限流 | ✅ 2次（加延时） | → retry_with_delay |
| `ANTI_CRAWL_CAPTCHA` | 需验证码 | ❌ | → need_user_action |
| `AUTH_LOGIN_REQUIRED` | 需登录 | ❌ | → need_user_action |
| `AUTH_MEMBER_ONLY` | 会员专享 | ❌ | → degrade_to_summary |
| `CONTENT_NOT_FOUND` | 内容不存在 | ❌ | → skip |
| `CONTENT_REMOVED` | 已下架 | ❌ | → skip |
| `CONTENT_PREMIUM_ONLY` | 付费内容 | ❌ | → degrade_to_summary |
| `CONTENT_DRM_PROTECTED` | DRM保护 | ❌ | → degrade_to_link |
| `PARSE_STRUCTURE_CHANGED` | 页面结构变了 | ❌ | → degrade_to_link |
| `DOWNLOAD_FILE_CORRUPTED` | 文件损坏 | ✅ 1次 | → 重新下载 |
| `DOWNLOAD_DISK_FULL` | 磁盘满 | ❌ | → need_user_action |

### 错误返回格式

每个失败/降级的资源必须包含：

```json
{
  "error_code": "CONTENT_PREMIUM_ONLY",
  "error_message": "需要付费才能查看完整内容",
  "can_retry": false,
  "suggested_action": "degrade_to_summary",
  "degraded_content": "已提取目录和核心摘要"
}
```

---

## 下载进度反馈

### 实时反馈

下载过程中，定期向用户反馈进度：

```
📥 正在下载，已完成 2/5：

✅ 完成：小学必背古诗文动画（B站）
✅ 完成：宝宝巴士国学古诗词（喜马拉雅）
⏳ 下载中：唐诗三百首精讲（网易公开课）... 60%
⏳ 等待中：小学古诗知识点汇总（百度文库）
⏳ 等待中：古诗手抄报模板（小红书）

预计还需要 2-3 分钟...
```

### 完成汇总

全部完成后，给出汇总：

```
✅ 下载完成！共 5 个资源：

📊 结果统计：
• 完整下载：3 个
• 降级获取：1 个（只拿到了摘要）
• 下载失败：1 个（已删除）

📁 保存位置：/downloads/古诗/

需要我帮您归档到资料库吗？
```

---

## 文件命名规范

下载后的文件必须用有意义的中文命名，不能用默认的 ID 或乱码。

### 命名格式

```
[主题]-[资源名]-[补充说明].[扩展名]
```

**示例：**
- `古诗-小学必背古诗文动画-228集全.mp4`
- `古诗-宝宝巴士国学古诗词-100集.mp3`
- `数学-四则混合运算练习题-100道含答案.pdf`

### 命名原则

1. **中文为主**：用户一看就知道是什么
2. **包含主题**：方便后续分类归档
3. **关键信息**：集数、含答案等重要信息带上
4. **不要太长**：控制在 30-50 字以内

---

## 参考资料

- `references/download-methods.md` - 通用下载工具使用说明（兜底方案）
- `references/error-codes.md` - 完整错误码体系（7类前缀+30+错误码+重试策略+降级路径）
- `references/platform-download-contract.md` - 平台下载接口规范
- `references/troubleshooting.md` - 常见下载问题排查
- `./scripts/{platform_id}/{platform_id}_dl.py` - 各平台专属下载脚本（bilibili/douyin/zhihu/weibo）

---

## 读写文件

### 1. 确认路径信息

读取 `{session_dir}/manifest.json`，获取本阶段执行所需信息：

- `manifest.stages.stage4.output` → 上游输入文件名（通常是 `stage4_select.json`）
- `manifest.stages.stage5.output` → 本阶段输出文件名（通常是 `stage5_download.json`）

### 2. 读取上游数据
- 读取 `{session_dir}/{上游输入文件}` 的 `data` 部分
- 提取用户选中的资源列表

### 3. 执行下载并写入结果

下载的文件存入 `{session_dir}/downloads/`（归档时由 library-manager 移入正式资料库）。下载完成后，将结果写入 `{session_dir}/{manifest.stages.stage5.output}`（通常是 `stage5_download.json`）：

```json
{
  "_meta": {
    "stage": 5,
    "session_id": "{session_id}",
    "skill": "resource-downloader",
    "created_at": "ISO时间",
    "input_from": "stage4_select.json"
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
        "// 说明": "保留 stage4 全部字段 + 新增下载结果字段",
        "resource_id": "...",
        "title": "...",
        "platform": "...",
        "source_url": "...",
        "...": "（stage4 的所有字段原样保留）",

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

- `_summary`（flow 读这个）：总数、成功/降级/失败各多少
- `data`（下游 library 读这个）：每个资源在上游字段基础上新增——`download_status`（success/degraded/failed）、`degraded_level`（Level 0-3）、`file_path`（本地路径）、`file_size`（字节）、`fetch_time`、`fetch_method`、失败时附加 `error_code`/`error_message`、降级时附加 `degraded_content`、失败时附加 `alternative_recommendations`
- **保留规则**：上游全部字段原样带过来；`failed` 的资源也要写进文件

### 4. 完成后

- 将 `manifest.json` 中 `stages.stage5.status` 更新为 `completed`
- 只返回 `_summary`，不在上下文中展开完整 data