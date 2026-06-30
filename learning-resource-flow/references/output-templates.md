# Flow 输出模板

## Stage 4：候选展示

```text
搜索执行完成：{success_platform_count} 个平台成功，{failed_platform_count} 个失败。
原始有效结果 {raw_count} 条；去重 {duplicates_removed} 条；业务过滤 {business_filtered} 条；合格候选 {candidate_count} 条。

1. {title}
   来源：{platform} · 类型：{type} · 质量：{quality_level}（{quality_score}）
   下载可行性：{download_feasibility}
   说明：{assessment_summary}

请输入编号、筛选条件、“全部”或“查看更多”。确认后才会下载。
```

平台失败必须单独说明，不要合并到过滤数量。

## Stage 5：下载进度

```text
下载进度：{completed}/{total}
成功 {success_count} · 降级 {degraded_count} · 失败 {failed_count}
当前：{title} — {status}
```

降级时补充 `degraded_level` 和缺失内容；失败时给出可理解的原因，不暴露 Cookie、token 或内部堆栈。

## Stage 6：最终汇总

```text
处理完成。

成功获取：{success_count}
降级保存：{degraded_count}
下载失败：{failed_count}
已归档：{archived_count}
重复跳过：{skipped_count}
资料库位置：{library_root}
```

按“成功、降级、失败、归档跳过”分组列出资源。每条至少包含标题、来源、最终状态和本地路径或来源链接。

## 无候选

```text
本次从 {platform_count} 个平台取得 {raw_count} 条原始结果，但筛选后没有符合当前条件的候选。
主要原因：{top_filter_reasons}

可以调整关键词、增加平台，或明确放宽费用/语言/质量条件。
```
