# Contributing

Thank you for your interest in SSCCS.  
Our goal is to achieve the highest level of technical innovation with minimal communication overhead. If you wish to contribute, please carefully internalize the philosophy and guidelines below.

## Overarching Principle: Human Life Comes First
This project exists to help us live better lives. Code, debate, and technical superiority are means, not ends in themselves. Therefore, rules and discussions must never devolve into unnecessary stress or “moral posturing” that exerts pressure on contributors. We focus on efficiently generating results within an atmosphere of objective, mutual respect.

## Our Mission: Beyond Boundaries, Toward a New Paradigm
We are a collective united to architect a completely new computing paradigm. We recognize that even the platforms hosting this repository are bound by centralized corporate infrastructures and legacy cultural frameworks. 

We demand, as our highest priority, a culture that encourages breaking the mold and thinking differently—provided it does not hinder the activity of other contributors. We aim to build a culture where even the boundaries surrounding us are treated as objects of innovation.

We aggressively adopt any technology that advances computing paradigms faster and with less energy. We do not delay adoption due to unproven traditions or institutional conservatism when a tool’s efficacy and safety are established.

## Core Philosophy: Results and Pragmatism

- Results-Oriented: The "pedigree" of how code was written matters less than whether it works, remains maintainable, and positively impacts the system.
- Efficiency: We bypass unnecessary bureaucracy and exhausting debates. Prove your point with code.
- Strict Technical Focus: Discussions are limited to software engineering, architecture, and performance. Ideological or social agendas unrelated to the project are considered noise; such behavior will naturally lose relevance and fade out within this community.
- Realistic Approach to Equality and Diversity: We support equal opportunity regardless of background. However, we recognize that human psychology does not always align with abstract ideals. We ensure that enforcing “equality” or “righteousness” does not itself become a new form of oppression. Complex social issues are addressed through a healthy project culture and merit-based consensus, not rigid policing.
- Clarity of Responsibility: Every commit must be GPG-signed. PR authors and reviewers bear 100% responsibility for the integrity of the code they submit.

## AI Tooling Policy: Tools as Standard

As of 2026, using AI (LLMs, etc.) for engineering is as standard as using a compiler or an IDE.

- No Mandatory Disclosure: Contributors are not required to disclose AI usage in commit messages or PRs.
- Human Accountability: Regardless of the tools used, the human engineer who submits the code bears 100% responsibility for its consequences.
- Evaluation Criteria: Reviewers evaluate only architectural consistency, logical correctness, security, and test compliance. Low-quality code that lacks proper human direction and validation will be rejected regardless of its origin.
- Extended Use of AI: AI can be actively utilized in areas difficult to codify, such as cultural synthesis or streamlining communication. We encourage using AI as an aid to improve decision-making and efficiency.

## Communication Guidelines

Keep communication lean, clear, and "dry."

- Issue Reporting: Reports should be brief, including clear reproduction paths, expected vs. actual results, and relevant logs.
- Limits on Debate: “Tooling wars” (religious debates over tech stacks) are prohibited. Propose alternatives only with objective data, such as benchmarks or architectural design documents.
- Self-Eliminating Non-Technical Discussions: Topics unrelated to technical goals will naturally go unnoticed and die out. Persistent attempts to steer the project toward external social agendas will result in a natural loss of influence.
- LLM-Enabled Global Collaboration: English is our common tongue, but not everyone's native language. We strongly encourage using powerful LLM models for translation and drafting to bridge communication gaps.

## Contribution Process
### Commit Signing (GPG)
Every commit must be GPG-signed. This provides technical provenance and clarifies accountability. Unsigned commits will be automatically rejected by the CI.

### Pull Request (PR) Criteria
- Atomic Changes: A single PR should contain one logical change.
- Self-Review: Validate your logic before submission. If AI assisted you, double-check its edge cases and logic.
- Test-Driven: New features and bug fixes must include automated tests. PRs that fail CI will not be reviewed.
- Technical Description: State the *problem* and the *technical reasoning* behind your solution. Link related issues where applicable.

Before merging, a PR must:
- Pass all CI tests.
- Receive approval from at least one reviewer.
- Have no merge conflicts.

### Code Style and Quality
- For Rust: Adhere to `rustfmt` and `clippy` conventions.
- General: Comply with the linter configurations in the repository root.
- Documentation: Public APIs must include clear documentation comments.

## Decision Making
- Routine Changes: Decided via peer review and CI success.
- Major Architecture (RFC): Significant changes are discussed in a dedicated RFC issue with a 7-day window. Decisions are made by core contributors or maintainer judgment.
- Progress Over Consensus: In the event of a deadlock, maintainers will make the final call. We prioritize momentum over perfect agreement.

## Culture and System Protection
We maintain a community of professionals focused on technical productivity.

### Cultural Self-Purification
Personal attacks, slander, or insults are not tolerated. We do not exercise “punishment” in an authoritarian manner; instead, those who persistently act unproductively will be recognized as incompatible with the project’s culture, and their participation will naturally become meaningless. This is the “self-purification” system we believe in.

### Technical Defense As Infrastructure Protection
We reserve the right to immediately block malicious technical actions that physically threaten the project’s momentum. This is a matter of resource protection, not ideological judgment:
- Resource Exhaustion: Intentional CI/CD spamming or storage abuse.
- Security Threats: Injecting malware, backdoors, or unauthorized data.
- Automation Abuse: Using bots with the deliberate intent to paralyze project workflows.

Maintainers may restrict access or report to platform providers solely to ensure the continued operation of the system.

---

All contributions that move SSCCS forward are sincerely welcome.
 