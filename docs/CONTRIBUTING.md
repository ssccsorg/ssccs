# Contributing

Thank you for your interest. This document outlines the technical procedures and standards for contributing code, documentation, and research to the project.

## Prerequisites

- Read the [Code of Conduct](/docs/CODE_OF_CONDUCT.md) to understand our community philosophy.
- All commits must be **GPG‑signed**. Unsigned commits will be rejected by CI.
- Install the Rust toolchain: `rustup` (see `rust-toolchain.toml` for the required version).

## Contribution Process

### 1. Commit Signing (GPG)

Every commit must be signed to provide provenance and accountability.

  ```bash
  git config --global user.signingkey <KEY_ID>
  git config commit.gpgSign true
  git commit -S -m "Your message"
  ```

### 2. Pull Request (PR) Criteria

PRs must be **atomic** – one logical change per PR.

- **Self‑review:** Validate your logic before submission. If AI assisted, manually verify edge cases.
- **Test‑driven:** Include automated tests for new features or bug fixes. PRs that fail CI will not be reviewed.
- **Description:** Clearly state the *problem* and the *technical reasoning* behind your solution. Link related issues.

**Merge requirements:**  
PR must pass all CI checks, receive approval from at least one reviewer, and have no merge conflicts.

### 3. Code Style and Quality

All contributions must follow the coding conventions, style guides, and testing practices established for the language in which they are written. The repository includes linters, formatters, and test harnesses to help maintain consistency.

- **Documentation:** Public APIs must be clearly documented, explaining their purpose, parameters, and behavior. Use the documentation style appropriate for the language (e.g., doc comments in Rust, Javadoc in Java, etc.).
- **Testing:** New features and bug fixes must include corresponding automated tests. The CI pipeline enforces that all tests pass before a PR can be merged.
- **Clean Code:** Write code that is readable, maintainable, and adheres to the principles of modularity and clarity. Avoid unnecessary complexity.
- **AI Usage:** Use of AI tools is encouraged as a standard. No disclosure is required, but the human engineer remains 100% accountable for the signed code. See the [Code of Conduct](/docs/CODE_OF_CONDUCT.md) for more details.

## Decision Making

- **Routine changes:** Decided via peer review and successful CI.
- **Major architecture changes:** Propose an **RFC** (request for comments) issue.  
  - Include a clear description of the change, motivation, and impact.
  - Allow at least 7 days for community discussion.
  - Final decision is made by maintainers based on technical merit and project direction.

If a discussion stalls, maintainers will make a call to keep momentum.

## Areas of Contribution

We welcome contributions in many forms:

- **Code:** Rust implementations, formal proofs, hardware descriptions (Verilog/VHDL).
- **Documentation:** Whitepaper improvements, tutorials, API docs.
- **Research:** Formal analysis, performance benchmarks, security audits.
- **Outreach:** Blog posts, talks, educational material.
 
For questions or discussions, use [GitHub Discussions](https://github.com/ssccsorg/ssccs/discussions).
 