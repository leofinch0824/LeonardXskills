# Three-Pass Fidelity Audit

**Scope:** `skills/paper-reading-assistant/SKILL.md` and
`references/deep-dive.md`, assessed against S. Keshav's original method. This
is an audit only; it does not modify the Skill.

## Evidence checked

- Primary publication: S. Keshav, *How to Read a Paper*, ACM SIGCOMM
  Computer Communication Review 37(3), 83–84 (2007),
  [DOI 10.1145/1273445.1273458](https://dl.acm.org/doi/10.1145/1273445.1273458).
- Official CCR PDF (the 2007 publication):
  [p83-keshavA.pdf](https://ccr.sigcomm.org/online/files/p83-keshavA.pdf).
- Author's later living version (17 Feb 2016), independently retrieved from
  SFU Library's hosted PDF, [paper-reading.pdf](https://www.lib.sfu.ca/system/files/32376/paper-reading.pdf).
  Its Three-Pass section preserves the passages audited here.

AnySearch academic search confirmed the 2007 CCR record and the official ACM
DOI. Its PDF extractor could not parse the CCR/SFU PDF, so the textual
comparison uses the author-version PDF obtained from the university-library
host; the official CCR link remains the publication of record.

## What is aligned

| Original method | Skill implementation | Assessment |
| --- | --- | --- |
| Read in *up to* three increasing-depth passes rather than linearly. | Starts at a goal-appropriate pass and says not to advance merely because a later pass exists. | Aligned. |
| Pass 1 is a 5–10 minute bird's-eye scan; it decides whether to continue. | Triage reads the expected structural material and recommends stop / Pass 2 / Pass 3 candidate. | Aligned in purpose. |
| Five Cs: Category, Context, Correctness, Contributions, Clarity. | Triage explicitly requires all Five Cs with suitable decision questions. | Strongly aligned. |
| Pass 2 grasps content, not details; summarize the main thrust with supporting evidence. | Understanding Map and Claim–Evidence Map require causal explanation, evidence, comparators, and caveats. | Strongly aligned and usefully operationalized. |
| Pass 3 virtually re-implements: recreate the work under the authors' assumptions, compare it to the paper, challenge assumptions, and note future work. | Deep dive reconstructs the pipeline, re-derives/checks equations, analyzes assumptions, plans reimplementation, critically reviews claims, and creates testable extension hypotheses. | Strongly aligned. |
| Selective depth is appropriate for literature surveys and research needs. | Explicit Pass-3 gate and selective treatment of broad surveys. | Aligned; preserves the method's efficiency rationale. |

## Deviations and risks

*The five items below were the findings of the original audit. All have since been
addressed; see "Resolution" for what changed.*

1. **Medium — Pass timing is absent.** Keshav gives Pass 1 about 5–10 minutes, Pass 2 up to an hour for an experienced reader, and Pass 3 many hours for beginners / more than 1–2 hours for experienced readers. Without budgets, an assistant can turn triage into an overlong summary and defeat the progressive-depth goal.
2. **Medium — Pass 2 omits two distinctive quality checks.** The original says to ignore details such as proofs, inspect figures/diagrams closely, check graph labels and error bars/statistical significance, and mark unread relevant references. The Skill asks for material figures/tables and claim evidence, but does not explicitly preserve proof-skipping, visual/statistical validity checks, or an unread-reference queue.
3. **Low–medium — Pass 1 slightly front-loads Pass-2 work.** The original first pass says to glance at mathematical content, then conclusions and references. The Skill additionally says to skim figures and tables and requests "apparent evidence." This is sensible AI triage, but it can encourage evidence appraisal before the deliberate Pass-2 visual examination. It should be labeled provisional and time-bounded.
4. **Low — The recovery choices after an unsuccessful Pass 2 are missing.** Keshav explicitly permits setting the paper aside, returning after background reading, or persevering to Pass 3. The current gate treats Pass 3 chiefly as a relevance/decision choice; it should also tell the user when missing background is the reason to pause rather than infer or force a deep read.
5. **Low — Pass-3 completion is narrower than the original.** The Skill covers hidden assumptions and reproduction gaps well, but should explicitly include reconstructing the paper's full structure from memory and checking for missing relevant citations, both of which Keshav names as end-state capabilities.

## Resolution (2026-08-23)

All five findings were addressed, alongside a separate interaction-design revision
that this fidelity audit did not originally cover.

| Finding | Resolution |
| --- | --- |
| 1. Pass timing | Explicit budgets on all three passes; Pass 3's hour estimates retained in `deep-dive.md`. |
| 2. Pass-2 quality checks | Added a "Visual and statistical validity check" subsection (axes/units, error bars and variance, stated significance, matched comparator conditions), explicit proof-skipping, and a background-follow-up queue. |
| 3. Pass-1 front-loading | Pass 1 now forbids close figure/table study and evidence appraisal, deferring both to Pass 2; its findings are labelled provisional. |
| 4. Pass-2 recovery | Added a decision table mapping the failure situation (missing background / vague method with code / unsound assumption / thin evidence) to pause, continue, or stop. |
| 5. Pass-3 completion | Full-structure reconstruction from memory added to "Reconstruct"; citation completeness check retained as a named deliverable. |

### Interaction-design revision (beyond the original audit's scope)

The audit assessed fidelity to Keshav's method but not the human–assistant division of
labour. Keshav's three passes describe one person budgeting *their own* time; once an
assistant does the reading, the scarce resource becomes the user's attention, and the
checkpoints change meaning — from "should I keep reading" to "is the assistant still
reading for the right question". The following were added on that basis:

- **Single-paper scope guard.** The Skill previously implied batch screening ("literature-review decisions", survey handling); it now reads one paper per run and asks the user to choose when given several.
- **Mandatory opening clarification.** Two questions — the decision the reading informs, and the reader's familiarity with the subfield — replacing "infer intent, ask when unclear", which in practice was rarely triggered. Skippable via "you decide", with the assumed defaults stated aloud.
- **Two hard stops.** After Pass 1 and before Pass 3, the assistant ends its turn rather than self-authorising the next pass.
- **Red-flag surfacing.** Assessment-changing findings are raised at the top of the current pass's output instead of being buried in a caveat column.
- **Division of labour.** Judgements requiring current knowledge of the field are handed back under "Needs your judgement" rather than asserted as inferences.
- **External verification in Pass 1.** Publication/retraction status, peer-review record (OpenReview scores and rebuttals), and citation profile — with explicit instructions never to reconstruct these from memory when retrieval fails.
- **Artifact availability check in Pass 2.** Claimed code and data links are actually resolved; a claim of availability is not evidence of availability.
- **Transferable parts in Pass 2.** Components liftable into the reader's own work, distinguished from Pass 3's extension hypotheses.
- **Persistence from Pass 2.** `.paper-reading/<slug>/` with fixed filenames and deliberately unspecified internal format.
- **Pass-3 deliverable restraint.** Produce only the deliverables named at the gate, typically one or two of five.

## Verdict

**High fidelity, with the operational drift now corrected.** The Skill preserves the essential Three-Pass architecture, Five Cs, escalating commitment, and the third pass's virtual-reimplementation/critical stance. Its additions (intent clarification, source ledger, claim–evidence mapping, reproducibility plan, external verification, and the human-in-the-loop checkpoints) are compatible extensions rather than replacements. With the resolutions above, it is faithful not only in broad concept but also in Keshav's practical guardrails against premature depth and unsupported interpretation.
