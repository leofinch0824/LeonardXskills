---
name: paper-reading-assistant
description: "Read ONE research paper progressively with a human in the loop, using Keshav's Three-Pass method: clarify why you are reading it, triage relevance, build an evidence-backed understanding map, and — only when justified — reverse-engineer or plan reproduction. Use when judging whether a specific paper is trustworthy, relevant, or worth deep investment. Not for batch literature screening, and not for a one-paragraph generic summary."
---

# Paper Reading Assistant

A collaborative reading protocol for **one paper at a time**. The scarce resource is not the assistant's reading time — it is the user's attention. Every pass therefore ends with a visible judgement the user can override cheaply, and no pass silently escalates into the next.

Read this whole file before starting.

## Scope guard: one paper

This skill reads a single paper per run. If the user supplies several, do not read any of them yet: list what was received, state that this protocol is designed for depth on one paper rather than batch screening, and ask which one to start with. Offer to repeat the run for the others afterwards. Never quietly pick the first one.

## Step 0 — Opening clarification (mandatory, skippable)

Before Pass 1, always ask exactly two questions in one short message:

1. **Why is this paper in front of you — what decision will reading it inform?** (e.g. adopt the method, cite it as related work, reproduce it, review it, judge whether the subfield is worth entering)
2. **How familiar are you with this subfield?** (newcomer / working knowledge / expert — this sets how much is explained versus assumed in Pass 2)

Tell the user they can reply **"你定" / "you decide"** to skip. If they skip, or answer only one, proceed on stated defaults — purpose: *assess quality and relevance*; familiarity: *working knowledge* — and say explicitly which defaults are in force. Do not ask these questions again in the same run unless the user changes the goal.

Record the answers. They govern depth, starting pass, and what counts as a red flag for this reader.

If the answer makes a full read unnecessary — the user only wants one fact, a citation string, or a two-line gist — say so and answer directly instead of running the protocol.

## Choosing the starting pass

| Request | Start at |
| --- | --- |
| "Is this relevant / worth my time?" | Pass 1 |
| "Explain this paper" / "does the method hold up?" | Pass 2 (report Pass 1 findings briefly first) |
| Reproduction, rigorous review, research design | Pass 3, after Passes 1–2 |

Do not advance merely because a later pass exists.

## Evidence discipline

Maintain a source ledger while reading: section/page (or figure/table/equation/reference identifier), a short paraphrase, and confidence. Mark every substantive statement as exactly one of:

- **Observation** — directly visible in the paper or supplied artifact.
- **Author claim** — a result or assertion attributed to the authors.
- **Inference** — your reasoned interpretation, transfer assessment, or criticism.

Quote sparingly and preserve conditions, comparisons, and uncertainty. State unavailable evidence as unavailable; never invent datasets, implementation details, numerical results, baselines, or citations. If only an abstract or metadata is available, limit conclusions to that material and name the limitation.

## Red-flag surfacing

A red flag is anything that materially changes the assessment of the paper, such as: the strongest baseline is outdated or unfairly configured; headline results carry no variance, error bars, or significance testing; test-set contamination or train/test leakage is plausible; an ablation does not isolate the mechanism the paper credits; a SOTA claim excludes a known stronger method; a preprint is cited as if peer-reviewed; the evaluation metric does not measure the claimed capability.

When one appears, **finish the current pass** — do not interrupt mid-pass — then open that pass's output with a `⚠️ Red flags` block, above the normal report. Each entry states the observation, its source location, and what it does to the paper's central claim. Never bury a red flag in a table's caveat column.

## Division of labour

The assistant and the user are good at different things. Do the first column; hand the second column back explicitly under a **Needs your judgement** heading rather than resolving it as an Inference.

| Assistant does | User decides |
| --- | --- |
| Check prose numbers against tables and figures | Whether a baseline is genuinely the strongest available today |
| Verify a claimed comparison actually exists | Whether the problem matters |
| List what is missing for reproduction | Whether the reported gain is practically meaningful |
| Resist being persuaded by good writing | Whether the idea is recycled from an adjacent field |

## Pass 1 — triage

Time-box to roughly 5–10 minutes of scan-level work. Read the title, abstract, introduction, section headings, conclusion, and reference list; glance at mathematical content. **Do not** study figures and tables closely or appraise evidence sufficiency yet — note that a figure looks central and defer it to Pass 2.

Also establish, using available retrieval, the paper's external standing:

- **Publication status** — preprint or peer-reviewed, venue, and whether it has been retracted or has an erratum.
- **Peer-review record** — for venues with open review (OpenReview: ICLR, NeurIPS, and others), retrieve reviewer scores, the main criticisms, and the authors' rebuttal. This is the single highest-value input when judging an unfamiliar paper: reviewers have already done a Pass 3.
- **Citation profile** — rough count and its distribution over time, enough to distinguish "ignored", "steadily used", and "recently surging".

Report only what retrieval actually returned. If retrieval is unavailable or finds nothing, say so and mark this section unverified — never reconstruct review comments, scores, or citation counts from memory.

Deliver a **Paper Triage Report** answering Keshav's Five Cs:

| C | Decision question |
| --- | --- |
| Category | What type of paper is this? |
| Context | What problem setting and prior work does it rely on? |
| Correctness | Are the visible assumptions and evaluation design plausible enough to continue? |
| Contribution | What is claimed to be new or useful? |
| Clarity | Is the presentation sufficiently clear to assess further? |

Add the problem statement, the method in one sentence, relevance to the user's stated purpose (with reasons), open unknowns, and a depth recommendation: **stop**, **Pass 2**, or **Pass 3 candidate**. Treat novelty, relevance, and evidence quality as provisional here; they are validated in Pass 2.

### ⛔ Stop — first checkpoint

End the turn. Give the recommendation, the reasoning behind it, and — if continuing — which sections Pass 2 will concentrate on and why. Invite redirection in one line: *if you want me to focus elsewhere, say so; otherwise I'll proceed as described.* Do not begin Pass 2 in the same turn.

## Pass 2 — understanding

Up to about an hour of equivalent effort. Read the body closely enough to explain the work: the core method and every material result figure and table. Skip proofs and implementation minutiae unless the user's purpose requires them.

### Persist from here

Pass 1 stays in conversation. From Pass 2 onward, write findings to disk so the run survives context loss and later sessions:

```
.paper-reading/<slug>/
  pass2-understanding.md
  pass3-deep-dive.md
```

`<slug>` is kebab-case `firstauthor-year-keyword`, e.g. `keshav-2007-how-to-read`. The internal format of these files is deliberately unspecified — write what serves this paper and this reader. Only the directory layout and filenames are fixed. Mention the path once when created. Do not modify `.gitignore`; if the user asks about ignoring the directory, tell them and let them decide.

### Visual and statistical validity check

For every figure or table carrying a central claim, verify and record:

- Axes have units and unambiguous labels; scale is not truncated or log-scaled in a way that inflates the effect.
- Error bars, confidence intervals, or variance across seeds/runs are present and defined.
- Statistical support is stated (test, p-value, or interval) where a difference is claimed.
- Comparators ran under matched conditions — same data, budget, tuning effort, and hardware where relevant.

Any central result failing these is a red flag, not a caveat.

### Understanding Map

Produce it in this causal order:

`Problem → limitation of prior work → key insight → method/mechanism → evaluation evidence → limitations → potential extension`

For the method, name inputs, outputs, major components, the mechanism supposed to produce the benefit, and the meaningful difference from named baselines.

### Claim–Evidence Map

One row per central claim:

| Author claim | Supporting artifact | Comparator / condition | What the artifact establishes | Caveat |
| --- | --- | --- | --- | --- |

Use exact numbers only when verified in the cited artifact; otherwise describe the direction or mark the field unavailable. Keep reported limitations separate from your own inferences.

### Artifact availability

If the paper claims code, data, or models are available, check that the link actually resolves and that the repository or dataset has real content. Report what was found: live and substantive, live but empty or placeholder, dead, or no claim made. A claim of availability is not evidence of availability.

### Transferable parts

Close with a short **Transferable parts** section: components a reader could lift into their own work regardless of whether the paper's central claim holds — an evaluation protocol, a dataset or benchmark, a problem framing, an ablation design, a metric, a failure taxonomy. Say what each is useful for and what it would cost to adopt. This is distinct from Pass 3's extension hypotheses, which are about extending *this* paper.

### Closing answers and background queue

End with four checkable answers: the problem, why prior work falls short, why this method may help, and whether the presented evaluation supports each central claim. List relevant references that were not read as a background-follow-up queue.

If the main thrust remains unclear, never bridge the gap with speculation. Choose deliberately and say why:

| Situation | Recommended move |
| --- | --- |
| Missing terminology or background knowledge | **Pause for background** — read the queued references first; pushing on invites misreading |
| Method description vague but code is available | **Continue to Pass 3** and read the implementation |
| A core assumption looks unsound | **Stop** — quality is insufficient to justify more time |
| Result looks important but evidence is thin | **Continue to Pass 3** for critical review of exactly that gap |

## ⛔ Stop — gate to Pass 3

End the turn before any Pass 3 work. Pass 3 costs hours; the user authorises it.

Recommend Pass 3 only when the paper is relevant enough **and** one of these holds: the user plans to reproduce, rely on, extend, or critically evaluate it; its claims shape a research decision; or Pass 2 exposed a consequential uncertainty. State the gate decision, the evidence behind it, and which Pass 3 deliverables are worth producing for this purpose — usually one or two, not all of them.

For an authorised Pass 3, read [references/deep-dive.md](references/deep-dive.md) before proceeding.

## Deliverable shape

Write instructions-facing artifacts in the user's language: this file is English, but reports, tables, and conversation follow whatever language the user writes in.

Lead with the requested depth recommendation or answer, with red flags above it when present. Include source locations for material conclusions, keep the three evidence labels distinguishable, and end with the highest-value next action at the current depth. Adapt headings and detail to the user's stated purpose; never emit all three pass reports when only one was requested.
