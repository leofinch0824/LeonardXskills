# Paper Trail 优化开发计划

## 1. 背景与结论

`paper-trail` 当前采用“业务痛点 → 学术问题 → 检索池 → 分层决策 → 结构化抽取 → 综合 → 验证与简报”的七阶段流程，并通过阶段闸门、API identifier 约束、事实引用、空结果作证和可适用性分档建立可追溯证据链。

整体架构合理，本轮不重写主流程，重点修复以下执行一致性和可移植性问题：

1. Landscape 获得更准确术语后，缺少既能校准检索词、又不破坏已确认 Intake 的机制。
2. T0/T1 只有上限，没有针对论文池过薄和原子问题覆盖不足的有界补检策略。
3. Worker 已经具备外部端点安全保护，但 Preflight 只报告是否配置，未明确展示端点边界类型。
4. 默认 Profile 和 Extract 规则包含 `4×H20`、`30B/70B`、PCB 兴趣等个人化假设，会污染其他工作区。
5. Profile 回灌条件缺少明确边界，可能把模型推断写成长期用户事实。
6. `ledger.md` 虽记录 token，但缺少标准化汇总和跨轮次消费点。

> 说明：`extract_paper.py` 已强制执行数据边界保护——外部端点不带 `--desensitized` 会退出，外部 HTTP 即使带该参数也会被拒绝。因此本轮不补做已有安全机制，只统一分类逻辑并增强 Preflight 可见性。

---

## 2. 开发目标与范围

### 2.1 目标

本轮实现以下目标：

1. Landscape 阶段能够校准检索词，但不静默修改用户已经确认的 Intake。
2. 论文池过薄或原子问题覆盖不足时，自动执行一次有界补检。
3. Preflight 明确报告 worker 端点的数据边界类型，并与 Extract 共用相同判断逻辑。
4. Profile 不再携带个人化硬编码，也不接受模型主观推断式回灌。
5. Ledger 产生可跨轮次比较的效率指标，但不混入论文质量闸门。
6. 用自动化测试锁定上述契约。

### 2.2 不在本轮范围内

- 不重写七阶段流程。
- 不改变论文搜索后端。
- 不实现端到端自动论文调研集成测试。
- 不增加新的 Python 第三方依赖。
- 不改变 `extract_paper.py` 使用的 OpenAI-compatible API 协议。
- 不自动判断正文是否真正完成脱敏；该确认仍由执行者负责。

---

## 3. 功能包一：修正 Profile 的可移植性

### 3.1 涉及文件

- `paper-trail/templates/profile.md`
- `paper-trail/reference/extract.md`
- `paper-trail/SKILL.md`

### 3.2 修改默认 Profile

从 `templates/profile.md` 移除以下个人化默认值：

- `4×H20`
- 全参微调约 `30B`
- `>70B` 判定超算力
- PCB 多模态参数抽取
- Prompt 优化闭环兴趣
- 默认允许微调
- 默认允许脱敏后调用外部 API

改为中性占位值，例如：

```markdown
## 硬约束

- 微调能力：TBD
- 算力预算：TBD
- 权重要求：TBD
- 数据出域规则：TBD
- 延迟要求：TBD
- License 限制：TBD
```

Intake 闸门只要求补齐与本轮候选方案判定有关的 TBD，不要求用户一次性填写所有字段。

### 3.3 修改 Extract 四档定义

把 `reference/extract.md` 中固定的硬件和模型规模判定改为相对 Profile 的定义：

- **直接可用**：满足 Profile 中的部署、权重、数据和资源约束。
- **需微调（算力内）**：论文所需训练资源在 Profile 上限内。
- **API 辅助（脱敏后）**：Profile 明确允许数据出域，并满足脱敏要求。
- **不适用**：与 Profile 中任一硬约束明确冲突。

新增临时状态规则：

> Profile 相关约束为 TBD 时，不得自行假设满足；抽取卡先标记“待确认”，并在 Brief 开放问题中列出。Stage 5 闸门前应将其解析成四档之一，否则作为未过闸项处理。

这样可以避免模型为了满足固定四档而虚构用户约束。

### 3.4 结构化 Profile 回灌

在 `templates/profile.md` 增加：

```markdown
## 增量更新记录

| 日期 | 调研运行 | 变更字段 | 旧值 | 新值 | 依据 |
|---|---|---|---|---|---|
```

仅允许以下内容进入 Profile：

1. 用户在 Intake 中明确提供或修改的约束；
2. 用户明确补齐了一个原为 TBD 的值；
3. 用户明确要求长期记录的兴趣或偏好。

以下内容不得直接写入 Profile：

- 模型从论文选择中推断出的“用户兴趣”；
- 因某类论文被降档而推断出的新约束；
- 仅对本轮痛点有效的临时条件。

Triage 或 Extract 发现可能的新约束时，只能写入 `06-brief.md` 的“待确认事项”；得到用户确认后，下一轮再进入 Profile。

### 3.5 验收标准

- 新工作区 bootstrap 后不再默认获得 PCB、4×H20 等个人信息。
- Extract 判定只引用当前 Profile 值。
- Profile 每次增量变更都有日期、运行目录和明确依据。
- 模型不得把推断写成长期用户事实。

---

## 4. 功能包二：Landscape 术语校准，同时冻结 Intake

直接在 Landscape 后修改 `00-intake.md` 不合适，因为 Intake 是用户确认过的范围合同。采用以下契约：

- Intake 保存用户确认的基线；
- Landscape 保存派生检索词；
- Discovery 使用两者并集；
- 如果 Landscape 改变问题语义而非仅扩展同义词，则重新打开 Intake 闸门。

### 4.1 涉及文件

- `paper-trail/SKILL.md`
- `paper-trail/reference/reframe.md`
- `paper-trail/reference/backends.md`
- `paper-trail/templates/intake.md`
- `paper-trail/templates/landscape.md`
- `paper-trail/templates/pool.md`

### 4.2 修改 Intake 契约

在 Intake 确认区增加状态：

```markdown
## 用户确认

- 状态：待确认 / 已确认并冻结 / 重新打开
- 确认日期：
- 用户修改记录：
- 重新打开原因：
```

规则：

- 用户确认后，原始痛点和原子问题视为冻结。
- 后续阶段不得静默修改原子问题。
- 单纯增加同义词或 taxonomy 术语不需要重新确认。
- 若 Landscape 发现原子问题的含义、边界或拆分方式错误，则将状态改为“重新打开”，回到 Intake 请求确认。

将“全程唯一人工交互点”调整为：

> Intake 是唯一的计划内人工交互点；若后续证据表明问题范围发生实质变化，必须重新打开 Intake，而不是静默修改已确认内容。

### 4.3 增加 Landscape 术语校准表

在 `templates/landscape.md` 增加：

```markdown
## Intake 词表校准

| 衍生术语 | 来源 [paper-id] | 对应原子问题 | 类型 | 后续动作 |
|---|---|---|---|---|
| | | | 同义扩展 / taxonomy 节点 / 语义修正 | 纳入 Discovery / 重开 Intake |
```

Landscape 闸门增加：

- 已逐项比较 Intake 词表与 Survey/Benchmark 术语；
- 同义扩展已经记录；
- Discovery 将使用“Intake 已确认词 + Landscape 衍生词”；
- 若发现语义修正，Intake 已重新获得确认；
- 不直接覆盖已确认的 Intake 内容。

### 4.4 增加查询词来源追踪

Discovery 查询记录增加“词来源”字段：

```markdown
| 来源后端 | 查询词 | 词来源 | 返回数 | 有效候选数 | 降级/异常 |
|---|---|---|---|---|---|
```

词来源限定为：

- `Intake`
- `Landscape`
- `Snowballing`
- `补检`

这样可以判断 Landscape 校准是否真正改善召回。

### 4.5 验收标准

- Landscape 能扩展检索词。
- 已确认 Intake 不会被后台静默修改。
- 实质范围变化一定重新进入用户确认。
- Pool 中每次查询能追踪到检索词来源。

---

## 5. 功能包三：论文池过薄时执行一次有界补检

只设置“T0+T1 至少 5 篇”并不充分：窄领域可能确实只有少量论文，而有 5 篇也不代表所有原子问题都被覆盖。因此使用“数量 + 问题覆盖 + 后端完整性”组合判定。

### 5.1 涉及文件

- `paper-trail/SKILL.md`
- `paper-trail/reference/triage.md`
- `paper-trail/templates/triage.md`
- `paper-trail/templates/pool.md`

### 5.2 定义 `POOL_THIN`

满足任一条件即标记 `POOL_THIN`：

1. T0 + T1 合计少于 5 篇；
2. 任一 Intake 原子问题没有直接相关的 T0/T1；
3. 某个原子问题只有 abstract-only 或单一来源证据；
4. Discovery 因关键后端不可用而明显收缩，且没有执行对应降级检索。

其中 5 篇是软阈值，不是最终交付的硬下限。

### 5.3 增加一次有界补检

触发 `POOL_THIN` 后，只允许补检一次，避免无限循环。补检按顺序执行：

1. 使用 Landscape 衍生词重新查询；
2. 增加同义词或上位 taxonomy 节点；
3. 近期窗口从 24 个月放宽到 48 个月；
4. 奠基作仍不限制年代；
5. 对现有高相关论文执行前向/后向 snowballing；
6. 记录每个补检查询的返回数和新增候选数。

补检结束后只有两种状态：

- `resolved`：不再满足 `POOL_THIN`；
- `accepted-thin`：仍然过薄，但已有充分检索证据，可以继续并在 Brief 中警告。

不得执行第二次自动补检。

### 5.4 修改 Triage 模板

新增：

```markdown
## 论文池充分性

- T0 数：
- T1 数：
- 无直接证据的 Intake 问题：
- 关键后端缺失：
- 判定：sufficient / POOL_THIN
- 补检状态：未触发 / resolved / accepted-thin
- 补检记录：见 02-pool.md 对应行
- accepted-thin 理由：
```

Triage 闸门增加：

- 所有原子问题均有候选覆盖情况；
- `POOL_THIN` 已补检一次；
- 补检后仍过薄时，已记录 `accepted-thin` 依据；
- 不因篇数少而虚假晋级低相关论文。

### 5.5 验收标准

- 少于 5 篇或存在问题覆盖空洞时，触发一次补检。
- 补检最多一次。
- 不会为了满足篇数而把不相关论文升到 T1。
- 空结果和薄结果都能携带充分检索证据交付。

---

## 6. 功能包四：统一 Worker 端点分类并由 Preflight 报告

现有安全执行是有效的：

- 外部端点必须显式传 `--desensitized`；
- 外部 HTTP 被拒绝；
- localhost、内网 IP、`.local`、`.internal` 和可信主机视为内部端点。

本功能包解决的是：相同规则应由 Preflight 提前展示，并避免 Preflight 与 Extract 未来各自维护一套判断。

### 6.1 涉及文件

- `paper-trail/scripts/worker_boundary.py`（新增）
- `paper-trail/scripts/extract_paper.py`
- `paper-trail/scripts/preflight.py`
- `paper-trail/reference/backends.md`
- `paper-trail/SKILL.md`
- `tests/test_paper_trail.py`

### 6.2 提取共享端点分类模块

新增 `paper-trail/scripts/worker_boundary.py`，提供纯函数：

```python
classify_worker_endpoint(base_url, trusted_hosts)
```

分类结果之一：

- `unconfigured`
- `invalid`
- `trusted-local`
- `external-https`
- `external-http-blocked`

同时返回结构化信息：

```json
{
  "classification": "external-https",
  "trusted": false,
  "requires_desensitized": true,
  "transport_allowed": true
}
```

不得在报告中输出 worker key。

### 6.3 改造 `extract_paper.py`

改为调用共享分类函数，同时保持现有 CLI 行为和错误信息兼容：

- `trusted-local`：允许调用；
- `external-https`：必须传 `--desensitized`；
- `external-http-blocked`：始终拒绝；
- `invalid`：拒绝。

### 6.4 增强 Preflight 报告

JSON 增加独立详情，同时保留现有 `capabilities.worker` 布尔值，避免破坏已有消费者：

```json
{
  "capabilities": {
    "worker": true
  },
  "details": {
    "worker_endpoint": {
      "classification": "external-https",
      "requires_desensitized": true,
      "transport_allowed": true
    }
  }
}
```

状态处理：

- 未配置：`degraded`，走 subagent 降级梯；
- 配置不完整：`degraded`，列出缺失的变量名；
- `external-http-blocked`：worker capability 为 false，整体仍可继续 degraded；
- `external-https`：worker 可用，但明确提示抽取时需要脱敏确认；
- `trusted-local`：worker 可用，不要求 `--desensitized`。

文本输出示例：

```text
- worker endpoint: external-https
- worker data boundary: --desensitized required
```

Worker 不可用不升级为 `blocked`，因为现有 Extract 有合法降级梯。

### 6.5 更新包完整性清单

新增脚本后同步修改：

- `preflight.py` 的 `REQUIRED_SKILL_FILES`
- `tests/test_paper_trail.py` 的包文件清单

### 6.6 验收标准

- Preflight 在不发起真实抽取调用的情况下报告端点类型。
- Preflight 与 Extract 使用同一个分类实现。
- 不打印密钥。
- 现有外部 HTTPS、外部 HTTP 和本地端点保护行为不回归。
- Worker 不可用仍然是 degraded，而不是错误阻断整个 Skill。

---

## 7. 功能包五：让 Ledger 可比较，但不污染质量记分卡

覆盖度、引用密度等属于调研质量，token/篇属于运行成本。成本高不等于调研不及格，因此不把 token 效率直接加入质量记分卡，而是列为非闸门运行指标。

### 7.1 涉及文件

- `paper-trail/templates/ledger.md`
- `paper-trail/templates/brief.md`
- `paper-trail/reference/verify.md`
- `paper-trail/SKILL.md`

### 7.2 标准化 Ledger 汇总

在 `templates/ledger.md` 增加：

```markdown
## 汇总指标

| 指标 | 值 | 计算方式 |
|---|---|---|
| 总 token | | 各阶段合计 |
| Discovery 候选数 | | 02-pool 去重后候选 |
| T0+T1 篇数 | | 03-triage |
| 完成抽取卡数 | | 04-extractions |
| 每篇抽取卡 token | | extract token / 抽取卡数 |
| 每篇入选论文总 token | | 总 token / (T0+T1) |
| 不可计量阶段 | | 无 usage 数据时列出 |
```

规则：

- 有 API usage 时使用实际数据；
- 无法获取时写“不可得”，不得假造精确值；
- agent token 只能估算时明确标注“估算”；
- 分母为 0 时写 `N/A`。

### 7.3 在 Brief 中消费指标

保留质量记分卡不变，在其下增加：

```markdown
## 运行指标（非质量闸门）

| 总 token | T0+T1 | 抽取卡数 | 每篇抽取卡 token | 每篇入选论文总 token |
|---|---|---|---|---|
```

在 `verify.md` 明确：

- 运行指标不参与及格/不及格；
- 用于连续 2–3 轮后比较成本；
- 如果 token 升高但覆盖度没有提升，应检查 Discovery 并发数量和 Extract 正文范围；
- 如果无法计量，不影响调研质量交付，但必须标注缺失。

### 7.4 验收标准

- `ledger.md` 的数据在 Brief 中有消费点。
- 质量记分卡算法不因成本指标改变。
- 不可得数据不会被伪造。
- 连续调研可以比较单位抽取成本。

---

## 8. 自动化测试计划

主要修改 `tests/test_paper_trail.py`。

### 8.1 Profile 可移植性测试

新增断言：

- 默认 profile 不包含 `4×H20`、`30B`、`70B` 等固定资源。
- 默认 profile 不预置 PCB 兴趣。
- 默认 profile 含必要的 TBD 字段。
- `reference/extract.md` 不再用固定硬件决定四档。
- Profile 含增量更新记录 schema。

注意：`reference/reframe.md` 中的 PCB 内容是教学案例，可以保留，不做全包级“禁止 PCB”断言。

### 8.2 Worker 分类单元测试

覆盖：

1. localhost HTTP → `trusted-local`
2. 私网 IP → `trusted-local`
3. `.internal` → `trusted-local`
4. `PAPER_TRAIL_WORKER_TRUSTED_HOSTS` → `trusted-local`
5. 外部 HTTPS → `external-https`
6. 外部 HTTP → `external-http-blocked`
7. 无效 URL → `invalid`
8. 未配置 → `unconfigured`

### 8.3 Preflight CLI 测试

验证 JSON 报告：

- 外部 HTTPS 报告 `requires_desensitized: true`；
- 外部 HTTP 将 worker capability 设为 false；
- 不完整配置列出缺失变量；
- 不会把 key 写到 stdout/stderr；
- 现有 path、bootstrap 和 relocated-skill 测试继续通过。

### 8.4 Extract 回归测试

保留并验证现有测试：

- 本地 worker 可调用；
- 外部 worker 缺少 `--desensitized` 被拒绝；
- 外部 HTTP 即使脱敏也被拒绝；
- 超过 120,000 字符拒绝静默截断；
- usage 正常输出到 stdout。

### 8.5 Markdown 契约测试

新增轻量契约断言：

- Landscape 模板包含“Intake 词表校准”；
- Intake 模板包含冻结/重开状态；
- Triage 模板包含 `POOL_THIN` 和补检状态；
- Pool 查询记录包含词来源；
- Ledger 包含单位成本；
- Brief 将运行指标标为非质量闸门；
- SKILL 主流程与各 reference 使用相同状态名称。

测试只锁定关键标题和状态名，不对整段文案做精确字符串匹配，避免过度脆弱。

---

## 9. 实现顺序

### 第 1 步：先写契约测试

先为以下行为添加失败测试：

- Profile 无个人化默认值；
- Worker 端点分类；
- 新模板章节存在；
- Preflight JSON 含端点详情。

这样可以防止文档和代码各自演化。

### 第 2 步：修复 Profile 与 Extract 规则

优先解决会直接影响论文适用性判断的硬编码问题：

- 修改 `templates/profile.md`
- 修改 `reference/extract.md`
- 修改 `SKILL.md` 的 Intake/Profile 规则

### 第 3 步：实现共享 Worker 分类

- 新增 `worker_boundary.py`
- 重构 `extract_paper.py`
- 改造 `preflight.py`
- 更新 `reference/backends.md`

完成后立即运行 worker 与 preflight 测试。

### 第 4 步：实现 Landscape、Discovery 和 Triage 流程改造

- 冻结 Intake；
- 增加 Landscape 衍生词；
- Pool 记录词来源；
- 增加 `POOL_THIN`；
- 增加一次有界补检和 `accepted-thin`。

这一步主要是 Skill 契约和模板修改，不需要新增运行时代码。

### 第 5 步：标准化 Ledger

- 修改 `templates/ledger.md`
- 修改 `templates/brief.md`
- 修改 `reference/verify.md`
- 在 `SKILL.md` Stage 7 中明确汇总动作

### 第 6 步：全量验证

执行：

```bash
python3 -m unittest discover -s tests -v
```

然后做两次 CLI smoke test：

```bash
python3 paper-trail/scripts/preflight.py \
  --workspace-root <临时工作区> \
  --bootstrap \
  --json
```

分别模拟：

- worker 未配置；
- 外部 HTTPS worker 已配置。

最后检查：

- bootstrap 不覆盖现有 profile；
- JSON 不泄露 key；
- 新增脚本被包完整性检查覆盖；
- Git diff 中没有安装机器的绝对路径。

---

## 10. 预计文件变更

预计修改约 13 个文件，新增 1 个脚本：

```text
paper-trail/
├── SKILL.md
├── scripts/
│   ├── extract_paper.py
│   ├── preflight.py
│   └── worker_boundary.py          # 新增
├── reference/
│   ├── backends.md
│   ├── extract.md
│   ├── reframe.md
│   ├── triage.md
│   └── verify.md
└── templates/
    ├── brief.md
    ├── intake.md
    ├── landscape.md
    ├── ledger.md
    ├── pool.md
    ├── profile.md
    └── triage.md

tests/
└── test_paper_trail.py
```

---

## 11. 完成定义

本轮优化只有同时满足以下条件才算完成：

1. 所有既有测试通过；
2. 新增端点分类和 Markdown 契约测试通过；
3. 新工作区不继承任何个人算力、数据或兴趣假设；
4. Intake 被确认后不会被 Landscape 静默改写；
5. `POOL_THIN` 最多触发一次自动补检；
6. 薄结果可以通过 `accepted-thin` 携带证据交付；
7. Preflight 和 Extract 使用相同的 worker 边界判定；
8. 外部 HTTP 继续被拒绝，外部 HTTPS 继续要求脱敏确认；
9. Ledger 指标在 Brief 中可见，但不参与质量及格判定；
10. 文档状态名、模板字段和脚本输出保持一致。
