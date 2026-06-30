# Generic 通用搜索

- Adapter：`scripts/generic/adapter.py`
- 认证：无
- 引擎：百度、Bing，必须同时执行
- 参数：`engines`，固定包含 `baidu`、`bing`

适合网页、公开文档、长尾资料和未直接接入的站点。Adapter 内部并行请求两个引擎，按规范化 URL 去重。验证码、安全验证或单引擎失败必须作为错误保留；另一引擎成功时仍返回有效结果。
