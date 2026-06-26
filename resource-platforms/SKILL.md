---
name: resource-platforms
description: 儿童学习资源平台执行层。封装7个平台（B站/智慧教育/知乎/抖音/微博/喜马拉雅/网易公开课）的搜索和下载能力。当需要执行具体平台搜索、视频下载、音频获取、文档导出等操作时加载本Skill。提供平台脚本路径、反爬策略、认证要求和下载方法。
---

# resource-platforms · 平台执行层

## 概述

本 Skill 是三层架构中的**平台执行层**，封装 7 个平台的搜索与下载能力。
不直接面向用户需求，由 `resource-search`（搜索调度）和 `resource-downloader`（下载调度）通过 `platform_base.py` 的 `CLIBasedPlatformSkill` 接口调度调用。

---

## 平台能力矩阵

| 平台 | 搜索 | 下载 | 登录要求 | 反爬等级 | 脚本目录 | 文档 |
|------|------|------|---------|---------|---------|------|
| bilibili | ✅ | ✅ | 搜索无需 | ⭐⭐⭐⭐ CDP+WBI | scripts/bilibili/ | references/bilibili.md |
| smartedu | ✅ | ✅ | Token可选 | ⭐⭐⭐ | scripts/smartedu/ | references/smartedu.md |
| zhihu | ✅ | ✅ | Cookie | ⭐⭐⭐ | scripts/zhihu/ | references/zhihu.md |
| douyin | ✅ | ✅ | 自动Token | ⭐⭐⭐⭐ ABogus+f2 | scripts/douyin/ | references/douyin.md |
| weibo | ✅ | ✅ | Cookie | ⭐⭐⭐ | scripts/weibo/ | references/weibo.md |
| ximalaya | ✅ | 🔲 | 无需 | ⭐ | scripts/ximalaya/ | references/ximalaya.md |
| open163 | ✅ | 🔲 | 无需 | ⭐ | scripts/open163/ | references/open163.md |

---

## 脚本执行机制

### CLIBasedPlatformSkill 约定

所有平台通过 `scripts/shared/platform_base.py` 的 `CLIBasedPlatformSkill` 基类接入：

1. **adapter.py**：每个平台的 `adapter.py` 继承 `CLIBasedPlatformSkill`，设置 `platform_name`
2. **搜索约定**：脚本名 `*_search.py` 自动被发现，执行 `{script} search {keyword} --max {n} -o {file}`
3. **下载约定**：脚本名 `*_dl.py` 自动被发现，执行 `{script} download {url} -o {dir}`
4. **输出标准化**：脚本输出 JSON 经 `_normalize_search_result()` 自动转为契约格式

### 共享模块

| 模块 | 路径 | 功能 |
|------|------|------|
| platform_base.py | scripts/shared/ | 平台基类 + RateLimiter + CircuitBreaker + CredentialManager |
| config_loader.py | scripts/shared/ | 统一配置加载（settings.yaml + 环境变量） |
| dedup.py | scripts/shared/ | 跨平台内容级去重引擎 |
| logger.py | scripts/shared/ | 日志 + 脱敏过滤器 |
| utils.py | scripts/shared/ | 通用工具函数 |
| wbi_sign.py | scripts/shared/ | B站 WBI 签名算法 |

---

## 新增平台指南

接入新平台只需 3 步：

1. 创建 `scripts/新平台名/` 目录
2. 编写搜索脚本 `新平台名_search.py`（输出标准 candidate JSON）
3. 编写 `adapter.py`（继承 `CLIBasedPlatformSkill`，设置 `platform_name`）

> 完整模板见：`../_templates/platform-skill-template.md`

---

## 参考文档索引

### 平台专属文档

| 文档 | 内容 |
|------|------|
| `references/bilibili.md` | B站搜索/下载、CDP模式、WBI签名、字幕获取 |
| `references/smartedu.md` | 智慧教育平台全资源下载（PDF/m3u8/音频/图片） |
| `references/smartedu-architecture.md` | smartedu 架构详解（模块依赖/流程图/CDN策略） |
| `references/smartedu-resource-schema.md` | smartedu 资源类型定义 |
| `references/zhihu.md` | 知乎搜索+内容导出 Markdown |
| `references/douyin.md` | 抖音 f2引擎搜索+无水印下载 |
| `references/weibo.md` | 微博 ajax搜索+用户图文下载 |
| `references/ximalaya.md` | 喜马拉雅专辑/声音搜索（公开API） |
| `references/open163.md` | 网易公开课搜索（服务端渲染解析） |

### 通用参考

| 文档 | 内容 |
|------|------|
| `references/download-methods.md` | 下载方法全览（yt-dlp/m3u8/f2/ffmpeg，913行） |
| `references/platform-search-contract.md` | 搜索接口契约（search ↔ platform） |
| `references/platform-download-contract.md` | 下载接口契约（downloader ↔ platform） |

### 外部规范（根目录 shared/）

| 文档 | 路径 |
|------|------|
| 资源元数据规范 | `../shared/schemas/resource-schema.md` |
| 质量评估标准 | `../shared/schemas/quality-rubric.md` |
| 错误码体系 | `../shared/schemas/error-codes.md` |
| 平台优势图谱 | `../shared/config/platform-advantages.md` |
| 平台映射表 | `../shared/config/platform-mapping.md` |
| 日志规范 | `../shared/logging-convention.md` |

---

## 关键原则

1. **脚本不可用时标记跳过** — 不阻塞其他平台的搜索/下载
2. **搜索优先用 API** — 避免启动浏览器（CDP/Playwright 仅作为 fallback）
3. **UGC 内容需严格评分** — 质量参差的平台内容交由 selector 做质量过滤
4. **反爬尊重** — RateLimiter 保证最小请求间隔，CircuitBreaker 熔断保护
5. **凭证安全** — Cookie/Token 通过环境变量传递，日志自动脱敏

---

*平台 Skill 版本：v1.0 | 平台数量：7（搜索7/下载5）*
