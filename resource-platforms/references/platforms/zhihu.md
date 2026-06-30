# 知乎平台

## 平台概况

- **域名**: zhihu.com
- **资源类型**: 问答、专栏文章、科普内容
- **目标用户**: 学龄儿童及以上
- **授权要求**: 搜索 API 需要 d_c0（设备指纹）+ z_c0（登录态）同时传入
- **权威级别**: 社区内容 — 有专业回答也有普通用户，需评分

## 标准接口

接口契约详见 `../schemas/platform-search-contract.md`（搜索）和 `../../../resource-downloader/references/platform-download-contract.md`（下载）。

### search(intent) → results

已实现。脚本路径：`scripts/zhihu/zhihu_search.py`

调用知乎搜索 API（`search_v3`），输出符合 platform-search-contract 的标准 JSON。

```bash
# 基本搜索（自动从 config/credentials.json 读取凭证）
python3 scripts/zhihu/zhihu_search.py search "三年级数学学习方法" --max 20

# 临时指定 Cookie（不写入配置文件）
python3 scripts/zhihu/zhihu_search.py search "小学英语启蒙" \
  --cookie "d_c0值 z_c0值" --max 20 -o candidates.json
```

### download(candidate) → result

已实现。脚本路径：`resource-downloader/scripts/zhihu/zhihu_dl.py`（已迁移至 downloader）

通过知乎 API 获取内容正文，导出为 Markdown 文件。

```bash
# 下载问答页面（导出为 Markdown）
python3 resource-downloader/scripts/zhihu/zhihu_dl.py download \
  "https://www.zhihu.com/question/123456789" -o ./downloads/
```

## 凭证管理

知乎搜索 API 需要 d_c0（设备指纹）+ z_c0（登录态）同时存在。

### 获取 Cookie

1. 浏览器登录知乎（zhihu.com）
2. 按 F12 打开开发者工具 → Application → Cookies → `https://www.zhihu.com`
3. 找到 `d_c0` 和 `z_c0` 两个值，复制它们的 Value

### 保存到本地（推荐）

```bash
# 持久化保存（随 skill 安装在用户本地，后续自动读取）
python3 scripts/zhihu/zhihu_search.py set-cookie "d_c0值 z_c0值"

# 检查已保存的凭证
python3 scripts/zhihu/zhihu_search.py check-cookie
```

凭证文件位置：`scripts/zhihu/config/credentials.json`（已被 .gitignore 排除，不会提交）

### 凭证查找优先级

1. CLI 参数 `--cookie`
2. 环境变量 `ZHIHU_COOKIE`
3. 配置文件 `config/credentials.json`

### Cookie 过期

知乎 z_c0 会定期过期（通常几天到几周）。当 API 返回 401/403 时，脚本输出 `[CREDENTIAL_EXPIRED]` 错误码。此时需重新获取 Cookie 并通过 `set-cookie` 更新。

## 关键词匹配范围

| 内容类型 | 匹配关键词 |
|---------|-----------|
| 学习方法 | 学习方法、怎么办、如何、经验 |
| 科普知识 | 为什么、原理、科普、知识 |
| 教育资源 | 推荐、书单、资源、网站 |

## 依赖

- 标准库 urllib，无需第三方包
- `shared/logger.py` — 统一日志

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

1. **搜索调用 API** — 需 d_c0 + z_c0 认证，无认证时跳过
2. **凭证持久化** — 用户首次配置后存入本地，自动读取
3. **脚本不可用时标记跳过** — 不阻塞其他平台
4. **社区内容需严格评分** — 有专业回答也有普通用户，交由 selector 做质量过滤

---

*文档版本：v2.0（2026-06-30 更新：三级降级移除，凭证持久化）*
