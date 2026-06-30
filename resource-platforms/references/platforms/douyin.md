# 抖音平台

## 平台概况

- **域名**: douyin.com
- **资源类型**: 短视频、趣味科普、教育类创作者内容
- **目标用户**: 全年龄段（需家长筛选）
- **授权要求**: 需要 f2 引擎自动生成的 Token 和 ABogus 签名
- **权威级别**: UGC 创作者内容 — 质量参差，需 selector 严格评分

## 标准接口

接口契约详见 `../schemas/platform-search-contract.md`（搜索）和 `../../../resource-downloader/references/platform-download-contract.md`（下载）。

### search(intent) → candidates

已实现。基于 f2 引擎调用 `SEARCH_EP` 端点（`https://www.douyin.com/aweme/v1/web/search/item/`），自动生成 Token + ABogus 签名。

```bash
# 搜索视频，输出标准 candidate JSON
python3 scripts/douyin/douyin_dl.py search "小学数学" --max 20 -o candidates.json

# 搜索结果输出到 stdout
python3 scripts/douyin/douyin_dl.py search "趣味科普" --max 15

# 搜索失败时降级到 CDP 浏览器模式
python3 scripts/douyin/douyin_dl.py --cdp http://127.0.0.1:9222 search "英语启蒙" --max 20
```

输出标准 candidate JSON，必填字段：`resource_id`（格式 `平台名:平台内ID`）/ `title` / `source_url` / `platform`。

### download(candidate) → result

通过 f2 引擎获取无水印视频。已完整实现。

## 下载方法

```bash
# 单个视频
python3 scripts/douyin/douyin_dl.py download <视频URL或ID> -o ./downloads/

# 批量下载
python3 scripts/douyin/douyin_dl.py batch list.json -o ./downloads/

# 用户全部视频
python3 scripts/douyin/douyin_dl.py user <sec_uid> -o ./downloads/
python3 scripts/douyin/douyin_dl.py user <sec_uid> -o ./downloads/ --list-only
```

## 关键词匹配范围

| 内容类型 | 匹配关键词 |
|---------|-----------|
| 趣味科普 | 科普、实验、原理、冷知识 |
| 教学片段 | 教学、解题、技巧、方法 |

## 依赖

- f2 引擎（自动 Token 生成 + ABogus 签名）
- httpx
- CDP 浏览器（fallback 模式）

## 质量自评维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 点赞数 | 35% | 10万+ S级，1万+ A级，千+ B级 |
| 评论数 | 15% | 互动活跃度参考 |
| 收藏数 | 15% | 收藏量反映实用价值 |
| 内容质量 | 35% | 综合评估（教学性、趣味性） |

## 主题分类推断

根据搜索关键词和视频标题/标签推断资源所属品类：

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

1. **搜索优先用 API** — 优先调用 f2 搜索接口，无需浏览器
2. **视频下载用 f2 引擎** — 自动处理 Token 和签名
3. **脚本不可用时标记跳过** — 不阻塞其他平台
4. **UGC 内容需严格评分** — 质量参差，交由 selector 做质量过滤
