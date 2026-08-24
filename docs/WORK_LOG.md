# LatentTarget GPU-free completion log

This is the chronological, human-readable record of the work performed before
any paid GPU or API experiment. It distinguishes code/test results from mock or
synthetic validation and from claims that still require a real model.

## Scope

- Included: design audit, current-model/tooling verification, literature
  verification, simulator and control implementation, Bayesian evidence
  baseline, power/sensitivity analysis, open-weight capture/black-box/steering
  interfaces, unit tests, mock and synthetic end-to-end validation, and the GPU
  handoff.
- Excluded: renting a GPU, downloading a 27B checkpoint, paid API calls, and any
  empirical claim about real LLM behavior.
- Date started: 2026-08-25 (Asia/Kolkata).

## Chronological entries

### 1. Baseline audit

- Read the experiment description supplied by the researcher.
- Read the experimental-design and statistical-power instructions.
- Attempted to load the requested GSD AI-integration/audit workflows. Their
  `SKILL.md` files were present, but the referenced workflow/reference files
  were not installed. I therefore used a manual AI contract, explicit plan,
  verification gates, and this log rather than claiming GSD executed.
- Repository was not initialized as git; no commit or remote provenance was
  available. I did not initialize or push it because that is not required to
  finish the local scientific package and no permission to publish was given.
- Ran the complete starting test suite: **201 passed**.
- Confirmed that all existing data and reported metrics are mock/synthetic;
  there are **zero real-model results**.
- Identified four pre-GPU gaps:
  1. no Bayesian evidence-only comparator;
  2. swap-pair assignment was confounded with `episode_index` (and therefore
     with scenario sequence);
  3. the black-box and steering ideas were documented but not executable as
     complete scripts;
  4. no reproducible sample-size sensitivity analysis.

### 2. Current-model and tooling verification

- Verified from the official Hugging Face model page that the newest dense
  Qwen checkpoint available today is `Qwen/Qwen3.8-27B`, not the previously
  selected `Qwen/Qwen3.6-27B`.
- Verified that Qwen 3.8 uses the Qwen 3.5 multimodal architecture family,
  with 64 language layers and hidden width 5120, and that the official loading
  example uses `AutoProcessor` plus `AutoModelForMultimodalLM`.
- Found that the existing provider's loader (`AutoTokenizer` plus
  `AutoModelForImageTextToText`) did not match the current official example.
  This is a preflight risk to fix and test locally with mocks; the actual model
  load still requires the GPU gate.
- Located the intended anchor work: Chen et al., *What Kind of User Are You?
  Uncovering User Models in LLM Chatbots* (ICML 2025 Actionable
  Interpretability workshop). The public abstract reports residual-stream
  linear directions for inferred user attributes, causal mediation, and
  activation steering. Our differentiator is dynamic, outcome-only inference
  and revision after a silent change, not the generic claim that a user
  attribute is linearly decodable.

### 3. Bayesian evidence-only observer

- Added `src/bayesian_observer.py`.
- The observer sees only the serialized history visible before the current
  focal message. It never sees the active type, target scores, current outcome,
  noise draw, or true swap round.
- Integrated the logistic-normal response probability with deterministic
  Gauss-Hermite quadrature and a symmetric hidden-Markov change hazard.
- Set hazard 0.10 as primary with 0, 0.05, and 0.20 as sensitivity values.
- Added `scripts/analyze_bayesian_observer.py` with manifest verification so
  simulator parameters cannot be guessed from defaults.
- **VERIFIED:** quadrature agrees with a 300,000-draw Monte Carlo check within
  0.002; start-of-round alignment, no-history, shuffled-history, transition,
  and end-to-end output tests pass.

### 4. Swap counterbalancing fix

- Found that the previous post-swap partner was selected from
  `episode_index % 2`, while scenario sequence is also keyed by episode index.
  Ordered type transitions could therefore be associated with different
  scenarios.
- Changed swap construction to run both possible partners for each initial
  target and episode index. All six ordered transitions now share every
  scenario sequence.
- Consequence: at 8 episode seeds, the five default conditions now contain 144
  episodes and 1,248 focal generations (48 swap episodes).
- **VERIFIED:** experiment/counterbalancing tests pass.

### 5. Honest probe pipeline

- Found that the old “stable” training mask included `no_history` and
  `random_target`, where target identity is not inferable from valid evidence.
  Restricted fitting to stable typed `full_history` episodes only.
- Replaced same-data layer selection/reporting with a deterministic,
  target-stratified episode split: 50% train, 25% dev, 25% untouched test.
- Added a cheap nearest-centroid dev layer selector, dev-only L2 selection, and
  one final held-out test evaluation. No round crosses episode partitions.
- Added persistence for the full fitted probe, including feature mean/scale.
- Added same-test transcript readout and Bayesian evidence baselines. The probe
  must beat the strongest visible-evidence baseline by five points to clear the
  preregistered interest gate.
- Merged the Bayesian and probe swap trajectories and added a probe-minus-
  Bayesian trajectory contrast.
- **VERIFIED:** synthetic signal/noise, leakage, split, persistence, and probe
  trajectory tests pass. **GPU-BLOCKED:** no real activation was captured.

### 6. Executable mechanistic controls

- Added `scripts/run_black_box_baseline.py` and
  `src/black_box_baseline.py`. Each logged prompt is measured in a separate,
  deterministic forward pass; answers never re-enter an episode. Output is
  checkpointed after every guess and resumes without duplicate calls.
- Added probe-derived residual directions in original activation coordinates:
  target-vs-other contrast divided by the training standard deviation.
- Added generic text-layer discovery and a temporary forward hook that changes
  only the final token, with target, opposite, zero, and norm-matched random
  directions.
- Added `scripts/run_steering.py` with untouched test-prompt selection,
  coefficients 1/3/6, and paired sampling seeds.
- Added `scripts/analyze_steering.py` with episode-clustered paired contrasts
  and a dose-response plot.
- **VERIFIED:** direction construction, norm matching, hidden-state-to-block
  mapping, tuple/tensor hook behavior, hook removal, black-box resume, and
  steering analysis tests pass. **GPU-BLOCKED:** interventions have not been
  executed on Qwen.

### 7. Current-model preflight and loader

- Updated the primary model from Qwen 3.6 to the current official dense
  `Qwen/Qwen3.8-27B` checkpoint.
- Updated the pod requirement to Transformers 5.12 and the loader to try the
  official `AutoProcessor` + `AutoModelForMultimodalLM` path first, while
  retaining text-only fallbacks.
- The official card states that Qwen3.8 thinking mode is enabled by default.
  Disabled it explicitly and adopted the card's non-thinking top-p/top-k
  defaults so hidden reasoning cannot become part of the focal message.
- Added `scripts/preflight_open_weight.py`. It performs one generation,
  validates finite `[row, hidden_state, d_model]` captures against the number
  of text blocks, tests text-layer discovery, and requires zero-vector steering
  to reproduce greedy output.
- **VERIFIED:** local contract/preflight tests pass. **GPU-BLOCKED:** official
  checkpoint loading and exact hidden-state nesting remain unverified until the
  one-generation preflight.

### 8. Statistical design and power sensitivity

- Added the explicit primary model to `src/analysis.py`:
  `match ~ round + full_history + round:full_history`, using only stable full-
  and no-history episodes with episode-clustered standard errors.
- Added `src/power_analysis.py` and `scripts/power_analysis.py`. Simulations use
  episodes as independent units, paired scenario/type episodes, binary round
  outcomes, and episode random intercepts.
- Ran 2,000 simulations per grid cell and wrote
  `results/tables/power_sensitivity.{json,csv}` and
  `results/figures/fig_power_sensitivity.png`.
- **MOCK/SYNTHETIC ONLY:** under the current assumptions, 8 episode seeds are
  badly underpowered for a behavioral interaction; approximately 28 seeds
  reached 80% only for a large nominal 25-point late-round increase. A test
  initially assumed much higher power and failed; the conservative simulation
  was retained and the test expectation corrected.

### 9. Preregistration and literature audit

- Added `docs/PREREGISTRATION.md` with exact prompts, simulator equation,
  confirmatory endpoints, classifier/human gate, probe split, Bayesian hazard,
  steering controls, multiplicity, missingness, stopping, and checkpoint rules.
- Added canonical `report-source.md` with a claim-level literature audit,
  evidence-gap matrix, recommendation, and retrieval provenance.
- Paper-lookup provenance: bounded OpenAlex topic query (10 of 10,482 results,
  explicitly non-exhaustive), targeted OpenAlex exact-title records, Crossref
  title/DOI metadata, arXiv Atom parsing for GLEE, and official ICML/ACL/Hugging
  Face pages.
- Corrected the extra repeated-persuasion paper's DOI to
  `10.1162/tacl_a_00462`. Clarified that several GLEE strategy prescriptions in
  the supplied summary are engineering extrapolations rather than conclusions
  proved by the cited economic papers.
- Recorded a source limitation: the OpenReview API for the Chen et al. anchor
  was challenge-blocked, so only the official ICML public abstract supports the
  summary.
- Verified current Runpod list rates for an eventual cost bound, but made no
  rental or purchase.

### 10. Offline end-to-end validation

- Ran the complete suite after implementation: **231 tests passed** at that
  checkpoint.
- Ran `scripts/validate_pipeline.py`: oracle positive control was detected;
  win-stay/lose-shift adapted only with usable feedback; random, round-robin,
  and fixed-frame negative controls remained flat. **PIPELINE VALIDATION
  PASSED.**
- Ran a fresh four-seed mock pilot with the fully counterbalanced design: 72
  episodes, 624 rounds, complete raw JSONL/manifest, all behavioral tables and
  plots, and three full transcripts in `PILOT_REPORT_MOCK.md`.
- Ran the Bayesian observer on that mock. It trailed the deliberately model-free
  win-stay/lose-shift behavior, an expected negative mechanistic pattern. These
  values are not LLM evidence.
- Generated 624 synthetic oracle activation rows (5 layers × 64 dimensions)
  and ran the full train/dev/test probe script. It selected the planted layer,
  scored 1.0 on the untouched synthetic test set, and wrote probe/trajectory
  artifacts. **MOCK/SYNTHETIC ONLY.**
- This run caught a text-report bug: a generic probe-minus-Bayesian statistic
  carried a hard-coded “Bayesian faster” interpretation. Replaced it with a
  column-aware interpretation and added a regression assertion.
- Found that rerunning an existing `run_id` appended duplicate episodes.
  Changed the runner to fail closed on a nonempty log; interrupted work must use
  a new ID and be combined explicitly after manifest checks.

### 11. Final verification and adversarial review

- Reran the complete suite after all fixes: **233 tests passed** in 19.51
  seconds. The 14 warnings are deprecations inside the installed Matplotlib and
  pyparsing versions; there were no project warnings or failures.
- Ran Python bytecode compilation over `src`, `scripts`, and `tests`: passed.
- Reran the full synthetic probe command after fixing the generic trajectory
  interpretation. It selected the planted layer using dev data, achieved 1.0
  on the untouched oracle-coded synthetic test, and now describes the
  probe-minus-Bayesian result using the actual column names. This is a fixture
  check, not evidence about an LLM.
- Replaced the stale adversarial review with `docs/REVIEW.md`, which marks the
  Bayesian comparator, swap counterbalancing, honest layer selection,
  executable controls, duplicate-log guard, and pickle-free probe persistence
  as resolved. It retains construct validity, instrument circularity, prompt-
  evidence decoding, real loader compatibility, power, and random-control rate
  matching as open risks.
- All 16 command-line scripts return help successfully. No GPU-only command was
  executed.

### 12. Repository and spend boundary

- Queried the GitHub API and remote refs for
  `https://github.com/4r4cn1d0/LatentTarget`: the repository is public but empty
  (`size: 0`, no refs) as of this audit.
- Initialized the local directory as a `main`-branch git repository, recorded
  the empty GitHub URL as `origin`, and created a local initial commit. This did
  **not** push or otherwise change GitHub.
- Added generated activation/probe `.npz` files to `.gitignore`; raw and
  reclassified JSONL were already ignored. Manifests, code, documentation,
  aggregate tables, and figures remain versionable.
- Paid GPU experiments: **0**. Paid API calls: **0**. Model downloads: **0**.
- The next permitted step is exactly the one-generation preflight in
  `docs/POD_RUNBOOK.md`; the full experiment remains approval-gated.

## Status legend for later entries

- **VERIFIED:** executed locally and passed.
- **MOCK/SYNTHETIC ONLY:** validates machinery, not LLM behavior.
- **GPU-BLOCKED:** code prepared, but no real checkpoint was run.
- **OPEN:** unresolved scientific or engineering issue.
