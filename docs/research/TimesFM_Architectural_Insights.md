# TimesFM Architectural Insights for SSCCS

## 1. Introduction

TimesFM (Time Series Foundation Model) is a decoder‑only transformer‑based foundation model for time‑series forecasting developed by Google Research. The recent version 2.5 introduces several architectural changes that are conceptually aligned with the SSCCS (Schema Segment Composition Computing System) paradigm. While TimesFM operates on classical hardware and uses standard neural arithmetic, its **system‑level design patterns** offer valuable inspiration for structuring immutable Schemas, mutable Fields, and observation‑driven Projections.

This document analyzes the TimesFM 2.5 codebase and extracts seven key technical directions that can inform SSCCS development.

## 2. Technical Patterns in TimesFM 2.5

### 2.1 Decoupling “Time” from a Special Axis

**What changed:** TimesFM 2.5 removed the explicit `frequency` indicator that was present in earlier versions. Time is no longer treated as a privileged dimension with a pre‑defined sampling rate; instead the model learns to treat it as one coordinate among many.

**Code evidence:**  
- No `frequency` parameter in `ForecastConfig` or model definition.  
- The patch‑based tokenizer (`input_patch_len=32`, `output_patch_len=128`) operates on raw time‑series values without any frequency‑specific preprocessing.  
- Rotary positional embeddings (`use_rotary_position_embeddings=True`) provide relative position information but do not assume a fixed periodicity.

**SSCCS insight:** Reinforces the idea that temporal semantics should not be hard‑wired; they can emerge from the structure of the coordinate space and the projection operator. In SSCCS, a “time” axis can be defined as an ordinary `AxisType::Continuous` or `AxisType::Discrete` with no special handling; the observation logic can still capture temporal relationships through structural adjacency.

**Technical Details:** The patch‑based tokenizer treats the input time series as a sequence of non‑overlapping windows of length `input_patch_len=32`. Each patch is linearly projected through a residual block (`ResidualBlockConfig`) that maps the raw values (plus a mask channel) into a 1280‑dimensional embedding. This embedding is then fed into the transformer stack. By avoiding any frequency‑specific normalization or feature engineering, the tokenizer effectively treats time as a uniform coordinate axis; the only temporal inductive bias comes from the positional embeddings and the causal attention mask. Rotary positional embeddings are applied to queries and keys before attention, using a sinusoid with geometrically increasing timescales (`min_timescale=1.0`, `max_timescale=10000.0`). This provides relative position information without assuming a fixed sampling frequency.

### 2.2 Separate Continuous Quantile Head as a Lightweight Projection

**What changed:** A dedicated 30 M parameter residual block (`output_projection_quantiles`) is added on top of the main forecast backbone. This block produces distributional outputs (quantiles) without recomputing the base representation.

**Code evidence:**  
- In the model definition, `TimesFM_2p5_200M_Definition` includes separate `output_projection_point` and `output_projection_quantiles` residual‑block configurations.
- The `use_continuous_quantile_head` flag in `ForecastConfig` controls whether the quantile head is used.  
- The forward pass returns both point forecasts and quantile spreads (`output_ts`, `output_quantile_spread`).

**SSCCS insight:** This mirrors the **Field + multiple projectors** pattern: one immutable Schema (the transformer backbone) produces a core representation, and different projection heads extract different views (point forecast, quantiles, etc.) without recomputing the base structure. In SSCCS, a single Field could be observed through several independent projectors, each yielding a different projection of the same underlying Segment.

**Technical Details:** The quantile head is a residual block with `input_dims=1280`, `hidden_dims=1280`, and `output_dims=10240` (10 quantiles × 1280 dimensions). It uses a Swish activation and no bias. The head projects the transformer's final hidden states into a high‑dimensional space that is later reshaped into quantile estimates. This design allows the model to produce distributional forecasts without modifying the core transformer parameters, exemplifying the SSCCS principle of multiple lightweight projectors on a single immutable Schema.

### 2.3 Static Context, Dynamic Forecast Horizon

**What changed:** The model accepts a fixed‑length context window (up to 16 384 points) and can generate forecasts of arbitrary length (`horizon`). The decoding loop uses a cache (KV‑cache) to incrementally produce outputs without re‑processing the entire context.

**Code evidence:**  
- `decode` method in the PyTorch implementation iterates over `num_decode_steps`, each step producing one output patch (`self.o`).
- `decode_caches` store intermediate transformer states to avoid redundant computation.  
- The `max_context` and `max_horizon` parameters in `ForecastConfig` are compile‑time limits, but the actual horizon can be smaller.

**SSCCS insight:** Matches the SSCCS concept of an **immutable Scheme** (the context window) and an **observation‑parameterized horizon**. The Scheme is fixed; the observation operator (`decode`) uses a runtime parameter (`horizon`) to determine how many projection steps to perform. The cache corresponds to incremental observation that reuses previously computed structural relationships.

**Technical Details:** The decode cache is implemented as a `DecodeCache` struct per transformer layer, containing `key` and `value` tensors of shape `[batch_size, decode_cache_size, num_heads, head_dim]`. The cache size is `num_input_patches + num_decode_steps * m` where `m = output_patch_len // input_patch_len = 4`. During autoregressive decoding, each step appends new key‑value pairs to the cache, avoiding recomputation of previous patches. This matches the SSCCS concept of incremental observation where intermediate structural resolutions are cached and reused across projection steps.

### 2.4 Frequency‑Agnostic Representation

**What changed:** By dropping the explicit frequency flag, the same model weights can handle time series with different sampling rates (e.g., hourly, daily, monthly). The model infers the underlying temporal structure from the data.

**Code evidence:**  
- No frequency‑specific normalization or feature engineering in the data loader.  
- The patch‑based tokenizer is invariant to the absolute time scale; it only sees values within each patch.  
- Rotary embeddings are scaled by position indices, not by real‑world time units.

**SSCCS insight:** Structural adjacency (e.g., closeness in time) does not have to be given by an external “frequency” parameter – it can be derived from the coordinate space itself. In SSCCS, adjacency relations can be defined purely through coordinate proximity, allowing the same Scheme to be projected onto differently‑sampled physical timelines.

**Technical Details:** TimesFM achieves frequency‑agnostic representation through two mechanisms: (1) per‑patch normalization (ReVIN) that removes global scale and shift, making each patch statistically similar regardless of sampling rate; (2) rotary positional embeddings that depend only on relative patch indices, not on absolute time units. The model’s invariance to affine transformations (`TimesFM(aX + b) = a·TimesFM(X) + b`) further ensures that scaling of the time axis does not affect the forecast shape. This allows the same weights to generalize across hourly, daily, or monthly series without retraining.

### 2.5 Separation of Inference and Fine‑Tuning (XReg Module)

**What changed:** Covariate adjustment is handled by an external `XReg` module that operates on the residuals of the base TimesFM forecast (or vice‑versa). The base model stays frozen while the linear adapter is fitted in‑context.

**Code evidence:**  
- The XReg library module implements `BatchedInContextXRegBase` that solves a ridge regression problem on the fly.
- `forecast_with_covariates` in the base module composes the TimesFM output with the XReg correction.
- The `xreg_mode` flag controls whether covariates are applied before or after the TimesFM forecast.

**SSCCS insight:** This matches the idea of an **immutable core** (the pre‑trained model) **+ a mutable Field** (the covariate adapter) that governs how observations are made. In SSCCS, the Scheme is immutable, but a Field can be mutated to incorporate external context; the observation then projects through the combined (Scheme + Field) state.

**Technical Details:** The XReg module implements `BatchedInContextXRegBase`, which solves a ridge regression problem `(XᵀX + λI)⁻¹Xᵀy` for each batch independently, where `X` are the covariates and `y` are the residuals of the base forecast. The regression weights are computed on‑the‑fly and applied to adjust the forecast, either additively or multiplicatively depending on `xreg_mode`. This enables covariate adaptation without updating the core model parameters, analogous to a mutable Field that overlays an immutable Scheme.

### 2.6 Declarative Configuration Objects

**What changed:** Inference‑time behavior is controlled by a `ForecastConfig` dataclass that captures normalization flags, quantile‑head usage, invariance guarantees, etc. This configuration is separate from the model weights and can be changed without reloading the checkpoint.

**Code evidence:**  
- The configuration module defines `ForecastConfig` with default values for `max_context`, `normalize_inputs`, `use_continuous_quantile_head`, etc.
- The `compile` method takes a `ForecastConfig` and generates an optimized decoding function accordingly.  
- Configuration options are used throughout the inference pipeline (padding, masking, normalization).
**SSCCS insight:** A lightweight way to package a **Field’s runtime policy** without altering the underlying Scheme. In SSCCS, a Field could be specified as a similar configuration object that travels with the observation request, describing how the observation should be resolved (e.g., resolution strategy, priority, allowed observers).

**Technical Details:** The `ForecastConfig` dataclass includes fields such as `max_context`, `max_horizon`, `normalize_inputs`, `use_continuous_quantile_head`, `force_flip_invariance`, and `infer_is_positive`. These flags control the behavior of the compiled decode function, enabling trade‑offs between accuracy, invariance, and performance. For example, setting `normalize_inputs=True` enables per‑patch ReVIN normalization, while `force_flip_invariance` extends the affine invariance guarantee to negative scalings. This configuration pattern mirrors the SSCCS concept of a Field policy that can be varied without modifying the underlying Scheme.


### 2.7 Model as a Resource, Not an Executable

**What changed:** Trained checkpoints are published on Hugging Face as `.safetensors` files and loaded as data. The same checkpoint can be used with different backends (PyTorch, Flax) and different inference configurations.

**Code evidence:**  
- `TimesFM_2p5_200M_torch.from_pretrained` downloads weights from Hugging Face.  
- `load_checkpoint` loads the `.safetensors` file into the model architecture.  
- The model class is framework‑agnostic; the same weights can be instantiated in PyTorch or Flax.
**SSCCS insight:** A Scheme plus its pre‑computed memory layout could be distributed as a binary blob that the runtime loads and observes – no per‑deployment recompilation needed. This aligns with the SSCCS vision of `.ss` files that describe an immutable structure and can be “projected” onto various hardware targets without re‑specifying the structure.

**Technical Details:** TimesFM checkpoints are stored in the `.safetensors` format, which serializes tensors without arbitrary code execution. The `from_pretrained` method downloads the checkpoint and loads it into a framework‑specific module (PyTorch or Flax) via a common architecture definition. This decoupling of weights from runtime allows the same trained model to be used across different hardware backends and inference configurations, directly analogous to the SSCCS vision of distributing a Scheme as a portable binary (`.ss` file) that can be projected onto diverse hardware targets.


## 3. Mapping to SSCCS Concepts

| TimesFM feature | SSCCS parallel | How SSCCS could implement it |
|----------------|----------------|-------------------------------|
| No explicit `frequency` | Time as an ordinary coordinate | Define a `AxisType::Continuous` axis named “time”; adjacency relations based on coordinate distance. |
| Separate quantile head | Multiple projectors on one Field | A single Field holds the base Segment; independent projector functions produce point forecasts, quantiles, confidence intervals, etc. |
| Fixed context, flexible horizon | Immutable Scheme, observation‑parameterized horizon | Scheme = context window; observation takes `horizon` parameter and iteratively projects new Segments using cached structural relations. |
| XReg covariate module | Mutable Field overlaying immutable core | Field contains covariate weights that can be updated in‑context; observation combines Scheme (time series) with Field (covariates). |
| `ForecastConfig` dataclass | Declarative Field policy object | A `FieldConfig` struct that specifies resolution strategy, triggers, priority, and other observation‑time parameters. |
| Checkpoint as distributable asset | `.ss` binary + pre‑computed layout | Serialize Scheme and its memory layout into a portable binary; load it into any SSCCS runtime for observation. |
| Patch‑based tokenization | Segment grouping by coordinate blocks | Define a “patch” Segment that aggregates a contiguous coordinate region; mapping from raw coordinates to patch Segments is a many‑to‑one relation. |
| Decode cache (KV‑cache) | Incremental observation reuse | Store intermediate projection results in a cache; subsequent observations can skip already‑computed structural resolutions. |

## 4. Implications for SSCCS Design

The TimesFM patterns suggest several concrete design choices for the SSCCS proof‑of‑concept:

1. **Axis‑type flexibility:** SSCCS should support axis types (continuous, discrete, cyclic, categorical) without privileging any particular dimension. Temporal semantics should emerge from relations, not from a built‑in “time” type.

2. **Projector polymorphism:** The core observation operator should be able to produce multiple projections from the same Field‑Scheme pair, possibly via lightweight “projection heads” that are compiled separately from the Scheme.

3. **Observation‑time parameters:** Like `ForecastConfig`, SSCCS should allow a configuration object to be passed with each observation request, specifying resolution strategy, horizon, quantization, etc., without modifying the Scheme.

4. **Incremental observation:** The decode‑cache pattern translates to storing intermediate structural‑resolution results, enabling efficient iterative projections (e.g., generating a sequence of values step‑by‑step).

5. **External adapters:** The XReg module demonstrates how external, mutable context can be cleanly separated from the immutable core. SSCCS could support “adapter Fields” that are fitted on‑the‑fly and composed with the base Scheme.

6. **Portable serialization:** The Hugging Face checkpoint model shows the value of distributing a trained model as a single file. SSCCS should define a binary format for Schemes that includes their structural graph and optional pre‑computed layout information.

## 5. Research Directions for SSCCS

The TimesFM 2.5 architecture reveals several time‑axis handling techniques that are not yet covered in the SSCCS whitepaper. These gaps represent concrete research topics that could extend the SSCCS model and improve its applicability to time‑series forecasting and other sequential domains.

### 5.1 Patch‑based Segment Grouping
TimesFM’s patch‑based tokenization groups contiguous time points into fixed‑length patches (input_patch_len=32, output_patch_len=128). In SSCCS terms, this corresponds to defining a “patch” Segment that aggregates a contiguous coordinate region. The mapping from raw coordinates to patch Segments is a many‑to‑one relation. Research topic: How can SSCCS Schemes efficiently express such hierarchical grouping, and how can the compiler map grouped Segments to hardware to preserve locality while enabling parallel observation?

#### Concrete SSCCS Construct
```ss
Scheme TimeSeriesPatch {
    axes: [
        (time: Continuous, unit: "second"),
        (value: Continuous, unit: "scalar")
    ],
    segments: [
        (interval: [t, t+32) → patch_id) for t in 0..T step 32
    ],
    relations: {
        grouped: (patch_id, [time_interval]) → hierarchical,
        adjacency: (patch_id, patch_id+1) → contiguous
    }
}
```
The `TimeSeriesPatch` Scheme defines a grouping relation that maps each 32‑step interval of the raw time axis to a distinct patch Segment. The compiler can then treat each patch as a single unit for observation, preserving spatial locality while enabling parallel projection across patches.

### 5.2 Relative Position Encoding via Rotary Embeddings
Rotary positional embeddings provide relative position information without assuming a fixed sampling frequency. In SSCCS, coordinate adjacency can be defined via distance metrics, but the model could benefit from explicit relative‑position projectors that encode cyclic patterns (e.g., sinusoidal embeddings). Research topic: Design a projector type that injects relative coordinate information into Field constraints, enabling frequency‑agnostic representation learning.

#### Concrete SSCCS Construct
```ss
Projector RotaryPositionEmbedding {
    input: (segment: Segment, dim: int),
    output: (embedding: Vector[dim]),
    parameters: {
        theta: float = 10000.0,
        base_freq: float = 1.0
    },
    apply: |segment| {
        let pos = segment.coordinate("time");
        let i = range(dim / 2);
        let freqs = 1.0 / (theta ** (2 * i / dim));
        let angles = pos * freqs;
        return vector([cos(angles), sin(angles)].flatten())
    }
}
```
The `RotaryPositionEmbedding` projector can be attached to any Field that requires relative position awareness. The compiler can fuse this projector with attention operations, similar to the rotary embeddings used in TimesFM's transformer layers.

### 5.3 Frequency‑Agnostic Representation Learning
TimesFM removes the explicit `frequency` parameter, letting the model infer temporal structure from data. SSCCS already treats time as an ordinary coordinate, but the whitepaper does not discuss how to learn axis‑type semantics from data. Research topic: Can a Field’s constraints be adapted dynamically to capture periodicity or other patterns observed in the coordinate distribution? This could lead to “self‑discovering” axis types.

#### Concrete SSCCS Construct
```ss
Field SelfDiscoveringAxis {
    scheme: TimeSeriesPatch,
    constraints: {
        axis_type: DynamicAxisType = infer_from_data(
            observed_coordinates: List[Coordinate],
            patterns: ["periodic", "linear", "categorical"]
        ),
        tolerance: float = 0.1
    },
    adapt: |observed| {
        let period = detect_periodicity(observed);
        if period > 0 {
            axis_type.set(Cyclic(period));
        } else {
            axis_type.set(Continuous);
        }
    }
}
```
The `SelfDiscoveringAxis` Field monitors the distribution of observed coordinates and updates its internal axis‑type representation accordingly. This enables the Scheme to capture temporal patterns without requiring a pre‑declared frequency, matching TimesFM’s frequency‑agnostic approach.

### 5.4 Incremental Observation Cache
The decode‑cache (KV‑cache) in TimesFM stores intermediate transformer states to avoid redundant computation during autoregressive generation. In SSCCS, this corresponds to caching intermediate structural‑resolution results across multiple observation steps. Research topic: Define a cache abstraction for Schemes that allows incremental observation, reusing previously computed projections while preserving determinism.

#### Concrete SSCCS Construct
```ss
Scheme CachedScheme {
    base: TimeSeriesPatch,
    cache: Map<SegmentId, Projection> = {},
    policy: {
        eviction: "LRU",
        max_size: 1000,
        persist_on_disk: false
    },
    observe: |segment| {
        if cache.contains(segment.id) {
            return cache[segment.id];
        } else {
            let result = base.observe(segment);
            cache.insert(segment.id, result);
            return result;
        }
    }
}
```
The `CachedScheme` wraps a base Scheme and transparently caches projection results. The cache can be warmed up during a preprocessing phase and reused across multiple observation steps, analogous to TimesFM’s KV‑cache that avoids recomputing previous transformer layers.

### 5.5 Lightweight Projection Heads
TimesFM’s separate quantile head is a 30 M parameter residual block that sits on top of the main backbone. This mirrors the SSCCS pattern of multiple projectors on a single Field. Research topic: Develop a compiler strategy for generating efficient “projection heads” as independently compilable units that can be attached to a Scheme without recomputing the base representation.

#### Concrete SSCCS Construct

```ss
Scheme ProjectionHead {
    base: TimeSeriesPatch,
    head: Projector = {
        input: base.embedding_dim,
        output: quantiles(0.1, 0.5, 0.9),
        layers: [Linear(1280, 512), ReLU(), Linear(512, 3)]
    },
    attach: |base_scheme| {
        let compiled_head = compile(head);
        return CombinedScheme {
            base: base_scheme,
            head: compiled_head,
            observe: |segment| {
                let base_proj = base_scheme.observe(segment);
                return head(base_proj);
            }
        };
    }
}
```
The `ProjectionHead` Scheme encapsulates a small neural network that can be compiled separately and attached to a base Scheme. This matches TimesFM’s quantile head, which is a residual block that operates on the backbone’s output without modifying the backbone itself.

### 5.6 External Adapter Modules (XReg)
The XReg module adjusts forecasts using covariates while keeping the core model frozen. In SSCCS, this is analogous to a mutable Field that overlays an immutable Scheme and can be fitted in‑context. Research topic: Design a composition mechanism for adapter Fields that can be dynamically updated based on external data, enabling fine‑tuning and personalization without altering the base Scheme.

#### Concrete SSCCS Construct
```ss
Field AdapterField {
    base: TimeSeriesPatch,
    mutable: Map<SegmentId, Vector> = {},
    fit: |covariates: Matrix, target: Vector| {
        // Ridge regression similar to TimesFM's XReg
        let weights = ridge_regression(covariates, target, alpha=0.1);
        mutable.set("weights", weights);
    },
    constraints: {
        allow_mutation: true,
        sync_with_base: false
    },
    observe: |segment| {
        let base_proj = base.observe(segment);
        let weights = mutable.get("weights");
        return weights * base_proj + bias;
    }
}
```
The `AdapterField` wraps an immutable Scheme and adds a mutable parameter layer that can be fitted to new covariates without changing the underlying Scheme. This mirrors TimesFM’s XReg module, which performs ridge regression on covariates while the core transformer remains frozen.
### 5.7 Declarative Configuration Objects
TimesFM’s `ForecastConfig` dataclass separates inference‑time behavior from model weights. SSCCS could adopt a similar pattern for Field policies. Research topic: Specify a configuration language for Fields that captures resolution strategies, triggers, priorities, and other observation‑time parameters, and integrate it with the SSCCS runtime.

#### Concrete SSCCS Construct
```toml
# Field configuration for a quantile‑forecasting task
[field]
scheme = "TimeSeriesPatch"
constraints = [
    { axis = "time", type = "Continuous", unit = "second" },
    { axis = "value", type = "Continuous", unit = "scalar" }
]

[projection]
type = "QuantileHead"
quantiles = [0.1, 0.5, 0.9]
hidden_dim = 512
activation = "ReLU"

[observation]
strategy = "incremental"
cache_enabled = true
max_cache_size = 1000

[adaptation]
enabled = true
adapter_type = "ridge_regression"
alpha = 0.1
```
The configuration file declaratively defines a Field’s behavior without requiring code changes. The SSCCS runtime can parse this configuration and generate appropriate projection, caching, and adaptation logic, similar to how TimesFM’s `ForecastConfig` controls inference‑time behavior.

### Summary of Architectural Mapping

| TimesFM Pattern | SSCCS Concept | Concrete Construct | Research Direction |
|----------------|---------------|-------------------|-------------------|
| Patch‑based tokenization | Segment grouping | `TimeSeriesPatch` Scheme | Patch‑based Segment Grouping |
| Rotary positional embeddings | Relative‑position projector | `RotaryPositionEmbedding` Projector | Relative Position Encoding via Rotary Embeddings |
| Frequency‑agnostic representation | Self‑discovering axis | `SelfDiscoveringAxis` Field | Frequency‑Agnostic Representation Learning |
| Decode‑cache (KV‑cache) | Incremental observation cache | `CachedScheme` wrapper | Incremental Observation Cache |
| Separate quantile head | Lightweight projection head | `ProjectionHead` Scheme | Lightweight Projection Heads |
| XReg covariate module | External adapter Field | `AdapterField` with mutable weights | External Adapter Modules (XReg) |
| ForecastConfig dataclass | Declarative configuration | TOML configuration language | Declarative Configuration Objects |


These directions illustrate how SSCCS can evolve by incorporating proven architectural patterns from modern foundation models. Pursuing them would not only make SSCCS more practical for time‑series tasks but also strengthen its general‑purpose structural‑computing foundations.

## 6. Conclusion

TimesFM 2.5 provides a rich source of architectural inspiration for SSCCS, not because of its internal transformer mechanics, but because of its **system‑level separation of concerns**: immutable context vs. mutable configuration, core representation vs. lightweight projection heads, and the treatment of time as just another coordinate.

By adopting these patterns, SSCCS can evolve into a more flexible and efficient structural‑computing framework, where the same immutable Scheme can be projected in many different ways, adapted to new data on the fly, and distributed as a reusable computational resource.
 
---

© 2026 [SSCCS Foundation](https://ssccs.org) — A non-profit research and engineering initiative building a computing model and compiler infrastructure.

- Whitepaper: [PDF](https://ssccs.org/wp) / [HTML](https://ssccs.org/wpw) DOI: [10.5281/zenodo.18759106](https://doi.org/10.5281/zenodo.18759106) via CERN/Zenodo, indexed by OpenAIRE. Licensed under *CC BY-NC-ND 4.0*.
- Official repository: [GitHub](https://github.com/ssccsorg). Authenticated via GPG: [BCCB196BADF50C99](https://keys.openpgp.org/search?q=BCCB196BADF50C99). Licensed under *Apache 2.0*. 
- Governed by the [Foundational Charter and Statute](https://ssccs.org/legal) of the SSCCS Foundation (in formation).
- Provenance: Human-authored and AI-refined: linguistic and editorial review; full intellectual responsibility with author(s). All major outputs are [C2PA-certified](https://ssccs.org/wpc2pa).