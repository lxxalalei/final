---
name: zhihu
description: 知乎资源站点。负责知乎问答和文章搜索、内容导出，实现平台 Skill 标准接口。
---

# 知乎平台

## 平台概况

- **域名**: zhihu.com
- **资源类型**: 问答、专栏文章、科普内容
- **目标用户**: 学龄儿童及以上
- **授权要求**: 搜索 API 需要登录（Cookie 中的 `z_c0` 作为 Bearer token）；无认证时可降级页面抓取
- **权威级别**: 社区内容 — 有专业回答也有普通用户，需评分

## 标准接口

接口契约详见 `../../shared/schemas/platform-search-contract.md`（搜索）和 `../../shared/schemas/platform-download-contract.md`（下载）。

### search(intent) → candidates

已实现。脚本路径：`platforms/zhihu/scripts/zhihu_search.py`

搜索策略（三级降级）：
1. **API 搜索**（优先）：调用 `https://www.zhihu.com/api/v4/search_v3`，需要 `z_c0` Cookie → 返回完整结果
2. **页面抓取降级**：无认证时抓取搜索结果页 HTML 并解析 → 知乎搜索页通常返回 403，此路径多数情况不可用
3. **搜索引擎兜底**：通过 Bing/百度 `site:zhihu.com` 搜索并提取知乎链接 → 召回率较低（0-5 条），但无需认证

无认证时实际效果：Bing/百度搜索引擎兜底返回 0-5 条知乎候选，召回率有限。配置 `z_c0` Cookie 后可获取完整搜索结果。

输出标准 candidate JSON，必填字段：`resource_id`（格式 `平台名:平台内ID`）/ `title` / `source_url` / `platform`。

```bash
# 基本搜索
python3 platforms/zhihu/scripts/zhihu_search.py search "三年级数学学习方法" --max 20

# 带 Cookie 搜索（获取完整 API 结果）
python3 platforms/zhihu/scripts/zhihu_search.py search "小学英语启蒙" \
  --cookie "z_c0=2|xxxxx" --max 20 -o candidates.json

# 通过环境变量传 Cookie
export ZHIHU_COOKIE="z_c0=2|xxxxx"
python3 platforms/zhihu/scripts/zhihu_search.py search "科普知识" --max 20
```

### download(candidate) → result

已实现。脚本路径：`platforms/zhihu/scripts/zhihu_dl.py`

通过知乎 API 获取内容正文，导出为 Markdown 文件。支持三种内容类型：

| URL 格式 | 内容类型 | 提取内容 |
|---------|---------|---------|
| `/question/{qid}` | 问题页 | 问题标题 + 前5个高赞回答 |
| `/question/{qid}/answer/{aid}` | 单回答 | 问题标题 + 指定回答正文 |
| `/p/{id}` 或 `zhuanlan.zhihu.com/p/{id}` | 专栏文章 | 文章正文 |

```bash
# 下载问答页面（导出为 Markdown）
python3 platforms/zhihu/scripts/zhihu_dl.py download \
  "https://www.zhihu.com/question/123456789" -o ./downloads/

# 下载专栏文章
python3 platforms/zhihu/scripts/zhihu_dl.py download \
  "https://zhuanlan.zhihu.com/p/12345678" -o ./downloads/

# 带 Cookie 下载（获取更多内容）
python3 platforms/zhihu/scripts/zhihu_dl.py download \
  "https://www.zhihu.com/question/123/answer/456" --cookie "z_c0=2|xxxxx" -o ./downloads/
```

输出：Markdown 文件（`.md`），包含标题、作者、正文内容。

## 搜索方法

直接调用 `zhihu_search.py`，无需浏览器。

```bash
# 搜索输出标准 candidate JSON 到 stdout 或文件
python3 platforms/zhihu/scripts/zhihu_search.py search "关键词" -o output.json
```

## 关键词匹配范围

| 内容类型 | 匹配关键词 |
|---------|-----------|
| 学习方法 | 学习方法、怎么办、如何、经验 |
| 科普知识 | 为什么、原理、科普、知识 |
| 教育资源 | 推荐、书单、资源、网站 |

## 依赖

- httpx（可选，有则用，无则降级 urllib）
- `shared/utils.py` — safe_filename 等通用工具
- `shared/logger.py` — 统一日志

## 认证说明

知乎搜索 API 和内容 API 需要 Bearer token（从 Cookie 中的 `z_c0` 提取）。

获取方式：
1. 登录知乎（zhihu.com）
2. 从浏览器 Cookie 中复制 `z_c0` 的值
3. 传入 `--cookie "z_c0=2|xxxxx"` 或设置环境变量 `ZHIHU_COOKIE`

无认证时：
- 搜索：API 不可用 → 页面抓取 403 → 搜索引擎兜底（Bing/百度 site:zhihu.com，召回率低 0-5 条）
- 下载：可获取部分公开内容，登录墙内容会缺失

**建议**：配置 `ZHIHU_COOKIE` 环境变量以获取完整搜索能力。

## 质量自评维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 赞同数 | 40% | 10000+ 满分，1000+ 15分，500+ 10分 |
| 评论数 | 10% | 1000+ 5分，500+ 3分 |
| 作者认证 | 10% | 认证作者 +5分 |
| 基础分 | 40% | 60分起步 |

## 主题分类推断

根据搜索关键词和问题/文章标题推断资源所属品类：

| 品类 | 关键词 |
|------|--------|
| 学科同步 | 数学、语文、英语、课本、教材、同步、课堂 |
| 科普启蒙 | 科普、科学、宇宙、恐龙、动物、实验、百科 |
| 人文历史 | 古诗、诗词、国学、论语、历史、成语、绘本 |
| 语言表达 | 英语、单词、口语、听力、拼音、识字、写作 |
| 思维训练 | 思维、逻辑、奥数、编程、scratch、python、益智 |
| 艺术美育 | 画画、美术、音乐、钢琴、舞蹈、书法、手工 |
| 习惯品格 | 习惯、情绪、安全、礼仪、品格、社交、情商 |
| 兴趣拓展 | 棋、围棋、运动、体育、航模、机器人、乐高 |

## 关键原则

1. **搜索优先用 API** — 调用知乎搜索 API，需 z_c0 认证
2. **内容下载导出 Markdown** — 通过 API 获取正文，导出为 `.md` 文件
3. **脚本不可用时标记跳过** — 不阻塞其他平台
4. **社区内容需严格评分** — 有专业回答也有普通用户，交由 selector 做质量过滤
5. **三级降级** — API → 页面抓取 → 搜索引擎兜底，无认证时也能返回有限结果
