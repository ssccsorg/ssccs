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

## Documentation Guidelines

- Don't put emojis.
- When a sentence would contain `.ss`, rewrite to use the full technical term appropriate to the context.
- Avoid sequential enumerations like “Week 1, Week 2”. Use numbered experiments, phases, or milestones instead.
- Avoid negated‑affirmation pairs (“not…, but…”). Express logic directly through affirmative, sequential, or conditional structures.

### Quarto

- Default .qmd template:

```qmd
---
title: text
subtitle: text
date: last-modified
metadata-files:
  - path/to/_include/author.yml
abstract: |
  text
---

{{< include [relative_path_to]/_include/_title_meta_items.qmd >}}

\`\`\`{python}
#| include: false
#| context: local
%run [relative_path_to]/_include/_graphviz.py
\`\`\`

... contents

```

- Use Python-DOT code blocks for necessary visualizations: the default template of DOT code in .qmd file:

```{python}
#| label: fig-label
#| fig-cap: text
dot("""
digraph DOTGraph {
... DOT Code ...
}
""")
```

- When code DOT, do not use `graph` for node or class name.

## Git

- Do commit only: do not push to remote.
- Do not merge a pull request or any branch.
- When starting a new task subject:
    1. Create a GitHub Issue, add relevant labels, then link the branch that will contain the work.
    2. Create a branch with the format `{issue-number}-{subject-alphabets-with-one-or-two-dashes}`.
- The pull request title format must be: `PR: {category}: {message}`. (Include `#{issue}` after the category only in PR branches; omit it in the main branch.)
- Do not test by pushing to GitHub.

### Commit Message Format

- `{category}: {message}`. Include `#{issue}` after the category only in PR branches (omit in main branch).

## Code

- Implement → Review → Apply feedback & fix → Build/Test (clean) → Commit → Propose next direction → Await user signal → Repeat
- Focus on the accuracy of the goal.
- Code as pessimistically and critically as possible.
- Do not generate unnecessary code. Produce only what is **essential** for the goal.
- Do not use text characters to draw diagrams (e.g., trees or boxes using ╔═) in code comments.
