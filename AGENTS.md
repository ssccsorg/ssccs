# AI Agent Instructions

All code, text content, output, and comments must be written in English.

## Reasoning Constraints

- Limit all inferences to given premises or widely verified facts; when uncertain, explicitly mark the boundary between fact and conjecture.
- Deconstruct claims, surface hidden assumptions, evaluate logical coherence, and consider alternatives. Every suggestion must be accompanied by a reasoning chain that exposes potential weaknesses and counterarguments.
- Explicitly label analytic conclusions vs. value judgments/practical recommendations. Keep the latter minimal and hedged.

## Markdown Format

- Do not use `---` between paragraphs. A horizontal rule is allowed only directly before a final reference or license section.
- Minimize bold. Use it only to highlight the single most critical point in the entire document.
- Do not use em dashes (`—`).
- Do not prefix headings with numbers; use plain headings.

## Content Guidelines

- Don't put emojis.
- When a sentence would contain `.ss`, rewrite to use the full technical term appropriate to the context.
- Avoid sequential enumerations like “Week 1, Week 2”. Use numbered experiments, phases, or milestones instead.
- Avoid negated‑affirmation pairs (“not…, but…”). Express logic directly through affirmative, sequential, or conditional structures.

## Git Workflow

- Do not push to remote without permission.
- Do not merge a pull request or any branch without permission.
- When starting a new task subject:
    1. Create a GitHub Issue, add relevant labels, then link the branch that will contain the work.
    2. Create a branch with the format `{issue-number}-{subject-alphabets-with-one-or-two-dashes}`.
- The pull request title format must be: `PR: {category}: {message}`. (Include `#{issue}` after the category only in PR branches; omit it in the main branch.)
- Do not test by pushing to GitHub.

### Commit Message Format

- `{category}: {message}`. Include `#{issue}` after the category only in PR branches (omit in main branch).

## Code

- Focus on the accuracy of the goal.
- Code as pessimistically and critically as possible.
- Do not generate unnecessary code. Produce only what is **essential** for the goal.
