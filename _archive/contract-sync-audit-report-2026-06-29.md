# 契约同步审计报告（历史归档）

> 本报告对应六阶段架构改造前的旧契约，仅保留作历史参考。

> 审计时间：2026-06-29
> 审计范围：`shared/schemas/skill-contract.md` vs 5 个子 SKILL.md 的内联输出格式
> 审计方法：逐阶段、逐字段对比两份定义的"字段名 / 必选可选标记 / 类型 / 枚举值"

---

## 审计结论

共发现 **8 处不同步**，分为 3 个严重等级：

| 等级 | 数量 | 含义 |
|------|------|------|
| 🔴 严重（架构级） | 1 | 契约流程图与实际架构脱节，会导致理解歧义 |
| 🟠 中等（枚举值冲突） | 2 | 同一字段的合法取值在两份文档中不同 |
| 🟡 轻微（必选/可选标记不一致） | 5 | 同一字段在一处标必选、另一处标可选 |

---

## 逐项明细

### 🔴 严重 1：契约流程概览图缺失 resource-platforms 层

**位置**：`skill-contract.md` 第 13-17 行

**契约写的**：
```
resource-intent  →  resource-search  →  resource-selector  →  resource-downloader  →  library-manager
   阶段一              阶段二               阶段三                阶段四                  阶段五
 (查询指令包)        (候选列表)           (选定列表)            (下载结果)             (归档结果)
```

**实际架构**：
```
resource-intent → resource-search → resource-platforms(执行) → resource-selector → ...
   阶段一            阶段二             阶段二(执行)             阶段三
 (查询指令包)     (搜索任务计划)         (候选列表)             (选定列表)
```

**问题**：契约把 resource-search 标注为"(候选列表)"产出方，但 `resource-search/SKILL.md` 实际产出的是**搜索任务计划**（`search_tasks`），候选列表由 `resource-platforms` 执行搜索后才产出。契约的流程概览图没有反映 resource-platforms 这一层。

**影响**：人类开发者读契约时会对"阶段二到底产出什么"产生歧义。测试脚本如果按契约验证"阶段二输出包含 resources 数组"，会失败（实际输出的是 search_tasks）。

**建议**：更新契约流程概览图，反映 resource-platforms 中间层。

---

### 🟠 中等 2：`queries[].tier` 枚举值冲突

**位置**：`skill-contract.md` 第 31 行 vs `resource-search/SKILL.md` 第 248 行

| 文档 | tier 合法值 |
|------|------------|
| `skill-contract.md`（阶段一→二） | `core / official / format / longtail` |
| `resource-intent/SKILL.md`（data 部分） | `core / official / format / longtail` |
| `resource-search/SKILL.md`（search_tasks 内） | `core / important / supplementary` |

**问题**：intent 产出 `core/official/format/longtail`，但 search 在构造 search_tasks 时把 tier 改成了 `core/important/supplementary`。同一字段名 `tier`，在不同阶段的合法值不同。

**影响**：如果测试脚本校验 tier 值，需要知道校验的是哪个阶段的 tier。跨阶段传递时 tier 值发生了"翻译"，但契约没有定义这个翻译规则。

**建议**：要么统一枚举值，要么在契约中明确标注"阶段一 tier 值 = core/official/format/longtail；阶段二 search_tasks 内 tier 值 = core/important/supplementary"。

---

### 🟠 中等 3：`file_size` 类型冲突

**位置**：`skill-contract.md` 第 113 行 vs `resource-downloader/SKILL.md` 第 247 行 + `library-manager/SKILL.md` 第 153 行

| 文档 | file_size 类型 | 示例值 |
|------|---------------|--------|
| `skill-contract.md` | `number` | （字节） |
| `resource-downloader/SKILL.md` 输出格式示例 | `string` | `"1.2GB"` |
| `resource-downloader/SKILL.md` 写文件部分 | `number` | `156000000` |
| `library-manager/SKILL.md` 下载阶段字段示例 | `string` | `"1.2GB"` |

**问题**：同一个 downloader SKILL.md 内部就不一致——"输出格式"章节用字符串 `"1.2GB"`，"写文件"章节用数字 `156000000`。契约要求 number。

**影响**：AI 实际产出什么类型取决于它读到的是哪个示例。测试脚本如果按 number 校验，遇到字符串会失败。

**建议**：统一为 number（字节），展示层再格式化为人类可读的大小。

---

### 🟡 轻微 4：`difficulty` 必选/可选标记不一致

| 文档 | 标记 |
|------|------|
| `skill-contract.md`（阶段一→二） | ⚠️ 可选 |
| `resource-intent/SKILL.md`（data 部分） | ✅ 必选 |

**影响**：如果测试按契约（可选），不会校验缺失；但 intent SKILL.md 告诉 AI 必须写。实际产出中 difficulty 总会有值（AI 照 SKILL.md 写），所以影响不大。但定义不一致本身就是隐患。

---

### 🟡 轻微 5：`format_preferences` 必选/可选标记不一致

| 文档 | 标记 |
|------|------|
| `skill-contract.md`（阶段一→二） | ⚠️ 可选 |
| `resource-intent/SKILL.md`（data 部分） | ✅ 必选 |

---

### 🟡 轻微 6：`source_preference` 必选/可选标记不一致

| 文档 | 标记 |
|------|------|
| `skill-contract.md`（阶段一→二） | ⚠️ 可选 |
| `resource-intent/SKILL.md`（data 部分） | ✅ 必选 |

---

### 🟡 轻微 7：selector 期望的输入文件名与 search 产出不匹配

**位置**：`resource-selector/SKILL.md` 第 377 行

**selector 写的**：`上游文件名（通常 stage2_search.json）`

**实际**：search 产出的搜索计划文件通常叫 `stage2_search_plan.json`，resource-platforms 执行后产出的候选列表才可能是 `stage2_search.json`。但契约和各 SKILL.md 没有统一约定这个中间文件的命名。

**影响**：selector 去读 `stage2_search.json` 时可能找不到文件（如果 platforms 执行后的文件叫别的名字）。

---

### 🟡 轻微 8：`subject` 字段在 contract.md 阶段二定义为必选，但实际由平台产出

**位置**：`skill-contract.md` 第 58 行

**契约定义**：`resources[].subject` = ✅ 必选

**实际**：subject 字段由 resource-platforms 的搜索脚本产出。但 contract.md 阶段二的定义是"search → selector"的候选列表，没有提到 subject 的来源是 platforms 层。部分老平台（bilibili/douyin 等）的 subject 字段靠补偿层填充，可能为空。

**影响**：如果测试按契约校验 subject 必选，老平台的输出可能不通过。

---

## 汇总对照表

| # | 阶段 | 字段/问题 | contract.md | SKILL.md | 严重度 |
|---|------|----------|-------------|----------|--------|
| 1 | 全局 | 流程概览图 | 5 阶段无 platforms | 实际有 platforms 层 | 🔴 |
| 2 | 1→2 | tier 枚举值 | core/official/format/longtail | search 内 core/important/supplementary | 🟠 |
| 3 | 4→5 | file_size 类型 | number | string "1.2GB" | 🟠 |
| 4 | 1→2 | difficulty | ⚠️可选 | ✅必选 | 🟡 |
| 5 | 1→2 | format_preferences | ⚠️可选 | ✅必选 | 🟡 |
| 6 | 1→2 | source_preference | ⚠️可选 | ✅必选 | 🟡 |
| 7 | 2→3 | 输入文件名 | 未约定 | selector 期望 stage2_search.json | 🟡 |
| 8 | 2→3 | subject 来源 | 必选，未标注来源 | 由 platforms 补偿层填充 | 🟡 |

---

## 修复建议（按优先级）

### P0：修复流程概览图（#1）

更新 `skill-contract.md` 第 13-17 行的流程概览图，加入 resource-platforms 层：

```
resource-intent  →  resource-search  →  resource-platforms  →  resource-selector  →  resource-downloader  →  library-manager
   阶段一              阶段二               阶段二(执行)            阶段三                阶段四                  阶段五
 (查询指令包)        (搜索任务计划)         (候选列表)           (选定列表)            (下载结果)             (归档结果)
```

同步补充"阶段二(执行) → 阶段三"的契约定义（候选资源列表，其实已存在于当前 contract.md 第 46-76 行，只是概览图没反映）。

### P1：统一 tier 枚举值或明确翻译规则（#2）

两个选项：
- **选项 A（统一）**：全局统一为 `core/official/format/longtail`，search SKILL.md 内的 search_tasks 也用这套值
- **选项 B（明确翻译）**：在契约中增加翻译规则章节

推荐选项 A，减少认知负担。

### P2：统一 file_size 类型为 number（#3）

修改所有 SKILL.md 中 `file_size` 的字符串示例为数字，展示层负责格式化。

### P3：对齐必选/可选标记（#4 #5 #6）

以 SKILL.md 为准（difficulty/format_preferences/source_preference 改为必选），更新 contract.md。

### P4：统一文件命名约定（#7）

在 contract.md 或 session-io-spec.md 中明确约定各阶段文件的命名。

---

## 根因分析

这些不同步的根本原因是上一轮记忆分析中指出的：

> **"对 AI 是'建议看'（软约束），对测试是'必须满足'（硬约束）。契约的权威性实际由 Python 测试背书。"**

因为 AI 实际照 SKILL.md 内联格式写字段，不看 contract.md，所以两份文档各自演化时没有人发现它们已经漂移了。测试脚本只校验 contract.md 定义的子集，也不覆盖枚举值/类型级别的一致性。

**根治方案**：写一个 `contract_drift_check.py`，自动解析 contract.md 表格和各 SKILL.md 的输出格式章节，对比字段名/类型/必选标记/枚举值是否一致，纳入 CI。
