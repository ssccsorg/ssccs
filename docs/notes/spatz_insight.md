# Spatz–SSCCS Structural Insights 

A Structural–Physical Synthesis for Deterministic and Efficient Computation



## Abstract

This report presents a unified interpretation of the SSCCS whitepaper and the Spatz architecture. SSCCS defines computation as a structural process over stationary data, while Spatz provides empirical evidence of the physical constraints governing efficient execution. By combining both, we derive a formal execution model in which computation is expressed as structure and bounded by memory bandwidth, register capacity, and dataflow balance. The result is a constraint‑complete view of computation: structure defines what is computed, and physical balance determines whether it can be executed efficiently and deterministically.

---

## 1. Introduction

Spatz, a compact RISC‑V vector processor cluster with a shared‑L1 scratchpad memory (SPM) and a tiny 2 KiB vector register file (VRF), investigates how modern hardware achieves high efficiency. Its results—95% FPU utilisation, 30% higher energy efficiency than a scalar cluster, and minimal register capacity—demonstrate that performance is not compute‑bound but constrained by data supply and storage balance.

The key insight is that these two perspectives are not independent. SSCCS implicitly assumes a physical model that Spatz makes explicit. This report formalises that connection.

---

## 2. Structural Model (SSCCS)

A *Scheme* is defined as a directed graph  

$$
\mathcal{S} = (V, E)
$$

where $V$ represents *Segments* (immutable atomic coordinates) and $E$ represents adjacency relations.

A *MemoryLayout* is a mapping  

$$
L: V \rightarrow \mathcal{A}
$$

where $\mathcal{A}$ is the physical address space. The mapping preserves locality such that adjacent Segments are placed in physically adjacent memory regions (same cache line, adjacent memory banks).

An *Observation* is a function  

$$
O: V' \rightarrow R
$$

where $V' \subseteq V$ and $R$ is the projection space (ephemeral results). Observations are recomputed when needed.

This model implies:

- Computation is defined by structure, not instruction order.
- Data remains stationary (zero movement of input data).
- Parallelism emerges from structural independence (no locks, no synchronisation).

---

## 3. Physical Model (Spatz)

A hardware instance is defined by three parameters:

$$
H = (C_F,\; \beta,\; Z)
$$

where  

- $C_F$: compute footprint (operations per cycle, e.g., FPU width)  
- $\beta$: memory bandwidth (data units per cycle from L1 to PEs)  
- $Z$: register capacity (VRF size in bytes)

Spatz introduces the fundamental **balance constraint**:

$$
C_F \cdot \beta \le \sqrt{Z}
$$

This condition is not an optimisation but a **requirement for sustained execution**. If violated, the system cannot supply data fast enough to keep compute units active, leading to pipeline stalls.

Additional empirical results from Spatz:

- High utilisation (95%) can be achieved without large register files.
- Compiler‑managed scratchpad memory (SPM) can replace hardware caches, eliminating cache‑miss unpredictability.
- Data‑level parallelism (DLP) alone is sufficient for high efficiency; complex instruction‑level parallelism (ILP) logic (out‑of‑order, branch prediction) is unnecessary.

---

## 4. Execution Feasibility

Execution in SSCCS must satisfy physical constraints. A `MemoryLayout` is **feasible** if:

$$
C_{F,O} \cdot \beta \le \sqrt{Z} \quad \text{for all Observations } O
$$

where $C_{F,O}$ is the compute footprint of the projector for that Observation.

If this condition is not met, the Observation stalls due to insufficient data supply.

Therefore:

- `MemoryLayout` is not merely a locality optimisation; it is a **constraint satisfaction problem**.
- An SSCCS program (Scheme + set of Fields) is executable if and only if its layout satisfies the balance condition for all Observations.

---

## 5. Throughput and Performance Bound

Let $T$ be the throughput of an Observation (results per cycle). Then:

$$
T \le \min\left( C_F,\; \beta \cdot \rho \right)
$$

where $\rho$ is the **data reuse factor** induced by the `MemoryLayout` (how many times each loaded data unit is used before being evicted). This implies:

- Compute capacity alone does not determine performance.
- Effective bandwidth, amplified by reuse, is equally critical.

Performance is bounded by the minimum of compute rate and data supply rate.

---

## 6. State and Register Capacity

Spatz shows that a small VRF (2 KiB) is sufficient for high utilisation. The optimal register capacity can be approximated as:

$$
Z_{\text{opt}} \approx (C_F \cdot \beta)^2
$$

If $Z$ exceeds this bound significantly:

- additional capacity does not improve throughput,
- energy efficiency decreases (larger register files consume more static power and area).

Thus:

- State is not a performance resource beyond a threshold.
- Optimal execution favours **minimal state**.

In SSCCS terms, this validates **stateless or near‑stateless Observations** – projectors should not hold large internal buffers.

---

## 7. Data Movement Revisited

SSCCS claims elimination of data movement. This requires refinement.

Total data movement can be decomposed as:

$$
C_{\text{total}} = C_{\text{input}} + C_{\text{projection}}
$$

SSCCS minimises $C_{\text{input}}$ by ensuring data locality (stationary Segments). However:

$$
C_{\text{projection}} > 0
$$

because Observations produce new data that must be consumed downstream (e.g., as input to another Field). Therefore:

- Data movement is **not eliminated** – it is **transformed** into a structured dataflow.
- The correct interpretation: execution is a **bandwidth‑constrained flow system**, not a zero‑movement system.

Spatz’s balance condition provides a way to predict when projection movement becomes a bottleneck.

---

## 8. Parallelism

In SSCCS, parallelism arises from independent subgraphs. If two subgraphs share no vertices or edges, their Observations can be executed concurrently without synchronisation.

Spatz confirms that:

- Data‑level parallelism alone can saturate compute units.
- Near‑linear scaling is achievable under balanced conditions (Spatz Fig. 10 shows near‑linear speedup on two cores).

Therefore: parallelism is a **property of structure**, realised through **balanced dataflow**.

---

## 9. Memory Model: Cache vs. Structured Layout

Traditional architectures rely on caches, which infer locality dynamically through hardware heuristics. Spatz replaces this with a **compiler‑managed scratchpad memory (SPM)**.

This implies a fundamental shift:

- From runtime heuristics to compile‑time determinism.
- From probabilistic locality to **guaranteed locality**.

SSCCS extends this idea: `MemoryLayout` becomes a **declarative specification** of data placement. The compiler does not guess; it enforces adjacency.

Thus: memory is not an optimisation layer but part of the **computational definition**.

---

## 10. Unified Formal Model

An execution instance can be represented as a tuple:

$$
\mathcal{E} = (\mathcal{S},\; L,\; O,\; H)
$$

where  

- $\mathcal{S}$ defines the structural graph (Segments + adjacency),
- $L$ defines the physical placement (MemoryLayout),
- $O$ defines the observation operator (projector),
- $H$ defines the physical hardware parameters $(C_F, \beta, Z)$.

Execution is **valid** if:

1. $C_{F,O} \cdot \beta \le \sqrt{Z}$ for all Observations $O$ (balance condition),
2. Observations operate with minimal state ($Z \approx Z_{\text{opt}}$),
3. Dataflow remains within bandwidth limits ($\beta$ not exceeded).

---

## 11. Integrated Interpretation

Combining SSCCS and Spatz yields a complete computational model:

- **SSCCS** defines the *structure* of computation (what is computed, how data is related).
- **Spatz** defines the *feasibility* of execution (whether the structure can be mapped to hardware without stalling).

Thus:

$$
\text{Computation} = \text{Structure} \times \text{Physical Balance}
$$

This implies:

- Layout determines execution behaviour.
- Bandwidth determines execution viability.
- State determines efficiency bounds.

---

## 12. Conclusion

The integration of SSCCS and Spatz leads to a holistic model of deterministic, efficient computation.

**Key conclusions:**

- Computation is not instruction‑driven but **structure‑driven**.
- Performance is not compute‑limited but **bandwidth‑limited**.
- State is not a scaling resource beyond a physical threshold.
- Data movement is **transformed, not eliminated** – it becomes a structured, bandwidth‑controlled flow.

**Final statement:**

> Computation is a structured dataflow process executed under strict physical constraints on bandwidth and storage.  
> SSCCS provides the structural language.  
> Spatz provides the physical laws.  
> Together, they define a deterministic and efficient model of computation.

---

## Appendix: Detailed Mapping of Spatz Insights to the SSCCS Whitepaper

This appendix re‑evaluates the Spatz paper in direct reference to specific sections of the current SSCCS whitepaper (docs.ssccs.org).

### A.1 Compiler‑Managed Memory vs. Hardware Caches

| Spatz | SSCCS (whitepaper §5.2 “Memory Mapping Logic”) |
|-------|--------------------------------------------------|
| Uses a scratchpad memory (SPM) where data placement is decided at compile time. | Defines a `MemoryLayout` abstraction that maps logical adjacency to physical addresses (row‑major, space‑filling curve). The compiler resolves layout offline. |
| SPM gives predictable latency and energy because no cache misses occur. | The compiler’s layout guarantees that structurally adjacent Segments are placed in the same cache line or adjacent memory banks – effectively making the memory system behave like an SPM for observation. |

**Insight confirmed:** Spatz shows that a compiler‑managed memory can achieve 95% FPU utilisation on a 2D workload while being energy‑efficient. This directly supports SSCCS’s decision to make memory layout a compile‑time, declarative step.

### A.2 The Efficiency of Small, Specialised Units

| Spatz | SSCCS (§3.4 “Observation and Projection”) |
|-------|-------------------------------------------------|
| A 2 KiB VRF is sufficient; large register files waste energy. | Observers (projectors) are lightweight; they do not hold large internal state. Observation is a stateless operation that reads from stationary Segments and produces a projection. |

**Insight:** Spatz provides empirical evidence that “smaller can be better”. For SSCCS, this justifies keeping the observation runtime minimal – no heavy vector register files, no out‑of‑order logic. The projector can be a simple sequence of memory reads and arithmetic operations, sized exactly to the data path needed for the target hardware.

### A.3 Data Movement as the Primary Bottleneck

| Spatz | SSCCS (§5.3 “Automating Manual Optimisations”) |
|-------|--------------------------------------------------|
| Explicitly cites the von Neumann bottleneck (one‑word‑at‑a‑time) as the main obstacle to energy efficiency. | Eliminates data movement by making all data stationary. The only movement is the projection result. |

**Nuance added by Spatz:** Even with a stationary data model, the projection itself must be moved to where it is used (e.g., as input to another Field). Spatz’s balance condition $C_F \beta \le \sqrt{Z}$ suggests that SSCCS needs a similar **balance condition** for the observation operator. If the projector consumes more data per cycle than the memory hierarchy can supply, the observation will stall – violating deterministic execution.

**Recommendation:** The SSCCS compiler should incorporate a performance/power model to warn when a `MemoryLayout` leads to an unbalanced observation (e.g., when the projection’s data footprint exceeds the local cache capacity).

### A.4 Data‑Level Parallelism Without ILP Complexity

| Spatz | SSCCS (§3.2 “Scheme” and §4.2 “Concurrent Observation”) |
|-------|----------------------------------------------------------|
| Relies on DLP and avoids complex ILP (out‑of‑order, branch prediction). | Parallelism emerges from structural independence in the Scheme. No locks, no atomic operations. |

**Insight:** Spatz demonstrates that DLP alone, when properly supported by a compiler‑managed memory, can achieve high efficiency. This matches SSCCS’s principle that concurrency is not programmed but derived from the Scheme’s relation graph. The whitepaper’s claim that “independent sub‑graphs can be observed concurrently” is validated by Spatz’s cluster of compact vector processors: each PE can independently process a sub‑graph without synchronisation, as long as data is laid out in the SPM.

### A.5 The Trade‑off Between Flexibility and Specialisation

| Spatz | SSCCS (§7 “System Stack and Runtime”) |
|-------|------------------------------------------|
| Uses a programmable RISC‑V vector core instead of a fixed‑function accelerator, to retain flexibility for evolving AI models. | Uses a generic `Field` abstraction and a compiler that can retarget the same Scheme to different hardware (CPU, FPGA, PIM). |

**Insight:** SSCCS’s approach – a structural blueprint (Scheme) plus a dynamic governance layer (Field) – is similar in spirit to Spatz’s programmable vector core. Both avoid locking into a fixed dataflow. However, Spatz quantifies the cost of flexibility: a processor‑based solution is about 30% more energy‑efficient than a scalar cluster, but still less efficient than a fully specialised accelerator. For SSCCS, this implies that the `Field` implementation should be **parametrisable** – e.g., a projector can be compiled to either a scalar loop, a vectorised loop, or a fixed‑function state machine, depending on the required flexibility.

### A.6 Concrete Recommendations for the SSCCS Whitepaper

| Section | Suggestion |
|---------|-------------|
| Memory‑Layout Resolution | Add a note that the compiler may balance the logical layout against the target’s cache line size and memory channel width, using a model similar to Spatz’s $C_F \beta \le \sqrt{Z}$. |
| Observation‑Code Generation | Mention that the projector can be compiled to a vectorised loop when the Scheme’s independent sub‑graphs are regular and dense – exactly the pattern Spatz exploits. |
| Hardware Mapping | Explicitly note that a shared scratchpad memory (SPM) or a compiler‑managed cache is a preferred target for the MemoryLayout; this avoids the unpredictability of hardware caches. |
| Limitations / Future Work | Acknowledge that the “zero data movement” claim applies only to input data; the projection results may still need to be moved. Spatz’s balance analysis can be used to predict when such movement becomes a bottleneck. |

### A.7 Conclusion of the Mapping

The Spatz paper provides **quantitative, real‑world evidence** that several core principles of SSCCS – compiler‑managed memory layout, lightweight observation units, reliance on data‑level parallelism, and the trade‑off between flexibility and specialisation – are not only theoretically sound but also practically achievable. The specific results (2 KiB VRF, 30% efficiency gain, 95% FPU utilisation) can be cited in the SSCCS whitepaper to ground its architectural claims. Conversely, Spatz’s balance equation and its treatment of data movement can help refine SSCCS’s own compiler heuristics and clarify the limits of “stationary data”.

The two works are highly complementary: Spatz shows *how* to build an efficient vector cluster; SSCCS shows *what* structural description makes such a cluster usable for a wide range of computations without sacrificing determinism or auditability.
