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

### 有专属 Skill 的平台（优先走平台通道）

| 平台 | Skill 路径 | Skill 状态 | 说明 |
|------|-----------|-----------|------|
| bilibili | `platforms/bilibili` | ✅ 可用 | B站专属，搜索+下载+反爬 |
| ximalaya | `platform-ximalaya` | 规划中 | 喜马拉雅专属，音频下载 |
| smartedu | `platforms/smartedu` | ✅ 可用 | 国家中小学智慧教育平台 |
| baiduwenku | `platform-baiduwenku` | 规划中 | 百度文库文档下载 |
| zhihu | `platforms/zhihu` | ✅ 可用 | 知乎图文提取 |
| douyin | `platforms/douyin` | ✅ 可用 | 抖音专属，f2引擎搜索+无水印下载 |
| weibo | `platforms/weibo` | ✅ 可用 | 微博专属，ajax搜索+用户图文下载 |

> 注：标记「✅ 可用」的平台已接入，优先走平台专属通道；其余走通用兜底通道。

### 通用下载通道

没有专属 Skill 的平台，按资源类型走通用通道：

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

根据统一错误码体系（`shared/schemas/error-codes.md`）：

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
      "file_size": "1.2GB",
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

## 错误处理

### 统一错误码

所有错误遵循统一错误码体系，详见：
`../shared/schemas/error-codes.md`

**主要错误类别：**
- `NETWORK_` - 网络错误（超时、连接失败等）
- `ANTI_CRAWL_` - 反爬错误（频率限制、验证码等）
- `AUTH_` - 认证错误（需要登录、权限不足等）
- `CONTENT_` - 内容错误（不存在、付费、DRM等）
- `PARSE_` - 解析错误（结构变化、格式不支持等）
- `DOWNLOAD_` - 下载错误（部分下载、文件损坏等）
- `SYSTEM_` - 系统错误（工具未找到、配置错误等）

### 错误返回格式

每个失败的资源都要包含：
```json
{
  "error_code": "CONTENT_PREMIUM_ONLY",
  "error_message": "需要付费才能查看完整内容",
  "can_retry": false,
  "suggested_action": "降级为摘要提取",
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

## 设计原则

### 1. 调度与执行分离
调度层只负责路由和管理，具体下载由平台 Skill 或通用工具执行。

### 2. 最大化提取原则
能拿完整不拿摘要，能拿原文件不拿转换格式，部分可用也输出。

### 3. 容错降级机制
下载失败不是终点，按四级降级路径逐步降低预期，尽量给用户有价值的东西。

### 4. 透明反馈
进度、成功、失败、降级，都要明确告诉用户，不隐瞒问题。

### 5. 统一规范
所有输入输出严格遵循统一元数据规范和错误码体系。

---

## 参考资料

- `references/download-methods.md` - 通用下载工具使用说明（兜底方案）
- `../shared/schemas/resource-schema.md` - 资源元数据规范
- `../shared/schemas/error-codes.md` - 统一错误码体系
- `../shared/schemas/skill-contract.md` - 跨 Skill 上下文传递契约
- `../shared/config/platform-mapping.md` - 平台-Skill 映射表

---

