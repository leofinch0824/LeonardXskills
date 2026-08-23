# Pass 3: reverse engineering and critique

Use this reference only after Pass 1 and Pass 2 support a deep read **and the user has authorised it at the gate**. The aim is to reconstruct the work closely enough to test its reasoning and identify what would be needed to reproduce or extend it. It is not a license to assert that a paper is reproducible without the required details.

Write findings to `.paper-reading/<slug>/pass3-deep-dive.md`, reusing the slug created in Pass 2. The internal format is up to you; only the path is fixed.

## Reconstruct

Expect a substantial time investment: experienced readers may need more than 1–2 hours, and newcomers can need many hours. Trace the full path from assumptions and inputs through transformations, objective/loss, training or optimization procedure, outputs, and evaluation. Re-derive important equations or algorithms in your own notation where useful; check dimensions, boundary cases, dependencies, and unstated choices. Then reconstruct the paper's full structure from memory and compare it with the paper, so omissions and weak links are visible. Label gaps as missing rather than filling them with conventional defaults.

Compare plausible alternative designs only against the paper's stated evidence. Explain whether an alternative is an **Inference** and what experiment would discriminate it.

## Deliverables

Produce **only the deliverables named at the gate** — for most purposes one or two, not all five. Producing all of them by default is the failure mode this pass is meant to avoid. Keep each compact and source-located.

1. **Assumption and risk analysis** — assumption, paper support, failure mode or scope boundary, and why it matters.
2. **Reimplementation plan** — required data and splits, preprocessing, model or system components, training/configuration, dependencies/hardware, evaluation protocol, expected outputs, and each missing detail or reproducibility risk.
3. **Critical claim review** — which claims are directly tested, weakly supported, untested, or contradicted by the provided evidence. Distinguish author claims, observations, and inferences. Where Pass 1 retrieved a peer-review record, note where reviewers' concerns agree or disagree with your own.
4. **Extension hypotheses** — a small set of testable directions tied to a limitation or transfer gap. State the hypothesis, minimal experiment, success metric, and risk; do not present a hypothesis as a paper contribution. This is about extending *this* paper; components worth lifting into the reader's own work belong to Pass 2's transferable-parts section.
5. **Citation completeness check** — relevant work that appears missing or insufficiently compared, why it matters, and the search or reading needed to verify the concern. Mark this as an **Inference** unless the paper itself identifies the gap.

Judgements that depend on knowing the current state of the field — whether a comparison is still the strongest available, whether a gain matters in practice — go under **Needs your judgement** rather than being asserted.

## Completion test

Finish only when a technically capable reader could identify the dependencies and decisions needed to attempt an implementation, reconstruct the paper's structure and central argument, and see exactly which parts remain unverified. If the paper omits a material detail, ask for supplementary material/code or list the experiment needed to resolve it.
