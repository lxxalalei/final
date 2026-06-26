# 喜马拉雅平台

## 平台概况

- **域名**: ximalaya.com
- **资源类型**: 音频（专辑、声音）— 儿歌、睡前故事、国学古诗、英语启蒙、科普百科
- **目标用户**: 全年龄段，尤其适合学龄前和小学（磨耳朵、听读、睡前听）
- **授权要求**: 搜索无需登录（公开 JSON API）；部分音频需 VIP
- **权威级别**: 社区内容 — 质量因主播而异，有大量知名 IP（宝宝巴士、米小圈、凯叔讲故事等）

## 标准接口

接口契约详见 `platform-search-contract.md`（搜索）和 `platform-download-contract.md`（下载）。

### search(intent) → candidates ✅ 已实现

**无需登录，无需 Cookie，无需浏览器。** 直接调用喜马拉雅官方公开搜索 API。

脚本路径：`scripts/ximalaya/ximalaya_search.py`

```bash
# 搜索专辑（默认）
python3 scripts/ximalaya/ximalaya_search.py search \
  "小学必背古诗" --max 20 -o results.json

# 搜索声音（单条音频）
python3 scripts/ximalaya/ximalaya_search.py search \
  "儿歌 两只老虎" --core track --max 15

# 只搜免费内容
python3 scripts/ximalaya/ximalaya_search.py search \
  "英语启蒙" --free-only --max 20

# 按热度排序
python3 scripts/ximalaya/ximalaya_search.py search \
  "睡前故事" --sort popularity --max 20

# 带 Cookie（可选，增强个性化结果）
python3 scripts/ximalaya/ximalaya_search.py search \
  "国学 三字经" --cookie "_xmLog=xxx" --max 20
```

**输出标准 candidate JSON**（符合 platform-search-contract），必填字段：`resource_id`（格式 `ximalaya:平台内ID`）/ `title` / `source_url` / `platform`。

### download(candidate) → result 🔲 规划中

下载能力尚未实现。喜马拉雅音频下载涉及音频地址解析（需处理 m4a/m4s 格式和加密），将在后续版本接入。

当前建议：
- 搜索阶段获取专辑/声音的 `source_url`，用户可直接访问喜马拉雅网页版收听
- 下载能力规划：解析专辑音轨列表 → 提取音频地址 → 下载 m4a/mp3

---

## 搜索方法

### 搜索接口

**主接口**（官方，推荐）：
```
GET https://www.ximalaya.com/revision/search
参数: core=album|track, kw=关键词, page=页码, rows=每页数,
      condition=relation|play|time, device=web, spellchecker=true
      fq=is_paid:false,（免费过滤，可选）
```

**降级接口**（M站镜像）：
```
GET https://apis.netstart.cn/ximalaya/search
参数: kw=关键词, core=album|track|all, page=页码, rows=每页数,
      condition=relation|play|recent, paidFilter=true&fq=is_paid:false,
```

### 搜索策略（双路径降级）

1. **主接口搜索**（优先）：调用 `revision/search`，公开 API 无需认证 → 返回完整结果
2. **镜像接口降级**：主接口异常时切换到 M站镜像接口 → 同样无需认证

### 搜索参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--core` | 搜索类型：`album`（专辑）/ `track`（声音） | `album` |
| `--max` | 最大返回数 | 20 |
| `--free-only` | 只返回免费内容 | 否 |
| `--sort` | 排序：`relevance`（相关度）/ `popularity`（热度）/ `newest`（最新） | `relevance` |
| `--cookie` | 可选 Cookie（增强个性化） | 无 |
| `-o` | 输出 JSON 文件路径 | stdout |

### 两种搜索类型对比

| 类型 | core | 适用场景 | source_url 格式 |
|------|------|---------|----------------|
| 专辑 | `album` | 找系列内容（如"小学必背古诗全集"） | `https://www.ximalaya.com/album/{id}` |
| 声音 | `track` | 找单条音频（如"两只老虎 儿歌"） | `https://www.ximalaya.com/sound/{id}` |

> 💡 **建议**：儿童学习资源搜索默认用 `album`（专辑），因为专辑是成体系的内容，更适合系统学习。

---

## 关键词匹配范围

| 内容类型 | 匹配关键词 |
|---------|-----------|
| 古诗国学 | 古诗、国学、三字经、弟子规、诗词、论语、唐诗 |
| 儿歌童谣 | 儿歌、童谣、宝宝、幼儿、启蒙 |
| 睡前故事 | 睡前、故事、童话、寓言 |
| 英语启蒙 | 英语、英文、启蒙、磨耳朵 |
| 科普百科 | 科普、十万个为什么、百科、知识 |
| 学科学习 | 语文、数学、拼音、识字、阅读 |

---

## 结果字段映射

从喜马拉雅 API 返回字段映射到统一元数据规范：

| 喜马拉雅字段 | 统一字段 | 说明 |
|-------------|---------|------|
| `id` | `resource_id` | 格式：`ximalaya:{id}` |
| `title` | `title` | 清理 HTML 高亮标记 |
| `url` | `source_url` | 规范化为 https 链接 |
| `intro` | `snippet` / `description` | 简介，截断 300 字 |
| `nickname` | `provider` | 主播昵称 |
| `play` | `play_count` / `view_count` | 播放量 |
| `score` | `score` | 评分（0-10） |
| `cover_path` | `cover_url` / `thumbnail_url` | 封面图 |
| `tracks` | `tracks_count` | 专辑集数 |
| `is_paid` | `is_paid` | 是否付费 |
| `is_v` | `is_verified_anchor` | 主播是否认证 |
| `is_finished` | `finished_status` | 已完结/连载中 |
| `tags` | `tags` | 标签列表 |
| `category_title` | `category_title` / `subject` | 分类 |

---

## 质量评分策略

遵循 `shared/schemas/quality-rubric.md` 五维评分标准，本平台自评逻辑：

| 维度 | 评分依据 | 加分规则 |
|------|---------|---------|
| 内容质量与完整性 | 评分 + 集数 | 评分≥9.5(+10)，集数≥50(+6) |
| 适龄匹配度 | 默认基础分 | 通过标题/分类推断主题 |
| 权威可信度 | 认证主播 | is_v=true(+6) |
| 可获取性 | 免费内容 | 免费(+4) |
| 安全与体验 | 播放量 | 千万(+18)/百万(+14)/十万(+10)/万(+6) |

基础分 60，满分 100。等级映射：S(≥90) / A(≥75) / B(≥60) / C(<60)。

---

## 反爬应对

### 平台反爬特点

喜马拉雅搜索接口**反爬较弱**，主要特点：
- 搜索 API 公开，无需登录/签名/设备指纹
- 有频率限制（高频请求可能被临时封 IP）
- 无验证码
- 无 IP 封禁（轻度限流）

### 应对策略

| 反爬类型 | 应对方法 | 对应错误码 |
|---------|---------|-----------|
| 频率限制 | 请求间隔 0.5 秒，分页时自动延时 | `ANTI_CRAWL_RATE_LIMITED` |
| 接口异常 | 降级到 M站镜像接口 | `NETWORK_REQUEST_FAILED` |

### 请求规范

- User-Agent：标准浏览器 UA（Chrome 131）
- 请求间隔：0.5 秒（分页搜索时）
- 最大并发：1（串行搜索）
- Cookie：可选（无 Cookie 也能完整搜索）

---

## 登录态管理

### 登录方式

**搜索功能无需登录。** 喜马拉雅搜索 API 是公开接口。

登录仅在以下场景需要：
- 获取个性化搜索结果
- 收藏/订阅专辑
- 收听 VIP 专享内容
- （未来）下载 VIP 音频

### Cookie / Token 管理

| 项目 | 说明 |
|------|------|
| 存储位置 | 环境变量 `XIMALAYA_COOKIE` 或 `--cookie` 参数 |
| 有效期 | 约 30 天（网页 Cookie） |
| 失效处理 | 搜索不受影响（公开接口）；VIP 内容需重新登录 |
| 获取方式 | 浏览器 F12 → Application → Cookies → 复制 `_xmLog` 等字段 |

### 权限分级

| 权限级别 | 可访问内容 | 对应错误码 |
|---------|-----------|-----------|
| 未登录 | 所有公开搜索结果、免费音频 | - |
| 已登录 | 上述 + 个性化推荐、收藏功能 | - |
| VIP 会员 | 上述 + VIP 专享音频 | `AUTH_MEMBER_ONLY`（不破解） |

---

## 依赖

| 依赖 | 用途 | 安装 |
|------|------|------|
| Python 3.10+ | 运行环境 | - |
| `shared.logger` | 统一日志 | 内置（项目共享） |
| httpx（可选） | HTTP 请求 | `pip install httpx`（无则降级 urllib） |

**无需浏览器、无需 Playwright、无需 ffmpeg（搜索阶段）。**

---

## 平台优势

> 📖 完整优势分析见 `../../shared/config/platform-advantages.md`

- **音频类首选**：古诗国学、儿歌、睡前故事、英语磨耳朵
- **内容丰富**：大量知名 IP（宝宝巴士、米小圈、凯叔讲故事等）
- **成体系**：专辑形式，适合系统学习
- **免费多**：大量免费内容可直接收听
- **技术友好**：搜索接口公开，反爬弱，接入成本低

---

## 参考资料

- `../../shared/schemas/resource-schema.md` - 资源元数据规范
- `../../shared/schemas/error-codes.md` - 统一错误码体系
- `../../shared/schemas/skill-contract.md` - 跨 Skill 上下文传递契约
- `platform-search-contract.md` - 平台搜索接口契约
- `../../shared/schemas/quality-rubric.md` - 质量评估标准
- `../../shared/config/platform-mapping.md` - 平台-Skill 映射表
- `../../shared/config/platform-advantages.md` - 平台优势图谱

---

*Skill 版本：v1.0（搜索能力）*
*架构版本：三层架构（平台执行层）*
