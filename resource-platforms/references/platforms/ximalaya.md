# 喜马拉雅平台

## 平台概况

- **域名**: ximalaya.com
- **资源类型**: 音频（专辑、声音）— 儿歌、睡前故事、国学古诗、英语启蒙、科普百科
- **目标用户**: 全年龄段，尤其适合学龄前和小学（磨耳朵、听读、睡前听）
- **授权要求**: 搜索无需登录（公开 JSON API），部分音频需 VIP
- **权威级别**: 社区内容 — 质量因主播而异，有大量知名 IP（宝宝巴士、米小圈、凯叔讲故事等）

## 标准接口

接口契约详见 `../schemas/platform-search-contract.md`。

### search(intent) → results

已实现。脚本路径：`scripts/ximalaya/ximalaya_search.py`

**无需登录，无需 Cookie，无需浏览器。** 直接调用喜马拉雅官方公开搜索 API。

```bash
# 搜索专辑（默认）
python3 scripts/ximalaya/ximalaya_search.py search "小学必背古诗" --max 20 -o results.json

# 搜索声音（单条音频）
python3 scripts/ximalaya/ximalaya_search.py search "儿歌 两只老虎" --core track --max 15

# 只搜免费内容
python3 scripts/ximalaya/ximalaya_search.py search "英语启蒙" --free-only --max 20

# 按热度排序
python3 scripts/ximalaya/ximalaya_search.py search "睡前故事" --sort popularity --max 20
```

### 下载

已迁移至 resource-downloader。

## 搜索参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--core` | 搜索类型：`album`（专辑）/ `track`（声音） | `album` |
| `--max` | 最大返回数 | 20 |
| `--free-only` | 只返回免费内容 | 否 |
| `--sort` | 排序：`relevance`/`popularity`/`newest` | `relevance` |
| `-o` | 输出 JSON 文件路径 | stdout |

### 两种搜索类型对比

| 类型 | core | 适用场景 | source_url 格式 |
|------|------|---------|----------------|
| 专辑 | `album` | 找系列内容（如"小学必背古诗全集"） | `https://www.ximalaya.com/album/{id}` |
| 声音 | `track` | 找单条音频（如"两只老虎 儿歌"） | `https://www.ximalaya.com/sound/{id}` |

默认用 `album`（专辑），因为专辑是成体系的内容，更适合系统学习。

## 关键词匹配范围

| 内容类型 | 匹配关键词 |
|---------|-----------|
| 古诗国学 | 古诗、国学、三字经、弟子规、诗词、论语、唐诗 |
| 儿歌童谣 | 儿歌、童谣、宝宝、幼儿、启蒙 |
| 睡前故事 | 睡前、故事、童话、寓言 |
| 英语启蒙 | 英语、英文、启蒙、磨耳朵 |
| 科普百科 | 科普、十万个为什么、百科、知识 |
| 学科学习 | 语文、数学、拼音、识字、阅读 |

## 质量评分策略

基础分 60，满分 100。等级映射：S(>=90) / A(>=75) / B(>=60) / C(<60)。

| 维度 | 评分依据 | 加分规则 |
|------|---------|---------|
| 内容质量与完整性 | 评分 + 集数 | 评分>=9.5(+10)，集数>=50(+6) |
| 权威可信度 | 认证主播 | is_v=true(+6) |
| 可获取性 | 免费内容 | 免费(+4) |
| 安全与体验 | 播放量 | 千万(+18)/百万(+14)/十万(+10)/万(+6) |

## 依赖

- 标准库 urllib，无需第三方包
- `shared/logger.py` — 统一日志
- 无需浏览器、无需 Playwright

---

*文档版本：v2.0（2026-06-30 标准化）*
