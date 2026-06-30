# 资源元数据生命周期

资源字段随六阶段逐步增加。除 selector 筛除未入选资源外，下游不得删除上游已有字段。

## Stage 3：平台原始结果

技术必填：

| 字段 | 类型 | 说明 |
|---|---|---|
| `resource_id` | string | `{platform}:{平台内 ID}` |
| `platform` | string | 小写平台标识 |
| `title` | string | 标题 |
| `source_url` | string | 原始来源地址 |

推荐但允许为空：

- `platform_resource_id`
- `type`
- `description`
- `author`
- `duration`
- `publish_time`
- `is_free`
- `language`
- `thumbnail_url`
- `download_feasibility`
- `platform_signals`
- `raw_metadata`

Stage 3 不应包含最终 `quality_score` 或 `quality_level`。旧平台返回同名字段时，将其移入 `platform_signals.native_score` 或 `raw_metadata`，避免与 selector 评分混淆。

## Stage 4：筛选与选择

Selector 在保留 stage 3 全部字段的基础上追加：

| 字段 | 类型 | 说明 |
|---|---|---|
| `quality_score` | number | 统一评分，0-100 |
| `quality_level` | string | `S` / `A` / `B` / `C` |
| `quality_dimensions` | object | 分维度得分 |
| `assessment_notes` | array | 推断、证据不足或风险说明 |
| `possible_duplicate` | boolean | 无法确定时的相似内容标记 |

只有用户确认的资源进入 `stage4_selection.json:data.resources`。

## Stage 5：下载

Downloader 追加：

- `download_status`：`success` / `degraded` / `failed`
- `degraded_level`：`Level 0` 至 `Level 3`
- `file_path`
- `file_size`：字节数，number
- `fetch_time`
- `fetch_method`
- `error_code`、`error_message`
- `degraded_content`

失败资源也必须保留。

## Stage 6：归档

Library manager 追加：

- `library_path`
- `archive_time`
- `dedup_status`：`new` / `duplicate` / `skipped`

## 平台标识

当前标准值：`bilibili`、`smartedu`、`zhihu`、`douyin`、`weibo`、`ximalaya`、`open163`、`generic`。
