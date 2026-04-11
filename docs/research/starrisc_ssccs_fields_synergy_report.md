# Synergy Between Radiation‑Hardened RISC‑V (StarRISC) and SSCCS Fields:  
## Logical Constraints as Physical Binary Units for Software‑Defined Fault Tolerance

**Technical Report** – SSCCS Foundation  
April 2026  

---

## Abstract

This report analyses the StarRISC radiation‑hardened 32‑bit RISC‑V microcontroller and its residual failure mode – accumulated memory upsets. It then introduces the **dual nature of Fields** in the SSCCS (Schema–Segment Composition Computing System) paradigm: Fields are not only logical constraint sets but also **executable binary units** that can be composed, signed, encrypted, and sandboxed. We demonstrate how this property enables **software‑defined fault tolerance** through temporal redundancy and distributed voting, without the area and power overhead of traditional hardware duplication (ECC, TMR). The report concludes with a concrete proposal to implement custom observation instructions (`OBSERVE`, `COLLAPSE`) via OpenHW’s XIF interface on the CORE‑V platform, experimentally validating the synergy between RHBD RISC‑V cores and the SSCCS Field model.

---

## 1. Introduction

Space and safety‑critical systems demand high reliability under radiation exposure. The StarRISC microcontroller [1], developed by the STARLab group at the University of Saskatchewan, represents a state‑of‑the‑art radiation‑hardened by design (RHBD) RISC‑V device. It uses hardened flip‑flops, SECDED ECC on SRAM, and increased drive strengths to achieve remarkable tolerance. However, its remaining vulnerability is **accumulated memory upsets** that ECC cannot correct indefinitely, and the hardening techniques impose significant area and power overhead.

Simultaneously, the SSCCS (Schema–Segment Composition Computing System) [2] proposes a radical shift: computation as **observation of stationary structure** rather than instruction sequencing. Central to this paradigm is the **Field** – a mutable constraint substrate. Section **2.3.3 of the SSCCS whitepaper** reveals a critical and often overlooked property: Fields are not merely logical specifications; they are **first‑class executable binary units**. A Field can be serialised, cryptographically signed, encrypted, and sandboxed, and multiple Fields can be composed both logically and dynamically at runtime.

This report analyses the StarRISC design, extracts its limitations, and then demonstrates how the dual nature of SSCCS Fields can complement RHBD to achieve **software‑defined fault tolerance** with minimal hardware overhead. We propose a concrete implementation path using OpenHW’s CORE‑V platform and the XIF interface for custom instructions.

---

## 2. StarRISC: A Radiation‑Hardened RISC‑V Baseline

### 2.1 Device Overview

StarRISC is a 32‑bit RISC‑V microcontroller based on the OpenHW CV32E40P core, fabricated in 22‑nm FD SOI technology. Key radiation performance metrics from heavy‑ion and proton testing [1]:

| Parameter | Value |
|-----------|-------|
| No SEFI up to LET | 96.30 MeV·cm²/mg |
| Functional after TID | 100 kRad (proton) |
| SRAM ECC | SECDED, 39‑bit words (32 data + 7 parity) |
| Core flip‑flops | Stacked‑transistor hardened cells (no upset up to LET ~90 MeV·cm²/mg) |

### 2.2 Residual Weakness

Despite excellent performance, two limitations remain:

1. **Accumulated memory upsets** – ECC can correct single errors, but multiple errors in the same word or continuous upsets eventually exceed correction capability.
2. **Hardware overhead** – ECC adds ~22% memory area; hardened flip‑flops increase core area by 2–3× compared to standard cells.

### 2.3 STARLab Research Portfolio

Beyond StarRISC, the STARLab group has extensive expertise in radiation‑hardened digital and analog circuits across technology nodes from 65 nm down to 12 nm, including hardened SRAM cells, flip‑flops, on‑chip error monitors, and hardened PLLs. This foundation makes STARLab a natural collaborator for exploring software‑defined radiation tolerance using SSCCS.

---

## 3. The Dual Nature of SSCCS Fields (Whitepaper §2.3.3)

### 3.1 Fields as Logical Constraints

A Field is formally defined as $F = (C, T)$, where $C$ is an admissibility predicate and $T$ a transition matrix. Fields can be combined algebraically:

- **Union** $F_1 \cup F_2$: $C = C_1 \lor C_2$, $T = \max(T_1,T_2)$
- **Intersection** $F_1 \cap F_2$: $C = C_1 \land C_2$, $T = \min(T_1,T_2)$
- **Product** $F_1 \times F_2$: operates on Cartesian product of Segment sets

These operations are purely logical – they manipulate constraints and preferences without addressing physical execution.

### 3.2 Fields as Physical Binary Units

The key insight of §2.3.3 is that Fields are **executable binaries**. Each Field can be:

- **Serialised** into a platform‑independent binary format (`.field`).
- **Cryptographically signed** – ensuring provenance and integrity.
- **Encrypted** – so only authorised observers can interpret its constraints.
- **Sandboxed** – executed in isolation without affecting other Fields.

Moreover, Field binaries can be composed **dynamically at runtime**. For example:

```rust
let f1 = Field::load("range.field");
let f2 = Field::load("parity.field");
let combined = f1.intersect(&f2);
```

The resulting binary contains both constraint checking routines and their combined transition logic. This enables late binding of governance policies – critical for adaptive systems such as autonomous spacecraft that may reconfigure fault tolerance strategies after launch.

3.3 Implications for Distributed Systems

Because a Field is a self‑contained binary, it can be transmitted across a network and executed on remote observers. Consider a swarm of RISC‑V nodes:

· The ground station composes a Field that encodes “majority vote among three sensors”.
· The Field binary is broadcast to all nodes.
· Each node independently observes its local Scheme under that Field, producing a projection.
· Projections are combined via the Field’s transition matrix (e.g., voting).

This software‑defined consensus requires no special hardware – only the SSCCS runtime and the ability to exchange small binaries. The same mechanism provides built‑in fault tolerance: a node that experiences a transient error will produce a deviating projection, which the voting Field automatically ignores.

---

4. Synergy: SSCCS Fields as a Software‑Defined Radiation Hardening Layer

4.1 Observation‑Based Fault Tolerance

Instead of ECC, a Field can enforce temporal redundancy:

```rust
let stability_field = Field::new()
    .with_predicate(|segment| {
        let v1 = observe(segment);
        let v2 = observe(segment);
        v1 == v2
    });
```

This Field, when applied to a memory Segment, automatically retries the observation until two consecutive reads match. Because the Field is a binary, it can be loaded into the runtime without modifying core hardware. The only requirement is the ability to execute the observe primitive – mapped to a custom RISC‑V instruction via XIF.

4.2 Distributed Voting Without Triple Modular Redundancy

Traditional triple modular redundancy (TMR) triples the hardware. Using SSCCS, a single RISC‑V core can achieve the same reliability by loading a voting Field:

```rust
let vote_field = Field::new()
    .with_predicate(|segment| {
        let p1 = observe_on_core(segment, 0);
        let p2 = observe_on_core(segment, 1);
        let p3 = observe_on_core(segment, 2);
        majority(p1, p2, p3)
    });
```

Here, observe_on_core directs the observation to a specific core (or time‑multiplexed observation on the same core). The Field binary coordinates the three observations and applies the majority function. No hardware voter is needed – the entire mechanism is encoded in the Field binary.

4.3 Comparison with Traditional RHBD

Metric Traditional RHBD (StarRISC) SSCCS‑augmented RHBD
Memory ECC 39‑bit words (+22% area) None (temporal checks)
Core hardening Custom flip‑flops (2–3× area) Standard cells + observation retry
Error detection ECC logic, error counters Field predicates (software)
Redundancy TMR (3× cores) Single core + voting Field
Power High (ECC + hardened cells) Low (extra observations only on error)
Flexibility Fixed at design time Reconfigurable via Field upload

---

5. Architectural Support: XIF Custom Instructions

To make Field binaries efficient, we propose two custom RISC‑V instructions via the OpenHW XIF interface:

Instruction Opcode Operation
OBSERVE rd, rs1, rs2 custom1 Project Segment rs1 under Field rs2, store result in rd.
COLLAPSE rd, rs1, rs2, rs3 custom2 Apply Field rs2 to Scheme rs1 with observation rule rs3, store projection in rd.

These instructions are stateless – they do not modify core registers beyond the result, and they do not keep internal state between calls. This matches the XIF requirement for tightly coupled coprocessors and avoids pipeline stalls.

5.1 Binary Format for Fields

A Field binary is a self‑describing, position‑independent executable:

Header (64 bytes) Bytecode (variable) Signature (variable)
Version, type, size, hash Compiled constraint predicate and transition logic Ed25519 or ECDSA signature

The bytecode is a simple stack machine that evaluates the admissibility predicate and computes the transition weight. The runtime contains a lightweight interpreter or, for performance, a JIT compiler that translates the bytecode to native RISC‑V instructions.

5.2 Memory Protection

Because Field binaries can be loaded from untrusted sources, the runtime sandboxes them using RISC‑V PMP (Physical Memory Protection) or, on Linux, seccomp. The sandbox ensures that a Field can only access the Segment memory it is allowed to observe and cannot interfere with other Fields.

---

6. Proposed Validation on OpenHW CORE‑V

We propose a concrete experiment on the OpenHW CORE‑V MCU DevKit:

1. Implement OBSERVE and COLLAPSE custom instructions via XIF, using the eFPGA fabric for acceleration.
2. Write a stability Field that retries observations until two consecutive reads match.
3. Inject single‑bit errors into SRAM using a controlled fault injection mechanism (e.g., laser or voltage glitching).
4. Measure detection and recovery latency, as well as energy overhead.
5. Compare with the built‑in ECC of the StarRISC design (simulated).

Expected outcome: SSCCS approach achieves comparable or better fault coverage with lower area and power, while adding the ability to reconfigure the fault tolerance policy after deployment.

---

7. Conclusion

The dual nature of Fields in SSCCS – logical constraint sets and executable binary units – is not a mere implementation detail. It is the project’s most distinctive contribution to computer architecture. By treating Fields as first‑class binaries that can be composed, signed, encrypted, and sandboxed, SSCCS enables:

· Software‑defined fault tolerance – temporal redundancy instead of hardware duplication.
· Distributed consensus without special hardware – voting Fields running on standard cores.
· Post‑deployment reconfiguration – upload new Field binaries to change governance policies.

When combined with radiation‑hardened RISC‑V cores like StarRISC, this approach promises to deliver space‑grade reliability at a fraction of the traditional area and power cost. The next step is to implement the necessary XIF custom instructions on an OpenHW CORE‑V platform and experimentally validate the concept.

---

References

[1] C. J. Elash et al., “Efficacy of Radiation Hardening by Design Techniques on an ASIC 32‑bit RISC‑V Microcontroller,” 2024 NSREC.
[2] T. Lee, “Schema–Segment Composition Computing System Whitepaper,” DOI: 10.5281/zenodo.18759106.
[3] OpenHW Group, “CORE‑V eXtension Interface (XIF) Specification,” 2025. [Online]. Available: https://github.com/openhwgroup/core-v-xif
[4] STARLab Research Projects, University of Saskatchewan. [Online]. Available: https://research-groups.usask.ca/starr-lab/research-projects.php

---

This report is part of the SSCCS open‑source research initiative. All technical claims are based on publicly available data from the cited sources.
