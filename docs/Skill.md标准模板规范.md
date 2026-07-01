# Skill 目录与职责规范

## 目标

Skill 依靠模型完成语义理解和动态决策，同时用契约、校验器和案例保证阶段产物稳定。不要把所有规则都堆入 SKILL.md，也不要用 Schema 取代模型推理。

## 标准目录

```text
skill-name/
├── SKILL.md
├── schemas/
│   ├── input.schema.json
│   └── output.schema.json
├── scripts/
│   └── validate_output.py
├── references/
│   ├── domain-rules.md
│   └── strategy.md
└── examples/
    └── golden-cases.json
```

按需创建目录；没有确定性逻辑时可以没有 scripts。不要创建 README、安装指南、建议版 SKILL 或同义重复参考文件。

## 文件职责

### SKILL.md

只保留模型执行时必须掌握的内容：

- 触发边界和职责。
- 输入、输出和版本。
- 推理原则。
- 动态决策步骤。
- 需要读取哪些 reference。
- 何时运行校验器。
- 失败、澄清和完成条件。

建议控制在 250 行以内。Frontmatter 只包含 `name` 和 `description`。

### schemas

定义字段名、类型、枚举、必填关系和版本。Schema 不描述复杂语义判断，不把主题路由或澄清策略写成僵硬枚举。

### scripts

处理确定性检查：

- JSON 是否可解析。
- Schema 版本和字段是否合法。
- ID 和计数是否一致。
- 是否选择不存在的平台。
- 是否丢失 must/exclude 约束。

校验器不得替模型推断用户意图。

### references

保存领域规则、平台特点和策略启发式。一个主题只保留一个权威文件；SKILL.md 明确什么时候加载。不要同时维护“完整版、建议版、速查版”而没有生成关系。

### examples

保存自然语言 golden cases 和结构化期望。重点验证关键语义和不变量，不要求模型逐字输出固定文本。

## 阶段文件

统一使用：

```json
{
  "_meta": {
    "schema_version": "intent-brief/v1",
    "session_id": "...",
    "created_at": "ISO 8601"
  },
  "_summary": {},
  "data": {}
}
```

- `_meta`：只保留版本、会话和写入时间；阶段、写入者和上游可由固定文件关系确定。
- `_summary`：仅在 Flow 需要快速读取状态或计数时使用；没有调度信息的阶段省略。
- `data`：下游需要的完整阶段产物。

不要在 `data` 重复版本，不要复制上游对象，不要保存展示统计或没有消费者的模型思考字段。`_summary` 中的计数必须能从 `data` 核对。生产者负责定义输出契约；消费者必须先校验版本。

## 模型与确定性逻辑边界

交给模型：

- 自然语言理解。
- 歧义识别。
- 语义推断和动态默认。
- 查询生成、平台组合和策略理由。
- 质量判断中需要综合语境的部分。

交给确定性逻辑：

- 文件、字段、枚举和版本。
- 平台是否真实可执行。
- ID、数量和约束透传。
- 文件写入后的完整性检查。

## 修改检查清单

1. 职责是否只属于一个 Skill。
2. 是否存在同义字段或冲突枚举。
3. SKILL.md 是否引用了不存在或重复的参考文件。
4. 模型推理结果是否有 evidence、status 或 reason。
5. 输出是否经过校验。
6. 是否有正向、歧义、冲突和边界 golden cases。
7. 下游是否明确支持当前 schema 版本。
