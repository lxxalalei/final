# scripts/ — 项目运维脚本

## healthcheck.py — 项目健康检查

对 `learning-resource-suite` 项目执行 5 类完整性检查，输出格式化报告。

### 检查内容

| 编号 | 检查项 | 说明 |
|------|--------|------|
| a | 目录结构完整性 | `shared/schemas/`、`shared/config/`、`platforms/` 等关键目录是否存在 |
| b | 文件存在性 | `resource-schema.md`、`error-codes.md`、`platform_base.py` 等关键文件是否到位 |
| c | 契约一致性 | 各 `SKILL.md` 中引用的 `shared/schemas/`、`shared/config/` 路径是否有效 |
| d | Python 依赖 | `shared/` 模块的 `import` 是否可解析（AST 静态分析 + 运行时导入） |
| e | 平台映射 | `platform-mapping.md` 中标记"可用"的平台是否有对应目录和 `SKILL.md` |

### 运行方式

```bash
# 标准检查（从项目根目录运行）
python scripts/healthcheck.py

# 只输出摘要（省略逐项详情）
python scripts/healthcheck.py --quiet

# 跳过第三方 pip 依赖检查（仅检查标准库 import）
python scripts/healthcheck.py --no-deps
```

### 输出说明

- ✅ **PASS** — 检查通过
- ⚠️ **WARN** — 有警告但不影响核心功能（如规划中平台尚未创建、第三方依赖未安装）
- ❌ **FAIL** — 检查未通过，需要修复

### 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 全部 PASS（允许 WARN） |
| 1 | 存在 FAIL 项 |

适合在 CI/CD 流水线或 Git pre-commit hook 中使用：

```bash
python scripts/healthcheck.py || { echo "健康检查未通过"; exit 1; }
```
