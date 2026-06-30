# Generic 通用网页搜索

## 能力

- 同一查询固定请求百度和 Bing。
- 合并两个引擎的结果，并按规范化 URL 去重。
- 支持普通关键词以及 Search 生成的 `site:`、`filetype:` 查询。
- 不需要登录，不提供下载能力。

## 边界

通用搜索用于发现跨站、长尾和具体文件资料。搜索引擎排名不等于资源质量，结果中的相关性、适龄性、费用、来源可靠性和安全性全部由 Selector 判断。

任一搜索引擎失败时保留另一引擎结果，并在 `errors` 中记录失败；两个引擎都失败时返回结构化空结果，不能伪装成“确实没有结果”。

## 命令

```bash
python scripts/generic/generic_search.py search "三年级数学 练习题" \
  --engines baidu,bing --max 20 -o /tmp/generic-search.json
```
