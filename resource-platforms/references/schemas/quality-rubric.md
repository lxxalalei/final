# 平台质量信号边界

最终质量过滤、评分和 S/A/B/C 定级已迁移到 `resource-selector/references/quality-rubric.md`。

平台层只采集可验证的原始信号，例如播放量、点赞量、作者认证、资源时长、是否免费、发布时间和平台原生评分，并写入 `platform_signals`。

平台层不得：

- 根据这些信号执行跨平台最终评分。
- 因低热度或平台自评分较低而删除结果。
- 把平台原生评分写成最终 `quality_score` 或 `quality_level`。

平台脚本因兼容性仍返回旧质量字段时，归一化阶段将其保存在 `platform_signals.native_score` 或 `raw_metadata`，交给 selector 判断。
