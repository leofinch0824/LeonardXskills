# Learn Loop Stage Contract Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended when explicitly authorized) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Implementation status (2026-08-05):** Tasks 1–9 and the deterministic Task 10 gates are implemented. Repeated fresh-context, multi-model content-quality sampling remains explicitly pending; see `learn-loop-format-contract-eval-results.md`.

**Goal:** Replace Learn Loop's hidden and contradictory format rules with disclosed stage contracts, progressive context packages, deterministic validation, retained multi-agent evidence, reliable Mode B/C records, and build-time Markdown-to-HTML rendering.

**Architecture:** `reference/stages/` owns executable stage semantics, `templates/` owns Markdown serialization, and a shared `contract_io.py` parser is used by preparation, validation, reference resolution, state mutation, and rendering. `prepare_stage.py` gates stages and emits self-contained current-stage context; `finalize_run.py` validates, renders, records review metadata, and only then marks the run complete.

**Tech Stack:** Python 3.11+, Poetry, standard-library `unittest`, `markdown-it-py` with raw HTML disabled, Markdown/HTML/CSS/JavaScript.

## Global Constraints

- Do not modify `skills/learn-loop/reference/original-prompts.md`; verify its implementation diff is empty.
- Implement only the latest contract; do not add legacy branches or migrate old run directories.
- Preserve unrelated user changes, especially the existing `TOPIC_SUB`/`.h1-sub` HTML contract and tests.
- Markdown remains the only learning fact source; HTML is a derived static view.
- Validators are read-only and return structured errors; they never auto-fix files.
- Narrative sections remain free text unless the final design explicitly defines fields, enums, counts, or references.
- Use Poetry for dependency changes and update both `pyproject.toml` and `poetry.lock` together.
- Do not commit unless the user explicitly asks; each task ends with a verification checkpoint instead.
- The normative design is `docs/plans/learn-loop/learn-loop-format-contract-gap-analysis.md`.

---

## File Map

### Create

- `skills/learn-loop/reference/stages/00-run-state.md` through `10-cheatsheet.md`: one executable semantic contract per Mode A stage.
- `skills/learn-loop/reference/modes/exam-record.md`: Mode B state and transaction contract.
- `skills/learn-loop/reference/modes/feynman-record.md`: Mode C state and transaction contract.
- `skills/learn-loop/templates/perspective-role.md`: canonical retained role output.
- `skills/learn-loop/templates/perspective-task.md`: self-contained role-agent task packet.
- `skills/learn-loop/scripts/contract_io.py`: shared Markdown parser, reference resolver, structured errors, run-state parsing, and atomic writes.
- `skills/learn-loop/scripts/prepare_stage.py`: stage gate, template materialization, current-stage context disclosure, role packets, and batch gates.
- `skills/learn-loop/scripts/render_learning_page.py`: validated Markdown-to-HTML build and cross-file reference expansion.
- `skills/learn-loop/scripts/finalize_run.py`: transactional Mode A completion and idempotent external registration.
- `tests/fixtures/learn-loop/`: minimal valid and invalid contract fixtures, including frozen DeepSeek-shaped failures.

### Modify

- `skills/learn-loop/SKILL.md`: concise orchestration, triggers, mode boundaries, commands, and pointers.
- `skills/learn-loop/reference/{perspectives,conflict,curriculum,examination,retention,html-guide}.md`: retain judgment guidance and point exact shapes to stage/mode contracts.
- `skills/learn-loop/templates/{run-state,01-perspectives,02-conflicts,03-brief,04-review,05-resources,06-ladder,07-sprint,08-exam-bank,08-exam-record,09-feynman-notes,09-feynman-record,10-cheatsheet}.md`: serialize the final contracts.
- `skills/learn-loop/scripts/{preflight,validate_stage,review_queue}.py`: package completeness, shared parsing, structured validation, and idempotency.
- `skills/learn-loop/assets/template.html`: only add renderer-required stable slots; retain existing topic subtitle structure.
- `tests/test_learn_loop.py`: make the currently untracked regression suite the executable contract and replace obsolete fixtures.
- `pyproject.toml`, `poetry.lock`: add and lock `markdown-it-py`.

### Preserve Unless a Failing Test Requires a Surgical Change

- `skills/learn-loop/assets/template.css`
- `skills/learn-loop/assets/template.js`
- `skills/learn-loop/agents/openai.yaml`
- `skills/learn-loop/reference/pre-check.md`
- `skills/learn-loop/scripts/render_template.py`
- `skills/learn-loop/templates/learner-profile.md`
- `skills/learn-loop/templates/review-queue.md`

---

### Task 1: Establish the tracked RED baseline

**Files:**

- Modify: `tests/test_learn_loop.py`
- Create: `tests/fixtures/learn-loop/deepseek-stage-03-heading.md`
- Create: `tests/fixtures/learn-loop/deepseek-stage-05-table.md`
- Create: `tests/fixtures/learn-loop/deepseek-stage-09-chinese-heading.md`
- Create: `tests/fixtures/learn-loop/docs-compliant-stage-02.md`

**Interfaces:**

- Consumes: current skill package and the failures documented in the final design.
- Produces: failing tests for every new public interface before production changes.

- [x] **Step 1: Preserve existing user-owned HTML regressions**

Keep the current tests for `{{TOPIC_SUB}}`, `.h1-sub`, fixed assets, workbench hooks, noscript behavior, and HTML status lines unchanged.

- [x] **Step 2: Add package and authority failures**

```python
def test_stage_contracts_and_runtime_tools_are_packaged(self):
    required = {
        "reference/stages/00-run-state.md",
        "reference/stages/10-cheatsheet.md",
        "reference/modes/exam-record.md",
        "reference/modes/feynman-record.md",
        "scripts/contract_io.py",
        "scripts/prepare_stage.py",
        "scripts/render_learning_page.py",
        "scripts/finalize_run.py",
        "templates/perspective-role.md",
        "templates/perspective-task.md",
    }
    self.assertEqual([], sorted(path for path in required if not (SKILL_ROOT / path).is_file()))

def test_original_prompt_has_no_duplicated_executable_contract(self):
    for contract in (SKILL_ROOT / "reference/stages").glob("*.md"):
        self.assertNotIn("```text\n我要研究【{{主题}}】", contract.read_text(encoding="utf-8"))
```

- [x] **Step 3: Add parser, preparation, mode, renderer, and finalizer API failures**

```python
def test_contract_io_parses_multiline_fields(self):
    module = load_script_module("contract_io.py")
    document = module.parse_document("### 记录 1\n\n- **说明：** 第一行\n  第二行\n")
    self.assertEqual("第一行\n第二行", document.sections[0].fields["说明"])

def test_prepare_stage_does_not_disclose_future_contracts(self):
    report = self.run_cli_json("prepare_stage.py", "--run-dir", str(run_dir), "--stage", "2")
    disclosed = "\n".join(report["disclosed"])
    self.assertIn("02-conflicts", disclosed)
    self.assertNotIn("03-brief", disclosed)

def test_mode_a_fixture_has_no_interaction_record_files(self):
    self.assertFalse((run_dir / "08-exam-record.md").exists())
    self.assertFalse((run_dir / "09-feynman-record.md").exists())

def test_renderer_expands_review_finding_reference(self):
    html = render_fixture("complete-anchored")
    self.assertIn("被引用的发现正文", html)
    self.assertIn("可靠性 8/10", html)

def test_finalize_is_idempotent(self):
    first = finalize_fixture(run_dir)
    second = finalize_fixture(run_dir)
    self.assertEqual(first["index_rows"], second["index_rows"])
    self.assertEqual(first["queue_rows"], second["queue_rows"])
```

- [x] **Step 4: Add contract mismatch regressions**

Cover at minimum:

- docs-compliant Step 2 with only one mutual enum must not be rejected for missing the other value;
- anchored Step 3 rejects C in findings 1–3, while unanchored Step 3 accepts all C and rejects evidence-strong wording;
- Chinese text immediately after a numbered heading cannot change record count;
- Step 7 is exactly 10 lessons × 5 questions;
- Step 8 has exact difficulty mapping and challenge answers are forbidden;
- Step 9 has two life examples, 3–5 recall checkpoints, and no Mode A final definition;
- Step 10 has the six canonical headings and exactly five Q&A pairs;
- run-state has no exercise cursor or weak-item fields.

- [x] **Step 5: Run the focused suite and verify RED**

Run:

```bash
poetry run python -m unittest discover -s tests -p 'test_learn_loop.py' -v
```

Expected: failures specifically report missing stage contracts/tools and old template/validator behavior. Existing HTML subtitle tests must remain green.

---

### Task 2: Add final stage and mode contracts plus canonical templates

**Files:**

- Create: `skills/learn-loop/reference/stages/*.md`
- Create: `skills/learn-loop/reference/modes/*.md`
- Create: `skills/learn-loop/templates/perspective-role.md`
- Create: `skills/learn-loop/templates/perspective-task.md`
- Modify: all Mode A and Mode B/C templates listed in the File Map

**Interfaces:**

- Consumes: final design field names, enum values, counts, free-text boundaries, and upstream sets.
- Produces: `reference/stages/<contract>.md` semantic contracts and template serialization with no hidden aliases.

- [x] **Step 1: Create one contract per stage and mode**

Every stage contract must use the same outline:

```md
# 第 N 步执行契约

## 目的
## 允许消费
## 必须产出
## 结构约束
## 内容评审
## 允许为空的条件
## 完成条件
```

Put exact fields/counts/enums only here. Keep the original prompt as a link and do not copy its body.

- [x] **Step 2: Materialize the final run-state template**

Include only:

- 执行契约；
- 消费上游；
- 运行标识（6 fields）；
- 前置判定（4）；
- 学习画像（5）；
- 能力与降级（5）；
- 模式 A 进度（3）；
- 上下文披露记录（repeated 2-field records）。

Delete the duplicate path/tier/anchoring blocks and all exercise fields.

- [x] **Step 3: Materialize Steps 1–5 exactly**

Apply the final design without synonyms:

- retained role file + parent summary and exact-copy references;
- unified Step 2 disagreement records, evidence comparison, adjudication question, full/partial agreement, and blind-spot candidate;
- Step 3 five finding fields and free-text CEO/hidden-link/action/frontier sections;
- Step 4 `发现引用` reviews and four overall review sections;
- Step 5 nine-field resources, optional 0–3 pitfalls, and 5–7 path nodes.

- [x] **Step 4: Materialize Steps 6–10 exactly**

Apply:

- five levels × eight fields plus three current-level fields;
- 10 lessons × six fields × five review questions plus four final-project fields;
- ten-row coverage plan, 10 question records × six fields, and five answerless challenges;
- Step 9 simple explanation, exactly two structured life examples, 3–5 recall checkpoints, no final definition;
- Step 10 canonical six sections, 3–5 scenarios, exactly five Q&A pairs, no backfill record section.

- [x] **Step 5: Materialize Mode B/C transaction templates**

The initial templates must contain only session state and an empty pending block. They must not contain fabricated completed question/retelling records or `本步提炼`.

- [x] **Step 6: Run static contract tests**

Run the package/contract subset. Expected: stage/mode package tests turn green; parser and runtime tests remain red.

---

### Task 3: Implement the shared Markdown contract and state I/O layer

**Files:**

- Create: `skills/learn-loop/scripts/contract_io.py`
- Modify: `tests/test_learn_loop.py`

**Interfaces:**

- Produces:

```python
@dataclass(frozen=True)
class ContractViolation:
    code: str
    file: str
    record: str | None
    field: str | None
    expected: str
    actual: str
    message: str

@dataclass
class Section:
    level: int
    title: str
    body: str
    fields: dict[str, str]
    start_line: int
    end_line: int

@dataclass
class MarkdownDocument:
    text: str
    sections: list[Section]

def parse_document(text: str) -> MarkdownDocument: ...
def exact_sections(document: MarkdownDocument, level: int, pattern: str) -> list[Section]: ...
def parse_upstream_table(document: MarkdownDocument) -> tuple[str, ...]: ...
def resolve_reference(run_dir: Path, reference: str) -> Section: ...
def read_run_state(path: Path) -> dict[str, str]: ...
def update_run_state(path: Path, updates: dict[str, str], disclosure: dict | None = None) -> None: ...
def atomic_write(path: Path, text: str) -> None: ...
```

- [x] **Step 1: Add focused parser failures**

Test one-line fields, multiline indented values, exact heading levels, duplicate headings, Markdown tables, sentinel values, and a number followed immediately by Chinese text.

- [x] **Step 2: Implement the minimal controlled-Markdown parser**

Parse only structures emitted by canonical templates. Do not build a general Markdown parser. Heading matching must operate on complete lines and never use `\b` for Chinese boundaries.

- [x] **Step 3: Implement safe reference resolution**

Reject absolute paths, `..`, paths outside the run directory, missing files, missing headings, and duplicate matching headings. Accept ``relative/path.md#精确标题`` only.

- [x] **Step 4: Implement atomic run-state updates**

Write a sibling temporary file, flush it, and replace the destination. Reject duplicate state fields, non-contiguous completed ranges, illegal state transitions, and hand-authored duplicate disclosure records.

- [x] **Step 5: Run parser/state tests**

Expected: Task 3 tests green; preparation/validator/renderer tests still red for missing consumers.

---

### Task 4: Implement progressive stage preparation and multi-agent packets

**Files:**

- Create: `skills/learn-loop/scripts/prepare_stage.py`
- Modify: `skills/learn-loop/templates/perspective-task.md`
- Modify: `tests/test_learn_loop.py`

**Interfaces:**

```python
def extract_original_prompt(stage: int, prompts_text: str) -> str: ...
def build_stage_context(run_dir: Path, stage: int, batch: int | None) -> tuple[Path, list[str]]: ...
def build_role_packets(run_dir: Path, state: dict[str, str]) -> list[Path]: ...
def prepare_stage(run_dir: Path, stage: int, batch: int | None = None) -> dict: ...
```

CLI JSON keys: `ok`, `stage`, `batch`, `output`, `context`, `disclosed`, `violations`.

- [x] **Step 1: Write stage-gate and no-overwrite failures**

Test: Stage N cannot prepare before N-1 passes; a populated output is never overwritten; no future contract/template appears in `disclosed`; repeat calls are idempotent only when the existing disclosure is identical.

- [x] **Step 2: Implement exact prompt extraction and trace digest**

The extraction result must be a continuous substring of the current original file. Stage 0 records the current SHA-256 without comparing it to a hard-coded value.

- [x] **Step 3: Implement current-stage context packets**

Each packet contains, in order: filled original prompt excerpt, current contract, current output template, allowed upstream excerpts, output path, and completion command. It may duplicate facts only as a generated disclosure snapshot and must identify original source paths.

- [x] **Step 4: Implement Step 1 role packets and parent barrier inputs**

Generate exactly five role packets and five retained role destinations. Every role packet embeds only that role's persona, channels, mode, grade rules, output template, and completion command. The parent packet lists all five expected files and cannot merge before each role validator passes.

- [x] **Step 5: Implement Step 7/8 two-batch gates**

`--batch 2` requires batch 1 local validation. Both batches share one stage output and one disclosure record; the second packet path is appended to its disclosure list.

- [x] **Step 6: Run preparation integration tests**

Expected: current-stage disclosure and role isolation tests green; full stage validation remains red until Task 5/6.

---

### Task 5: Replace Stage 0–5 validation with structured contract validation

**Files:**

- Modify: `skills/learn-loop/scripts/validate_stage.py`
- Modify: `tests/test_learn_loop.py`
- Create/Modify: `tests/fixtures/learn-loop/*`

**Interfaces:**

```python
def validate_one(stage: str, run_dir: Path, batch: int | None = None) -> list[ContractViolation]: ...
def validate_all(run_dir: Path, include_final: bool = True) -> dict: ...
```

CLI keeps `--stage`, `--all`, and `--json`, adds optional `--batch 1|2`, and serializes violations with `dataclasses.asdict`.

- [x] **Step 1: Convert common checks to parsed structures**

Remove `field_value` regex searching, fuzzy backtick upstream search, and string-only violations. Validate exact `执行契约`, exact `消费上游` file set, multiline nonempty fields, placeholders, and exactly three takeaways.

- [x] **Step 2: Implement Stage 0 validation**

Check the six run-state sections, exact field uniqueness, allowed profile prefixes/defaults, capability enums, ISO timestamp, prompt digest shape, contiguous progress, and disclosure continuity. Reject exercise fields.

- [x] **Step 3: Implement Stage 1 validation and parent-copy comparison**

Validate five retained role files, role-specific search records, A/B/C rules, C unanchored reason, and fixed result states. Then ensure parent summary core values equal the source role values after whitespace normalization.

- [x] **Step 4: Implement Stage 2 validation**

Validate per-record disagreement enum conditions, exact evidence comparison, conditional adjudication question, full/partial support counts, source independence fields, per-item consensus enum, and one-or-none blind-spot candidate.

- [x] **Step 5: Implement anchored/unanchored Stage 3 validation**

Read mode from run-state. Anchored requires A/B in findings 1–3; unanchored requires all C, a hypothesis notice, and rejects evidence-strong phrases. Validate references and keep narrative checks structural only.

- [x] **Step 6: Implement Stage 4/5 validation**

Resolve all five Step 4 finding references and enforce unique 1–10 scores. Validate exactly five resource cards, A/B URL vs C declaration, optional pit records, 5–7 chronological path nodes, and coverage of all resource references.

- [x] **Step 7: Verify historical failures now produce local errors**

Run the DeepSeek-shaped fixtures. Expected: no cascade to “zero records”; each fixture reports one or a small set of precise `file/record/field` errors.

---

### Task 6: Implement Stage 6–10 and Mode B/C validation

**Files:**

- Modify: `skills/learn-loop/scripts/validate_stage.py`
- Modify: `tests/test_learn_loop.py`

**Interfaces:**

- Consumes: `contract_io.py`, final templates, run-state mode.
- Produces: exact validators for later stages and interaction records.

- [x] **Step 1: Implement Stage 6 and 7 checks**

Validate five levels × eight fields, fixed level names, three current-level fields, exactly ten lessons × six fields × five questions, batch-local completion, core-20 content presence, and four final-project fields.

- [x] **Step 2: Implement Stage 8 checks**

Validate ten coverage rows, exact difficulty mapping, ten six-field questions, question-specific rubrics, and exactly five challenge prompts with no answer/rubric labels.

- [x] **Step 3: Implement Stage 9 checks**

Require `12 岁版讲解`, exactly two example records × three fields, 3–5 checkpoint records × four fields, and reject the old `最终定义`, `第一层/第二层/第三层`, user quotes, scores, or retelling rounds.

- [x] **Step 4: Implement Stage 10 checks**

Require the six canonical headings, 3–5 numbered application scenarios, exactly five Q&A pairs with one answer each, no backfill record, and no old aliases.

- [x] **Step 5: Implement Mode B lifecycle checks**

Validate absence before start, pending-item structure, cursor 0–10, completed base-record count, nested follow-ups, separate challenge records, append-only record ordering, and final summary consistency. Follow-ups/challenges never increment the base cursor.

- [x] **Step 6: Implement Mode C lifecycle checks**

Validate pending teaching/invitation, round count, six fields per completed round, concept continuity, allowed end states, and a real final-round reference for `已讲清`.

- [x] **Step 7: Run all Markdown and interaction tests**

Expected: all Stage 0–10 and Mode B/C tests green; renderer/finalizer tests remain red.

---

### Task 7: Build static HTML from validated Markdown

**Files:**

- Modify: `pyproject.toml`
- Modify: `poetry.lock`
- Create: `skills/learn-loop/scripts/render_learning_page.py`
- Modify: `skills/learn-loop/scripts/render_template.py`
- Modify: `skills/learn-loop/assets/template.html`
- Modify: `skills/learn-loop/reference/html-guide.md`
- Modify: `tests/test_learn_loop.py`

**Interfaces:**

```python
def render_markdown(text: str) -> str: ...
def build_view_model(run_dir: Path) -> dict[str, str]: ...
def expand_review_cards(run_dir: Path) -> str: ...
def render_learning_page(run_dir: Path, output: Path, inline: bool = False) -> Path: ...
```

CLI:

```bash
poetry run python skills/learn-loop/scripts/render_learning_page.py \
  --run-dir <run-dir> --output <run-dir>/<topic>-十步学习.html [--inline]
```

- [x] **Step 1: Add the Markdown dependency with Poetry**

Run:

```bash
poetry add markdown-it-py
```

Expected: `pyproject.toml` lists the dependency and `poetry.lock` is refreshed.

- [x] **Step 2: Configure safe deterministic Markdown rendering**

Use `MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False}).enable("table")`. Raw HTML must be escaped; external links must be checked for `http`/`https` before being inserted into template-specific attributes.

- [x] **Step 3: Build the view model from facts**

Read run-state and stages 1–10 only after validation. Derive prompt blocks from original prompt excerpts and profile values. Do not let missing HTML content be invented in the view layer.

- [x] **Step 4: Expand cross-file references**

For every Step 4 review, resolve its Step 3 finding and render one complete static card. For Step 1, render the parent summary plus collapsible full role analysis/search logs. Broken references fail the build.

- [x] **Step 5: Preserve the fixed template and asset pipeline**

Keep one `topic-title` `<h1>`, nonempty `.h1-sub`, existing workbench hooks, stable `data-od-id` values, local CSS/JS references, and `--inline`. `render_template.py` remains the final asset packager.

- [x] **Step 6: Derive Mode B/C status without Markdown fetches**

File absent → not started; file present → read its session status. Generated HTML contains the current static status and never fetches Markdown in the browser.

- [x] **Step 7: Run HTML tests**

Expected: finding expansion, role-detail expansion, raw-HTML escaping, no unresolved placeholders, fixed assets, inline mode, topic subtitle, and offline behavior all green.

---

### Task 8: Implement transactional finalization and package completeness

**Files:**

- Create: `skills/learn-loop/scripts/finalize_run.py`
- Modify: `skills/learn-loop/scripts/preflight.py`
- Modify: `skills/learn-loop/scripts/review_queue.py`
- Modify: `tests/test_learn_loop.py`

**Interfaces:**

```python
def finalize_run(
    run_dir: Path,
    state_root: Path,
    learning_root: Path,
    inline: bool = False,
    profile_fact: str | None = None,
    profile_quote: str | None = None,
) -> dict: ...
```

JSON keys: `ok`, `html`, `index_updated`, `queue_updated`, `profile_updated`, `state`, `violations`.

- [x] **Step 1: Add all-or-not-complete failures**

Test that any Stage or HTML failure leaves run-state `进行中`; repeated success creates no duplicate INDEX/queue rows; profile update requires both a fact and user quote.

- [x] **Step 2: Make package completeness exhaustive**

Update `REQUIRED_SKILL_FILES` to include `pre-check.md`, HTML/CSS/JS assets, renderer, finalizer, stage/mode contracts, and new templates. Keep preflight bootstrap limited to global profile, queue, and INDEX.

- [x] **Step 3: Make INDEX and review queue idempotent by run ID**

An identical existing row returns `updated: false`; a conflicting row with the same run ID is an error. Preserve historical score entries and append-only behavior.

- [x] **Step 4: Implement ordered finalization**

Validate stages → render → validate HTML → update INDEX → update queue → optional profile → atomically mark complete → revalidate all. If a pre-state mutation operation fails, do not mark complete.

- [x] **Step 5: Run finalization tests twice**

Expected: first execution updates artifacts; second execution is a clean no-op with identical final files.

---

### Task 9: Align orchestration and judgment references with the final contracts

**Files:**

- Modify: `skills/learn-loop/SKILL.md`
- Modify: `skills/learn-loop/reference/pre-check.md`
- Modify: `skills/learn-loop/reference/perspectives.md`
- Modify: `skills/learn-loop/reference/conflict.md`
- Modify: `skills/learn-loop/reference/curriculum.md`
- Modify: `skills/learn-loop/reference/examination.md`
- Modify: `skills/learn-loop/reference/retention.md`
- Modify: `skills/learn-loop/reference/html-guide.md`
- Modify: `tests/test_learn_loop.py`

**Interfaces:**

- `SKILL.md` invokes `preflight.py`, `prepare_stage.py`, `validate_stage.py`, Mode B/C record creation, and `finalize_run.py` in the documented order.
- Judgment references contain principles and decision rules only; exact shapes point to stage/mode contracts.

- [x] **Step 1: Tighten skill discovery metadata in `SKILL.md`**

Make the frontmatter description describe only triggering/non-triggering conditions. Keep detailed workflow in the body so an agent cannot shortcut by following the description alone.

- [x] **Step 2: Replace the stage table with file/contract pointers and completion gates**

Each row names the output file, contract file, required upstream, validation command, and whether a batch is used. Do not repeat field tables.

- [x] **Step 3: Document multi-agent dispatch and parent barrier explicitly**

State that role agents read only their packet, write only their role file, and return the path/status; the parent waits, validates each, merges exact core values, and retains every role file.

- [x] **Step 4: Rewrite references to remove duplicate executable specs**

Keep source grading rationale, reliability rubric, pedagogy, Feynman loop, retention principles, and trust gates. Replace exact field/count replicas with links to the authoritative contract.

- [x] **Step 5: Update every command and completion statement**

Mode A must not create records; Stage 9 must not produce a final definition; HTML must be built from Markdown; only `finalize_run.py` marks completion and registers review artifacts.

- [x] **Step 6: Run contract-reachability tests**

Assert every stage row links to an existing contract/template, every packaged file is reachable from SKILL or an invoked script, and no validator label is absent from its contract/template.

---

### Task 10: Pressure-test the skill and complete the regression gate

**Files:**

- Modify: `tests/test_learn_loop.py`
- Create: `docs/plans/learn-loop/learn-loop-format-contract-eval-results.md`

**Interfaces:**

- Consumes: final skill, contracts, scripts, and the RED scenarios from Task 1.
- Produces: repeatable evidence that the new instructions reduce output variance without suppressing content.

- [x] **Step 1: Define fresh-context pressure scenarios**

Include at least:

1. anchored parallel Step 1 with one failed search;
2. unanchored orchestrated Steps 2–3 where all findings are C;
3. a no-conflict topic that tempts fabricated disagreement;
4. Step 7/8 long-output batching;
5. Mode B user silence, follow-up, and challenge;
6. Mode C user stops before passing;
7. Step 4 reference rendered with Step 3 content.

- [x] **Step 2: Record the existing/control behavior**

Use the documented DeepSeek run plus fresh no-new-contract samples as RED evidence. Record exact omissions, format drift, fabricated states, and rationalizations; do not rely on pass/fail counts alone.

- [ ] **Step 3: Run the final skill repeatedly**

Use at least five fresh-context samples for each wording-sensitive scenario. When multiple model tiers are available, include one medium/flash tier and one stronger parent tier; otherwise state the model-coverage limitation and still run five fresh contexts.

- [ ] **Step 4: Check information preservation and variance**

Confirm role files retain full analysis/search failures, parent summaries do not alter core claims, output structures converge, and free-text sections remain substantive rather than field-shaped fragments.

Pending limitation: the current repository/session has no controlled multi-model fresh-context runner. The deterministic information channel is covered, but model-tier narrative depth and five-run variance remain unclaimed in `learn-loop-format-contract-eval-results.md`.

- [x] **Step 5: Run the complete automated suite**

```bash
poetry run python -m unittest discover -s tests -p 'test_learn_loop.py' -v
```

Expected: all tests pass with no warnings or skipped Learn Loop cases.

- [x] **Step 6: Run direct CLI smoke checks**

```bash
LEARN_LOOP_SMOKE_ROOT="$(mktemp -d)"
LEARN_LOOP_SMOKE_NEW_RUN="$LEARN_LOOP_SMOKE_ROOT/learning/2026-08-05-120000-smoke-new"
poetry run python skills/learn-loop/scripts/preflight.py --workspace-root "$LEARN_LOOP_SMOKE_ROOT" --bootstrap --json
poetry run python skills/learn-loop/scripts/prepare_stage.py --run-dir "$LEARN_LOOP_SMOKE_NEW_RUN" --stage 0 --json
poetry run python -m unittest \
  tests.test_learn_loop.LearnLoopCliTest.test_validate_stage_reports_json_violation \
  tests.test_learn_loop.LearnLoopFinalizerTest.test_complete_run_finalizes_idempotently -v
```

Expected: preflight and stage preparation return valid JSON; validator returns a structured error for an invalid run; the golden finalizer CLI completes twice without duplicate INDEX/queue records and only marks completion after valid HTML.

- [x] **Step 7: Verify surgical scope and immutable prompt**

Run:

```bash
git diff --check
git diff -- skills/learn-loop/reference/original-prompts.md
git status --short
```

Expected: no whitespace errors; no diff for `original-prompts.md`; unrelated user changes remain present and unmodified.

---

## Completion Criteria

- All stage/mode contracts, templates, validators, context packages, and commands agree exactly.
- A fresh agent can execute each stage by reading only its disclosed context packet.
- Five role agents retain their own full files and the parent can validate/merge without information loss.
- Anchored and unanchored branches both pass their own non-contradictory gates.
- Mode A never fabricates Mode B/C records; Mode B/C cannot advance without actual user input.
- Step 9 ends in recall checkpoints, not a model-authored final definition.
- Final HTML expands Markdown references at build time and opens offline without reading Markdown.
- Finalization is idempotent and marks completion only after all stages and HTML pass.
- The original prompt file is unchanged.
- The tracked Learn Loop test suite and pressure-evaluation report provide reproducible deterministic evidence; repeated cross-model narrative-quality sampling remains explicitly marked pending rather than inferred.
