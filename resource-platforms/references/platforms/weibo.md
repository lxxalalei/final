# 微博平台

## 平台概况

- **域名**: weibo.com
- **资源类型**: 图文、短视频、转载内容
- **目标用户**: 全年龄段
- **授权要求**: 需要 Cookie（ajax API 需要登录态，SUB cookie）
- **权威级别**: UGC — 内容质量参差，需 selector 评分

## 标准接口

接口契约详见 `../schemas/platform-search-contract.md`（搜索）和 `../schemas/platform-download-contract.md`（下载）。

### search(intent) → candidates

已实现。基于微博 ajax API（`https://weibo.com/ajax/searchall`）搜索，需要 Cookie（SUB cookie 登录态）。

```bash
# 搜索微博内容，输出标准 candidate JSON
python3 scripts/weibo/weibo_dl.py search "教育方法" --max 20 --cookie weibo_cookies.txt

# 搜索结果输出到文件
python3 scripts/weibo/weibo_dl.py search "科普知识" --max 20 --cookie weibo_cookies.txt -o candidates.json
```

输出标准 candidate JSON，必填字段：`resource_id`（格式 `平台名:平台内ID`）/ `title` / `source_url` / `platform`。

### download(candidate) → result

给定微博用户主页链接，爬取该用户所有微博（图文+视频）并下载。已完整实现。

## 下载方法

```bash
# 按用户主页 URL 下载
python3 scripts/weibo/weibo_dl.py download https://weibo.com/u/1669879400 -o ./downloads/

# 按用户名下载
python3 scripts/weibo/weibo_dl.py download https://weibo.com/n/用户名 -o ./downloads/ --max-pages 5

# 按 UID 下载
python3 scripts/weibo/weibo_dl.py download --uid 1669879400 -o ./downloads/

# 搜索微博内容（输出 candidate JSON）
python3 scripts/weibo/weibo_dl.py search "教育方法" --max 20 --cookie weibo_cookies.txt
```

输出结构：图文 → Markdown + 图片；视频 → 原始视频文件。

## 关键词匹配范围

| 内容类型 | 匹配关键词 |
|---------|-----------|
| 教育资讯 | 教育、学习方法、育儿、亲子 |
| 科普图文 | 科普、知识、百科、冷知识 |
| 习题分享 | 练习、习题、试卷、考试 |

## 依赖

- requests / urllib
- 微博 ajax API
- Cookie（SUB cookie，通过 Cookie Bridge 获取）
- `shared/utils.py` — safe_filename 等通用工具

## 质量自评维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 转发数 | 30% | 传播度指标 |
| 点赞数 | 20% | 认可度指标 |
| 评论数 | 15% | 互动活跃度 |
| 内容质量 | 35% | 综合评估 |

## 主题分类推断

根据搜索关键词和微博内容/标签推断资源所属品类：

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

1. **搜索优先用 ajax API** — 基于 ajax 接口实现关键词搜索
2. **图文下载用 weibo_dl.py** — 自动处理分页和内容提取
3. **脚本不可用时标记跳过** — 不阻塞其他平台
4. **UGC 内容需严格评分** — 内容质量参差，交由 selector 做质量过滤
