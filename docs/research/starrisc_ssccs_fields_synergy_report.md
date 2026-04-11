# StarRISC Radiation-Hardened RISC-V and SSCCS

## SSCCS Field Composition Protocols and StarRISC RHBD Architecture 

**Date:** April 12, 2026  
**Author:** SSCCS Foundation  



## Abstract

This report analyzes the potential synergy between the **StarRISC** radiation-hardened RISC-V microcontroller and the **Schema–Segment Composition Computing System (SSCCS)**. While StarRISC provides robust hardware-level protection against radiation-induced errors through Radiation Hardening by Design (RHBD), it faces limitations regarding accumulated memory upsets and fixed hardware overhead. 

We propose leveraging the dual nature of **SSCCS Fields**—specifically their definition in **Section 2.3.3** of the SSCCS Whitepaper as both logical constraint sets and **executable, cryptographically signed binary units**. By treating fault tolerance policies as dynamic Field binaries that can be composed, sandboxed, and updated post-deployment, we can implement **Software-Defined Fault Tolerance (SDFT)**. This approach complements StarRISC’s physical hardening with adaptive, observation-based redundancy (temporal and spatial voting) without the area penalty of traditional Triple Modular Redundancy (TMR). This report outlines the architectural integration via OpenHW’s XIF interface and proposes a validation roadmap.



## 1. Introduction

Spaceborne and safety-critical computing systems require high reliability under ionizing radiation. The **StarRISC** microcontroller, developed by STARLab at the University of Saskatchewan, represents a state-of-the-art open-source RHBD RISC-V implementation [1]. It utilizes hardened flip-flops and SECDED ECC to mitigate Single Event Upsets (SEUs). However, hardware hardening is static: once fabricated, the protection mechanism cannot adapt to new error patterns or mission phases, and it incurs significant area and power costs.

Concurrently, the **SSCCS** paradigm redefines computation not as instruction sequencing, but as the **observation of stationary structures** under dynamic constraints [2]. Central to this model is the **Field**, a mutable substrate that governs which states are admissible. Crucially, **Section 2.3.3** of the SSCCS Whitepaper establishes that Fields are not merely abstract logic; they are **first-class executable binaries** that can be encrypted, signed, and sandboxed [2].

This report argues that the **binary nature of SSCCS Fields** offers a unique solution to the rigidity of traditional RHBD. By loading "Fault Tolerance Fields" onto a StarRISC-like platform, we can achieve adaptive, software-defined redundancy that evolves with the mission environment, reducing hardware overhead while enhancing resilience against complex failure modes like Multi-Bit Upsets (MBUs).



## 2. StarRISC: Baseline Capabilities and Limitations

### 2.1 Device Overview
StarRISC is based on the OpenHW CV32E40P core, fabricated in 22-nm FD-SOI technology. Key features include:
*   **Hardened Sequential Elements:** Stacked-transistor flip-flops resistant to SEUs up to high Linear Energy Transfer (LET) values.
*   **ECC Protected Memory:** SECDED (Single Error Correction, Double Error Detection) on SRAM.
*   **Performance:** Functional after 100 kRad (proton) TID and no SEFI up to LET ~96 MeV·cm²/mg [1].

### 2.2 Residual Vulnerabilities
Despite its robustness, StarRISC exhibits two critical limitations:
1.  **Accumulated/Complex Errors:** SECDED ECC corrects single-bit errors but fails against Multi-Bit Upsets (MBUs) in a single word or accumulated errors over time. Hardware voters (TMR) are effective but triple the area.
2.  **Static Protection:** The hardening strategy is fixed at design time. If a specific mission phase requires higher reliability for certain data structures, the hardware cannot dynamically increase redundancy without pre-designed, always-on overhead.



## 3. The Core Enabler: SSCCS Fields as Executable Binaries

The synergy with StarRISC relies entirely on the properties of SSCCS Fields described in **Section 2.3.3: Logical and Binary-Level Composition Protocols** [2].

### 3.1 Dual Nature of Fields
In SSCCS, a Field $F = (C, T)$ consists of a constraint predicate $C$ and a transition matrix $T$. While logically these define admissibility, physically:
*   **Fields are Executable Binaries:** A Field is compiled into a platform-independent binary format (`.field`) containing the logic for constraint evaluation and transition weighting.
*   **Cryptographic Integrity:** Fields can be digitally signed. This ensures that only authorized fault-tolerance policies (e.g., from Mission Control) are executed on the spacecraft, preventing malicious or corrupted updates.
*   **Sandboxing:** Fields execute in isolated environments. A faulty or compromised Field cannot corrupt the underlying Segment data or other Fields, providing inherent structural isolation [2].

### 3.2 Dynamic Composition
Fields support algebraic composition (Union, Intersection, Product) at the binary level [2]. This allows for **runtime reconfiguration** of fault tolerance strategies. For example:
*   **Normal Mode:** Load `Field_ECC_Light` (minimal checking).
*   **Solar Storm Mode:** Dynamically compose `Field_ECC_Heavy` $\cap$ `Field_Temporal_Vote` (strict temporal redundancy) and load it into the runtime.

This capability transforms fault tolerance from a **hardware feature** into a **software-defined service**.



## 4. Synergy: Software-Defined Radiation Hardening (SDRH)

We propose a hybrid architecture where StarRISC provides the **physical baseline** resilience, and SSCCS Fields provide the **adaptive, semantic** resilience.

### 4.1 Temporal Redundancy via Observation Fields
Traditional TMR uses three physical cores. SSCCS enables **Temporal TMR** using a single core via the `OBSERVE` primitive. A "Stability Field" can be defined to require that a Segment’s value remains consistent across multiple observations within a time window.

```rust
// Conceptual Rust-like pseudocode for a Stability Field
let stability_field = Field::new()
    .with_predicate(|segment| {
        let val_t0 = observe(segment);
        let val_t1 = observe(segment); // Re-observe
        val_t0 == val_t1 // Admissible only if stable
    })
    .sign_with(mission_control_key);
```

Because the Field is a signed binary, this logic can be uploaded and verified on-orbit. If radiation causes a transient upset in the register during the first observation, the second observation will likely differ, causing the Field to reject the projection and trigger a retry or error handler. This mitigates SEUs that escape hardware ECC without tripling the hardware.

### 4.2 Distributed Voting with Signed Fields
In a multi-core or swarm configuration, SSCCS Fields enable **Software-Defined Consensus**. A "Voting Field" can be broadcast to multiple StarRISC nodes. Each node observes its local Segment and projects a value. The Field’s transition matrix $T$ aggregates these projections using a majority vote or weighted average [2].

*   **Advantage:** No dedicated hardware voter is needed. The voting logic is contained within the Field binary.
*   **Security:** Since the Field is signed [2], a compromised node cannot inject a malicious voting algorithm. The integrity of the consensus mechanism is cryptographically guaranteed.

### 4.3 Mitigating MBUs with Semantic Constraints
Hardware ECC is blind to data semantics. An SSCCS Field, however, can enforce **semantic constraints**. For example, a Field governing a navigation coordinate can reject values that are physically impossible (e.g., sudden velocity jumps exceeding thrust capabilities). This acts as a secondary filter for MBUs that corrupt data in ways that ECC cannot detect (if they happen to form a valid codeword) or correct.



## 5. Architectural Implementation on OpenHW CORE-V

To realize this synergy, we propose implementing SSCCS runtime support on the **OpenHW CORE-V** platform, leveraging the **eXtension Interface (XIF)** [3].

### 5.1 Custom Instructions for Field Execution
Efficient execution of Field binaries requires hardware acceleration for the `OBSERVE` and `COLLAPSE` operations. We propose two custom instructions via XIF:

| Instruction | Operation | Description |
| : | : | : |
| `OBSERVE rd, rs1, rs2` | Project Segment | Reads Segment at `rs1`, applies Field at `rs2`, stores result in `rd`. Handles retry logic if configured. |
| `COLLAPSE rd, rs1, rs2` | Aggregate Projections | Combines multiple observations (e.g., from different cores/times) using the Field’s transition matrix $T$. |

These instructions allow the StarRISC core to offload the complex constraint evaluation of the Field to a tightly coupled coprocessor or accelerator, minimizing performance overhead.

### 5.2 Secure Field Loading
Leveraging the **Binary-Level Composition Protocols** [2]:
1.  **Upload:** New Field binaries (e.g., updated fault tolerance policies) are uploaded to StarRISC’s secure memory.
2.  **Verification:** The SSCCS Runtime verifies the Ed25519/ECDSA signature of the Field binary against a root of trust stored in OTP.
3.  **Sandboxing:** The Field is loaded into a protected memory region (using PMP - Physical Memory Protection). It can only access Segments explicitly granted permission, preventing side-channel attacks or fault propagation [2].



## 6. Proposed Validation Roadmap

We propose a joint validation effort between SSCCS Foundation and STARLab:

1.  **Phase 1: Simulation**
    *   Simulate StarRISC core with SSCCS Runtime.
    *   Inject MBUs into SRAM.
    *   Measure detection rate of "Semantic Fields" vs. standard SECDED ECC.

2.  **Phase 2: FPGA Emulation**
    *   Implement `OBSERVE`/`COLLAPSE` via XIF on an FPGA-emulated CV32E40P.
    *   Demonstrate dynamic loading of signed Field binaries.
    *   Benchmark area/power overhead compared to hardcoded TMR.

3.  **Phase 3: Radiation Testing**
    *   Expose the hybrid system to heavy-ion testing.
    *   Validate that software-defined Fields can recover from errors that exceed hardware ECC capabilities.



## 7. Conclusion

The integration of **StarRISC** and **SSCCS** represents a paradigm shift in radiation-hardened computing. By exploiting the **executable binary nature of SSCCS Fields** [2], we can move beyond static hardware hardening to **adaptive, software-defined resilience**.

This synergy offers:
*   **Reduced SWaP:** Lower area/power than full TMR by using temporal redundancy and smart voting.
*   **Adaptability:** Post-launch updates to fault tolerance strategies via signed Field binaries.
*   **Enhanced Security:** Cryptographic verification of all governance logic [2].

We recommend initiating a collaborative proof-of-concept using the OpenHW CORE-V ecosystem to validate this architecture, positioning SSCCS as the essential software substrate for next-generation resilient space computing.



## References

[1] C. J. Elash et al., "Efficacy of Radiation Hardening by Design Techniques on an ASIC 32-bit RISC-V Microcontroller," *2024 IEEE Nuclear and Space Radiation Effects Conference (NSREC)*, 2024.  
🔗 [IEEE Xplore / STARLab Publication](https://research-groups.usask.ca/starr-lab/research-projects.php) *(Note: Specific link to NSREC paper to be inserted upon final publication availability)*

[2] T. Lee, "Schema–Segment Composition Computing System (SSCCS) Whitepaper," SSCCS Foundation, Feb. 2026. DOI: 10.5281/zenodo.18759106.  
🔗 [SSCCS Whitepaper (PDF)](https://doi.org/10.5281/zenodo.18759106)  
🔗 [Section 2.3.3: Logical and Binary-Level Composition Protocols](https://doi.org/10.5281/zenodo.18759106)

[3] OpenHW Group, "CORE-V eXtension Interface (XIF) Specification," GitHub Repository.  
🔗 [OpenHW CORE-V XIF](https://github.com/openhwgroup/core-v-xif)

[4] STARLab, University of Saskatchewan, "Radiation-Hardened Digital and Analog Circuits."  
🔗 [STARLab Research Projects](https://research-groups.usask.ca/starr-lab/research-projects.php)