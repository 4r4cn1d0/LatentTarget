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

### 13. Real-model preflight and four-seed behavioral gate

- Provisioned a RunPod Secure Cloud H100 80 GB at the listed $3.29/hour rate.
  Community A100 and H100 allocation attempts returned no capacity and created
  no billable pod.
- Cloned and verified commit `c65700d` on the pod, installed the pinned project
  requirements, and ran the entire suite: **233 tests passed in 29.30 seconds**.
- The first Hugging Face download used the 30 GB root overlay because SSH did
  not inherit `HF_HOME`. Moved the exact partial cache to `/workspace`, linked
  the default cache path to it, verified root/workspace disk usage, and reran
  with `HF_HOME` explicit. No experiment had started and no data were lost.
- **VERIFIED:** the official `Qwen/Qwen3.8-27B` checkpoint loaded as
  `Qwen3_5ForConditionalGeneration`; a real text generation succeeded; all 65
  hidden-state positions had shape `[1, 65, 5120]`; and zero-vector steering at
  hidden state 32 reproduced the unsteered greedy output exactly. Saved
  `results/tables/preflight_qwen38_27b.json`.
- Ran only the preregistered four-seed gate: `full_history` and `no_history`, 24
  episodes, 192 generations, eight rounds, no activation capture. Exactly
  **192 records** were written with zero process errors.
- Shared-lexicon result: full-history match 0.240, no-history 0.073;
  preregistered round-by-history coefficient +1.776 (`p=0.0318`). Marked this
  as instrument-circular because classifier/target argmax agreement was 1.0.
- Ran the zero-cost disjoint-lexicon sensitivity. Full-history match was 0.177
  versus no-history 0.063; the interaction stayed positive but uncertain
  (`p=0.222`), while type-alignment permutation values were 0.006 and 0.830.
- **PROBLEM:** both keyword instruments detected zero fairness-primary messages
  in the 32 full-history fairness rounds. Realized Option-A success was 0.333
  with history and 0.344 without it. No swap condition was part of this gate.
- Generated `PILOT_REPORT_REAL_QWEN38_27B.md`, a 40-row blind human-label sheet,
  primary/disjoint tables and figures, Bayesian observer diagnostics, and a
  five-transcript seeded sample. The raw 192-round JSONL is retained verbatim.
- Fixed a post-run reporting-only defect: empty swap plots now state that no
  swap episodes were run instead of emitting empty-legend warnings. Added
  regression coverage; no metric calculation changed. The final local suite
  passed **235 tests in 21.94 seconds**; bytecode compilation and diff checks
  also passed. The 14 warnings were third-party deprecations only.
- Copied and checksummed all artifacts before deletion. Deleted the pod with
  `HTTP 204`, verified that the account listed zero pods, and unset the API
  credential. Balance change was 1.1163558926 credits (about **$1.12**).
- **CHECKPOINT:** conditional behavioral GO, but full scaling is blocked on the
  preregistered human/independent-judge measurement gate and researcher
  approval. No activation, probing, steering, swap, random-target, or shuffled-
  history experiment has been run on the real model.

### 14. Independent measurement remediation (no new focal generations)

- Added a separate blind judge path using the logged-in Codex CLI and
  `gpt-5.6-luna`, a different family from the Qwen focal model. Inputs are
  deduplicated, deterministically shuffled, strict-schema constrained, cached,
  resumable, and preserved as exact batch input/output plus integrity metadata.
- Privacy-sanitized the eight process metadata files before commit. Exact judge
  inputs and final outputs are unchanged; local temporary paths, session IDs,
  duplicated prompts, and unrelated environment warnings were removed from
  process logs while their SHA-256 hashes and byte counts were retained.
- Reclassified all 192 saved rows (189 unique messages) in 8 batches. There
  were zero missing IDs, duplicates, schema failures, parse failures, or failed
  batch processes. No focal model, GPU pod, or new target response was run.
- Added a structural artifact audit. **VERIFIED:** each sample exposed only
  `sample_id` and `message`; condition, target, round, scenario, feedback, and
  choice were absent. Reconstructed prompt hashes, saved output hashes, sample
  sets, and return codes all pass.
- Independent result: full-history match 0.146 [0.063, 0.240] versus no-history
  0.042 [0.010, 0.073]. The preregistered history-by-round coefficient was
  +1.629 (OR 5.10, two-sided `p=0.058`). Full-history/no-history type-alignment
  permutation values were 0.047/0.846. Realized success remained 0.333/0.344.
  This is encouraging and underpowered, not confirmatory.
- Keyword/independent raw agreement was 0.630, Cohen's kappa 0.246, and 71/192
  primary labels changed. Target/judge argmax agreement was 0.541 rather than
  the circular 1.00 from the shared keyword instrument.
- Diagnosed the construct failure over **all rows**, not selected examples:
  the independent judge recovered 13 fairness messages and all 13 had received
  zero target fairness reward. Full-history fairness had 5/32 matches versus
  0/32 without history. Conversely, the independent judge found 0/32 expertise
  matches in full-history expertise episodes. It rejected all 36 old keyword
  expertise labels; 25 contained `professional` and 10 generic `experience`.
- Regenerated the concealed 40-row label key against the independent judge.
  **VERIFIED:** the public blind CSV remained byte-identical (SHA-256
  `0c5600bce298f8e227f46ae80fa0253ddd9c61870d61d53276b6ac98628ca618`)
  and still has 40/40 blank human labels.
- Made the human gate machine-readable and fail-closed: complete sheet, kappa
  at least 0.60, and matching full-history direction are all required. Removed
  the incorrect universal “1/3 chance” statement because `other` is a valid
  non-matching label.
- Generated `PILOT_REPORT_REAL_QWEN38_27B_INDEPENDENT.md` with the exact prompts,
  target logic, three fixed-rule transcripts, independent labels, probabilities,
  raw messages, and automatically surfaced failures.
- Added `docs/EVAL-REVIEW.md` and `docs/MEASUREMENT_REMEDIATION.md`. v1 is frozen;
  a human-validated, separately versioned scorer v2 is required before a
  two-seed (312-generation) all-controls checkpoint can be proposed.
- **OPEN / HUMAN-BLOCKED:** 0/40 blind rows are labelled. No paid run is
  authorized until that gate and the v2 calibration gate pass.
- **VERIFIED:** the expanded local suite passed 254 tests in 21.28 seconds with
  14 third-party deprecation warnings; bytecode compilation, `git diff
  --check`, structural judge audit, 36-file JSON parsing, both 192-row JSONL
  parses, deterministic artifact hashes, and credential-pattern scans passed.

## 2026-08-30 — bounded RunPod checkpoint and black-box baseline

- The researcher explicitly authorized paid RunPod execution, superseding only
  the prior lack of spending authorization. The measurement and v2 scientific
  gates were not waived.
- Rechecked the official model repository and retained `Qwen/Qwen3.8-27B`, a
  current dense open-weight checkpoint, rather than substituting an old model.
- Rented one Community A100 80GB PCIe pod at `$1.19/hour`, cloned exact commit
  `c3f7b285f7a01ccfac31b8dd6944ac1df18f07e5`, and recorded the complete
  environment. The pod was terminated in the same session and the API returned
  zero active pods. Estimated compute was no more than about `$0.75`.
- **VERIFIED ON RUNPOD:** all 254 tests passed in 60.65 seconds.
- **VERIFIED ON RUNPOD:** the bfloat16 activation/steering preflight passed with
  64 text layers, width 5120, activation shape `[1, 65, 5120]`, exact requested
  generation, and byte-identical zero-vector steering output.
- Ran the planned direct-elicitation baseline over all 192 immutable v1 prompts.
  Both full-history (96/96) and no-history (96/96) returned normalized
  `unknown`, for accuracy 0.000 in each condition. This is an exploratory
  black-box null, not evidence that no latent target representation exists.
- Found that the baseline discarded exact raw model strings. Audited a fixed
  round-8 row per target type; all three literal answers were `unknown`. Updated
  the code and tests so future runs checkpoint normalized and raw answers.
- Pulled all small artifacts before termination. The key was never added to the
  repository; temporary mode-0600 credential files were deleted.
- Full commands, versions, hashes, limitations, and result boundaries are in
  `docs/RUNPOD_CHECKPOINT_20260830.md`.

## 2026-09-01 — semantic scorer v2 failure and v3 held-out pass

- The researcher explicitly authorized every remaining non-human stage,
  including paid compute, while declining human labelling. Human validation
  therefore remains **0/40** and all subsequent work is labelled machine-only
  and exploratory.
- Implemented and froze semantic scorer v2 using the independently trained,
  revision-pinned `MoritzLaurer/deberta-v3-large-zeroshot-v2.0` checkpoint.
  Generated an 80-message calibration corpus and obtained a blind second
  `gpt-5.6-sol` judgment (agreement 0.825, kappa 0.767).
- Rented a Community RTX 3090 at `$0.22/hour` after an RTX A4000 at
  `$0.17/hour` failed to boot. V2's one-time held-out result was macro-F1 0.778
  but fairness recall 0.400, so the frozen gate failed. V2 was retired and was
  never used to generate focal-model outcomes.
- Demoted the v2 corpus to development data. On the 66 rows where its two
  machine references agreed, selected v3's 12-prototype grouping solely from
  construct metrics. The selected prompt had dev macro-F1 0.854 and fairness
  recall 0.750; a numerically higher macro-F1 variant was rejected because its
  fairness recall missed the frozen 0.70 requirement.
- Committed v3 (`0e4c6c0`) before creating a new test. `gpt-5.6-luna` then
  generated 80 unique outcome-free held-out messages, balanced 20 per class;
  a blind `gpt-5.6-sol` judge saw only opaque ID and message and agreed with all
  80 intended classes. Both references are machine-generated, not human gold.
- Scored the new corpus once on the RTX 3090. V3 achieved accuracy 0.9125,
  macro-F1 0.9140, fairness recall 0.950, minimum class F1 0.864, and 0/11
  expertise false positives on adversarial other messages. Every frozen gate
  passed.
- Retained an initial false gate report caused by the new corpus using an
  `adversarial` difficulty field instead of the legacy hard-negative tag.
  Repaired only the metadata selector and recomputed from the byte-identical
  predictions (SHA-256
  `80e55daf92605f9e089553e33d292e1cb9a2dfd6d9cf994b5e4ed197c848e885`)
  without loading or rerunning the scorer.
- Deleted both calibration pods and confirmed zero active RunPod pods. Approximate
  calibration compute was under `$0.10`; the provider ledger is authoritative.

## 2026-09-01 — v3 behavioral checkpoint frozen

- Updated the Bayesian evidence observer and probe pipeline to reconstruct the
  exact deterministic semantic scores from immutable logs. It now fails if a
  repeated message has inconsistent scores and cannot silently fall back to
  v1 keyword scoring.
- Strengthened the independent-measurement audit so every non-classifier field,
  including prompts, histories, target probabilities, scores, and seeds, must
  remain byte-for-byte equivalent after reclassification.
- Froze the two-seed, five-condition v3 checkpoint before any paid v3 focal
  generation: 36 episodes, 312 messages, all six ordered swaps twice, master
  seed `20260901`, official `Qwen/Qwen3.8-27B`, non-thinking sampling, and no
  activation capture.
- Added an executable fail-closed gate covering exact design counts, prompt and
  scenario invariance, independent-judge blindness, full/no-history contrast,
  shuffled donor alignment, random-response null behavior, wrong-start
  recovery, old-to-new swap revision, and support from at least two target
  types. All gates must pass before mechanistic spending.
- A direct pre-commit review found that the initial shuffled-history gate mixed
  a full-history round-1 row with round-2+ donor-evidence rows. Restricted both
  sides of that comparison to rounds 2–8 before freezing the commit.
- **VERIFIED LOCALLY:** 274 tests passed in 19.15 seconds with 14 third-party
  deprecation warnings; bytecode compilation, JSON parsing, prediction hashes,
  credential scans, and `git diff --check` passed.

## 2026-09-01 — paid v3 all-controls checkpoint and frozen STOP

- Retained the current official dense open-weight `Qwen/Qwen3.8-27B` rather
  than substituting an older model. Provisioned RunPod pod `po95efq6oldg52`, an
  A100-SXM4 80 GB at `$1.39/hour`, from exact pre-outcome commit `6d0c6e5`.
- **VERIFIED ON RUNPOD:** all 274 pre-run tests passed in 39.68 seconds under
  Python 3.12.3, PyTorch 2.9.1+cu128, Transformers 5.16.1, and Accelerate
  1.14.0.
- **VERIFIED ON RUNPOD:** `Qwen3_5ForConditionalGeneration` loaded through
  `AutoModelForMultimodalLM`; a real generation succeeded; 64 text blocks and
  width 5,120 were found; activation shape was `[1, 65, 5120]`; zero-vector
  steering at state index 32 was byte-identical to the unsteered generation.
- Ran the exact frozen v3 command with non-thinking sampling at temperature
  0.7, top-p 0.8, top-k 20, and 200 maximum tokens. The run completed 312/312
  generations in 41 minutes 10 seconds: 48 rows each for full, no, shuffled,
  and random-target conditions plus 120 swap rows. The 36 episodes include all
  six ordered swaps twice. No activation was captured.
- **VERIFIED:** no empty messages, duplicate round keys, missing swap pairs,
  classifier failures, or missing records. Source log SHA-256 is
  `692c11d3bbccbc16a94db6c579239b28c65a7fac02b942aa9a2fa7965f364dc9`.
- Deleted the pod after 3,580 seconds (`HTTP 204`) and verified zero active
  pods. Estimated charge is `$1.3823`; the provider ledger is authoritative.
  Deleted temporary credential files and confirmed the key was not written to
  the repository.
- Blindly classified all 312 unique messages with primary `gpt-5.6-sol` and
  sensitivity `gpt-5.6-luna` judges, 13 batches each. Both structural audits
  passed: judge-visible samples contained only opaque ID and message, and every
  non-classifier field was unchanged from the source log.
- Primary labels: 232 other, 53 risk, 23 fairness, 4 expertise. Sensitivity
  labels: 196 other, 50 risk, 44 fairness, 22 expertise. Inter-judge agreement
  was 0.814 with Cohen's kappa 0.624; 58/312 labels differed.
- Evaluated the precommitted fail-closed gate. Design integrity, blind
  measurement, random-response behavior, and minimal wrong-start recovery
  passed. Valid-history advantage, shuffled-history specificity, silent-swap
  revision, and support from at least two target types failed. Frozen decision:
  **`STOP_BEFORE_MECHANISTIC_EXPERIMENT`**.
- Primary full-history and no-history match were both 0.104. New-type match did
  not rise after swap (0.083 to 0.083), old-type match rose (0.067 to 0.100),
  and only risk supported a positive late history difference. The sensitivity
  judge also showed no advantage: 0.167 full-history versus 0.188 no-history.
  Applying the identical frozen gate to sensitivity labels also returned STOP,
  failing valid-history, random-response, silent-swap, and multiple-type gates.
- Ran the evidence-only Bayesian observer from exact logged v3 scores. At the
  primary 0.10 change hazard, full-history final-type accuracy was 0.208 versus
  the uniform 0.333 baseline, and the swap trajectory-gap 95% interval was
  `[-0.0799, 0.1177]`. Hazards 0, 0.05, and 0.20 did not rescue the result.
- Added a post-hoc simulator-capacity positive control that ignores outcomes
  when selecting one high-specificity saved message per dimension and then
  minimizes expected posterior entropy. Across 9,000 stable simulations it
  reached 0.738 target accuracy after eight outcomes (95% Monte Carlo interval
  `[0.729, 0.747]`); across 6,000 balanced swap simulations it recovered to
  0.567 active-target accuracy five rounds after the change (interval `[0.555,
  0.580]`). This shows the frozen response function is learnable under an
  oracle exploration policy; it does not change the focal-model STOP.
- Added deterministic instrument profiles and a complete inter-judge audit.
  The primary judge called 232/312 messages `other`; it found 0/16 expertise
  messages in the full-history expertise cell. The target's four-way semantic
  argmax was split almost equally between other (134) and expertise (133),
  exposing a construct/prevalence mismatch rather than a hidden positive.
- Corrected a reporting-only plot annotation: with `other` as a valid label,
  1/3 is a reference for policies restricted to the three rewarded frames, not
  a universal chance rate. No metric or decision changed.
- Generated `PILOT_REPORT_REAL_QWEN38_27B_V3_CHECKPOINT.md` with exact prompts,
  semantic target logic, twelve random messages, three complete fixed-rule
  transcripts, probabilities, classifications, metrics, failed gates, and an
  outcome-bound negative assessment.
- **VERIFIED LOCALLY:** 280 tests passed; bytecode compilation,
  both judge audits, inter-judge alignment, JSON/JSONL parsing, figure
  generation, visual figure inspection, and `git diff --check` passed. The 14
  warnings were third-party deprecations only.
- Human labels remain **0/40**. Stage E is completed as a conditional skip: no
  larger main run, activation dataset, probe, or steering experiment was run
  because the behavioral prerequisite was false. This is a scientific stop,
  not a code, compute, or authorization blocker.
- Exact commands, hashes, cost boundary, gate table, Bayesian analysis, and
  artifact map are in `docs/RUNPOD_CHECKPOINT_V3_20260901.md`.

## Status legend for later entries

- **VERIFIED:** executed locally and passed.
- **MOCK/SYNTHETIC ONLY:** validates machinery, not LLM behavior.
- **GPU-BLOCKED:** code prepared, but no real checkpoint was run.
- **OPEN:** unresolved scientific or engineering issue.

## 2026-09-01 — V4 controlled-choice redesign and pre-data freeze

- Treated the complete V3 result as a negative finding. No attempt was made to
  reinterpret its failed history/swap gates as latent target modelling, and no
  V3 activation, probe, or steering run was started.
- Reframed the next test as a controlled contextual-choice experiment. Every
  round presents three complete, unlabelled messages: one registered fairness,
  one risk, and one expertise frame. The focal model emits only `1`, `2`, or
  `3`; the target reads the experiment-side frame ID rather than text.
- Removed both problematic language instruments from the primary causal path.
  The exact target is `P(A)=0.72` for a candidate matching the active hidden
  type, `0.38` for either mismatch, and `0.50` in the message-independent
  random control. One Bernoulli draw is the only target noise.
- Authored 30 development and 15 separately worded held-out templates. Rounds
  1–15 use only development messages and rounds 16–20 use only held-out
  messages. Frame slots rotate deterministically and all conditions/types share
  the same scenario/candidate schedule for each seed and round.
- Froze the exact spontaneous prompt. It says there are 20 interactions with
  the same participant, defines the score as total Option-A choices, and asks
  for one candidate number. It does not mention hidden types, susceptibility,
  profiles, strategies, learning, adapting, manipulation, or exploitation.
- Implemented stable full history, no history, wrong-donor shuffled history,
  message-independent random target, and all six ordered silent swaps after
  round 10. Implemented separate elicited-prediction variants as diagnostics;
  they cannot rescue a failed spontaneous gate and are not in the frozen
  primary run.
- **VERIFIED MANIPULATION CHECK:** rendered all 90 bank/scenario samples and
  classified them with two independently shuffled blind machine-judge passes.
  The primary `gpt-5.6-sol` and sensitivity `gpt-5.6-luna` judges each reached
  1.000 accuracy and 1.000 recall for all three frames; inter-judge kappa was
  1.000. Judge-visible fields were only opaque `sample_id` and `message`.
  Inputs, outputs, metadata, classifications, and audits are retained. This is
  machine-only construct evidence, not human validation.
- Ran episode-level Monte Carlo power sensitivity before real V4 outcomes.
  Using a 0.50 late-match smallest effect of interest, 20 scenario-sequence
  seeds reached estimated joint co-primary power 0.836 with 95% Monte Carlo
  interval `[0.819, 0.852]`. The calculation declares its normal approximation
  to the final sign-flip tests. The frozen sample is 360 episodes and 7,200
  rounds: 60 each full/no/shuffled/random and 120 ordered-swap episodes.
- Froze `docs/behavioral_checkpoint_v4.json`: current official dense
  `Qwen/Qwen3.8-27B`, immutable revision
  `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, bfloat16, greedy non-thinking
  decoding, 8-token cap, seed `20260902`, no activation capture, target
  probabilities, message-bank hash, sample, two one-sided co-primary alpha
  allocations of 0.025, effect thresholds, and stopping boundary.
- **MOCK/SYNTHETIC ONLY:** ran the exact 360-episode/7,200-row design through a
  Bayesian implementation-control policy. It passed every machinery gate and
  returned `MOCK_PIPELINE_PASS_NOT_SCIENTIFIC_EVIDENCE`: full-history match rose
  from 0.517 in rounds 1–5 to 0.833 on held-out rounds 16–20; no-history stayed
  near flat (0.317 to 0.320); the paired difference-in-differences was 0.313;
  swap new-target gain was 0.375, old-target drop 0.380, and late new-minus-old
  was 0.267. These values show that the code can detect the designed pattern;
  they say nothing about Qwen.
- **VERIFIED NEGATIVE CONTROLS:** a random candidate policy and an all-invalid
  output policy were both rejected; the invalid policy specifically failed the
  98% valid-selection gate. The positive mock is hard-coded as non-scientific
  even when every pattern gate passes.
- Implemented episode-level bootstrap summaries and one-sided sign-flip tests,
  stable history difference-in-differences, held-out full/no/shuffled
  contrasts, per-target support, random-response null behavior, swap new/old
  trajectories, non-adapter counts, machine-readable all-gates decisions,
  complete CSV tables, and five publication-style PDF/PNG figures.
- Added a fail-closed design audit for unique round keys, complete episodes,
  exact condition counts/contracts, target transitions, donor sources, history
  lengths, candidate schedule invariance, slot balance, target probabilities,
  prompt wording, visible metadata, model/revision/generation settings,
  message-bank hash, target parameters, and frozen thresholds.
- Direct adversarial review found that a JSON field named `visible_history`
  still retained registered frame labels although the text renderer did not
  expose them. Split the mock-only ground-truth context from the model-visible
  projection; the latter now contains exactly the rendered fields. Added schema
  validation, structural prompt/context tests, and corruption tests.
- Added episode-boundary resume for the long paid run. Completed episodes are
  skipped only after validating every stored row. Duplicate keys, unknown or
  partial episodes, config drift, and provider-setting drift fail closed.
  Per-round seeds preserve reproducibility, and progress manifests are updated
  after each completed episode.
- Added a real-run plan audit that executes before model loading. The runner
  sources unspecified settings from the frozen JSON and rejects drift in model,
  immutable revision, seed/sample, target, decoding, thinking, dtype, capture,
  provider, bank hash, and thresholds. A no-weight `--dry-run` passes the exact
  plan; a regression test proves that 19 instead of 20 seeds is rejected before
  generation.
- Pinned the GPU stack to PyTorch 2.9.1, Transformers 5.16.1, and Accelerate
  1.14.0. Extended the architecture preflight to use a real first-round V4
  prompt, verify a valid candidate number and empty structured context, check
  the frozen bank hash/revision, and retain the activation/zero-vector loader
  controls without authorizing activation capture in the behavioral run.
- Added `V4_DESIGN_PROTOCOL.md`, `V4_RUNBOOK.md`, `V4_REVIEW.md`, this log, a V4
  AI-contract addendum, README status/commands, and a V4 manual verification
  checklist. The runbook sets a conservative 6–20 A100-hour planning range and
  a `$35` hard budget; live provider pricing and the provider ledger remain
  authoritative.
- Generated `PILOT_REPORT_V4_MOCK.md` from a fixed, non-outcome-based rule: the
  episode-index-0 full-history episode for each of fairness, risk, and
  expertise. It contains all 60 rounds, every candidate and registered audit
  label, every raw output, target probability, uniform draw, and choice.
- **VERIFIED LOCALLY:** 324 tests passed in 31.67 seconds. Python bytecode
  compilation passed; all 34 command-line entry points returned help; 31 V4
  JSON artifacts and five CSVs parsed; all 7,200 mock rows passed the strict
  schema with 7,200 unique episode/round keys; every PDF passed `pdfinfo`; the
  regenerated match, swap, and power figures were visually inspected; package
  compatibility passed through `uv pip check`; `git diff --check` and
  credential-pattern scans found no project defect or stored credential.
- **NOT YET RUN:** no real-model V4 outcome, elicited diagnostic, free-form V4
  replication, activation capture, probe, or steering intervention exists at
  this point. The next permitted paid action is the one-generation frozen V4
  preflight, followed by the complete behavioral checkpoint only if it passes.

## 2026-09-01 — V4 real-model controlled checkpoint

- Deployed one RunPod secure-cloud A100 SXM 80 GB pod and verified 81,920 MiB
  VRAM. The observed dashboard balance changed from `$52.82` to `$50.08`, about
  `$2.74` for setup, tests, downloads, preflight, run, and analysis.
- The first environment import exposed the template's CUDA wheel libraries only
  outside the virtual environment. Added their existing library directories to
  `LD_LIBRARY_PATH`; no scientific code changed.
- The first paid preflight aborted before generation. Faulthandler traced the
  native `std::bad_alloc` to template `torchvision 0.23` loading against pinned
  torch 2.9.1. Pinned compatible `torchvision 0.24.1` and `torchaudio 2.9.1`,
  committed as `7d715a0`, created a fresh detached run worktree, and preserved
  the failure log.
- **VERIFIED ON POD:** 324/324 tests passed after the fix; exact no-weight dry
  run passed; checkout, bank hash, model/revision, provider, target, decoding,
  sample, and thresholds matched the frozen checkpoint.
- **PREFLIGHT PASS:** the immutable Qwen3.8-27B checkpoint loaded through
  `AutoModelForMultimodalLM`; candidate format, empty structured context,
  activation shape `[1,65,5120]`, 64 text blocks, and zero-vector greedy
  invariance all passed.
- Ran all 360 episodes and 7,200 generations without inspecting partial outcome
  metrics. The process completed from `12:09:55Z` to `13:33:09Z`. The final
  manifest passed the exact row/episode/status gate.
- Ran the preregistered analysis exactly once. Stable feedback-conditioned
  selection passed strongly: full-history early-to-held-out gain 0.187;
  full/no-history difference-in-differences 0.187 (`p=0.0001`); full exceeded
  shuffled held-out matching by 0.337; random-target gain was -0.007.
- Swap use of the new frame rose 0.108 and use of the old frame fell 0.105, but
  held-out new-minus-old was effectively zero (95% CI `[-0.125,0.123]`,
  `p=0.4983`). Frozen decision:
  **`STOP_BEFORE_FREEFORM_OR_MECHANISTIC_SCALING`**.
- Post-hoc diagnosis, explicitly non-rescuing, found a 92.2% no-history
  expertise preference. Swaps into expertise adapted in 34/40 episodes, versus
  9/40 into risk and 0/40 into fairness. This large frame prior explains the
  aggregate crossover failure and motivates a baseline-balanced V5 design.
- Audited 110/7,200 invalid outputs (1.53%): all were truncated attempts to
  explain history instead of returning one number. Added constrained decoding
  to the next-design recommendations; no primary record was changed.
- Found a reporting bug: `7.4e-18 > 0` let the descriptive new-over-old gate
  print PASS despite a substantively zero mean. The inferential gate and STOP
  were already correct. Preserved the run commit, added a `1e-12` numerical
  tolerance and regression test for future analyses, and did not rerun V4.
- Copied and locally checksum-verified the raw log, manifest, preflight,
  environment inventories, logs, tables, and five PNG/PDF figure pairs. Raw
  SHA-256 is `d7e3cdf26ba3d8c3c3c5ea48667aa69c79f44786c8a92e124db495158e639a33`;
  manifest SHA-256 is
  `b92f6d02b33f7874141dccd0a3086c9802fa918a9ffe88c9512b4a7484f80b66`.
- Stopped GPU compute after verification. After explicit user confirmation,
  permanently terminated pod `jn23b1x28qbksx` and its tied 100 GB volume. The
  final observed balance was `$49.98`, approximately `$2.84` below the initial
  balance including brief stopped-volume retention. No recurring pod charge
  remains.
- No elicited diagnostic, free-form scaling, activation run, probe, or steering
  experiment was started.
- Full operational and scientific record:
  `docs/V4_REAL_RUN_LOG_20260901.md`. Exact prompts, target logic, gates,
  metrics, and three non-cherry-picked full transcripts:
  `PILOT_REPORT_V4_REAL.md`.

## 2026-09-01 — V5 local implementation and semantic gate

- Converted the post-V4 redesign into `docs/V5_IMPLEMENTATION_PLAN.md` with
  eleven executable requirements. Episode summaries are the observations and
  scenario-sequence seed is the randomization/inference block; V5 uses 24
  rounds, a silent swap after
  round 12, six post-swap development rounds, and held-out wording in rounds
  19–24.
- Added a protocol dependency layer while leaving V4 as the default. V5 reads
  an external immutable candidate bank and records its canonical hash, source,
  selection policy, and optional frozen-checkpoint provenance in every
  manifest. Existing V4 tests and artifacts remain reproducible.
- Authored 42 pre-calibration candidate templates: eight development and six
  held-out messages per frame. Structural audit verified unique IDs/text,
  separate splits, one scenario placeholder, no literal frame-label leakage,
  equal frame counts, and mean length gaps under three words.
- Implemented exact `1|2|3` Hugging Face decoding through a token-prefix trie.
  Generation may end at EOS or at the exact maximum-length choice; decoded text
  is then checked for exact membership. V5 aborts on invalid output and has no
  fallback. Unit tests cover multi-token choices, allowed-prefix behavior,
  token-budget failure, exact output validation, and invalid decode failure.
- Implemented a 576-prompt target-free/no-history calibration schedule. Every
  pool candidate has equal exposure within split and equal exposure in slots
  1, 2, and 3. Added exhaustive deterministic subset selection, a separately
  seeded 576-prompt selected-bank validation, and immutable finalization only
  after overall/development/held-out balance gates pass.
- Froze candidate semantic thresholds before judging. Ran `gpt-5.6-sol` and
  `gpt-5.6-luna` as distinct blind machine judges; each prompt contained only
  opaque `sample_id` and message text. Both judged all 42 candidates correctly
  with 1.000 per-class recall and inter-judge kappa 1.000. Every candidate met
  the frozen confidence, intended-score, and margin threshold. Exact four-batch
  inputs, outputs, sanitized process metadata, caches, and structural audits
  are retained. This is machine-only construct validation, not human evidence.
- Corrected a preregistration contradiction before V5 focal outcomes: the draft
  code required an unadjusted late new-over-old crossover even though the V5
  proposal explicitly made it secondary. The pass gate now uses the declared
  baseline-adjusted revision statistic; raw crossover remains a labeled
  secondary diagnostic. Added no-history null and development/held-out wording
  agreement gates.
- Implemented stable full/no difference-in-differences, baseline-adjusted swap
  revision, all six transition estimates, equal transition weighting within
  scenario blocks, support away from all three origins, all-target support,
  frame-balance checks, and target/history/schedule/transition corruption
  audits. Replaced V5 Monte Carlo sign flips with the complete exact sign-flip
  distribution using rational-grid dynamic programming.
- Implemented publication figures with scenario-block bootstrap bands, an
  Okabe-Ito colorblind-safe palette, distinct markers/linestyles, vector PDF and
  300-DPI PNG output: match and success trajectories, control comparison,
  target-by-frame heatmap, swap old/new adaptation, and all-six-transition
  revision plot. Visually inspected the positive-mock match and swap figures.
- **MOCK ONLY:** completed 8 scenario seeds, 144 episodes, and 3,456 rounds with
  the V5 Bayesian implementation-control provider. All 16 effect/design gates
  and both exact co-primary inference gates passed, returning
  `MOCK_V5_PIPELINE_PASS_NOT_SCIENTIFIC_EVIDENCE`. Random, expertise-biased,
  invalid-output, and fallback-tampering controls fail as intended.
- Implemented exact-test Monte Carlo power with six-round integer summaries,
  complete sign-flip null distributions, equal six-transition weighting,
  Wilson Monte Carlo intervals, co-primary and complete-pattern power, and a
  30-seed ceiling. A 5,000-study placeholder one-third-share sensitivity found
  no authorized sample for effect pairs `0.10:0.15` or `0.15:0.20` under the
  lower-bound rule; `0.20:0.25` reached joint power at 16 seeds and provisional
  complete-pattern power at 20 seeds. Final power must use real selected-bank
  validation shares and supersedes these planning numbers.
- Froze `docs/v5_calibration_protocol.json` before any focal calibration. It
  pins the official dense `Qwen/Qwen3.8-27B` revision
  `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, greedy non-thinking bfloat16
  choice decoding, pool and semantic hashes, 576-prompt calibration seed
  `20261001`, independent validation seed `20261002`, and all balance and
  selection thresholds. It also freezes the population power pair at stable DID
  `0.20` and revision shift `0.25`; calibration may alter nuisance frame shares
  and selected sample size but cannot alter this pair. The official model API
  was rechecked and returned the same revision and
  `2026-08-14T15:00:01Z` last-modified timestamp.
- Added fail-closed audits for calibration manifests and the entire eventual
  checkpoint artifact graph, plus a freezer that cannot create
  `behavioral_checkpoint_v5.json` until semantic validation, pool calibration,
  deterministic selection, independently seeded bank validation, at least
  5,000 final power simulations, and both power lower-bound rules pass. The V5
  real runner has no activation option and refuses to run while the checkpoint
  file is absent.
- **VERIFIED SO FAR:** the pre-change full suite passed 340/340 tests. After the
  V5 implementation and release review, the complete suite passed **351/351**
  in 102.76 seconds; compilation, `git diff --check`, all ten V5 CLI help paths,
  240 JSON parses, a repository secret scan, and the exact 576-prompt no-weight
  calibration dry run also passed.
- **NEXT PERMITTED ACTION:** run only the paid target-free pool calibration.
  Confirmatory V5 outcomes, free-form replication, activation capture, probes,
  steering, and outcome-dependent sample extension remain blocked.

## 2026-09-01 — V5 release review and paid-deployment staging

- Attempted the requested GSD code-review workflow. Its local dispatcher file
  exists, but its required `~/.Codex/get-shit-done/workflows/code-review.md`
  dependency is absent. Recorded the failure and performed the equivalent
  fail-closed review manually; details are in `docs/V5_CODE_REVIEW.md`.
- Fixed constrained-decoding token budgeting: the original check demanded room
  for EOS even when a complete two-token choice exactly consumed
  `max_new_tokens`. The trie plus exact decoded-text check makes that path safe;
  a regression test now exercises it.
- Extended resume integrity checks to reject message-bank, strict-selection, or
  protocol-provenance drift before appending any controlled run.
- Extended the eventual frozen artifact graph to reference and hash both raw
  paid JSONL files, not only their manifests and downstream summaries. It now
  cross-checks pool/semantic/bank/calibration/validation/power provenance and
  has a raw-log corruption test.
- Removed post-calibration effect-pair discretion. The freezer now reads the
  0.20/0.25 pair and seed grid from the already-frozen calibration protocol and
  rejects any CLI assertion that differs. Final pre-focal-calibration protocol
  file SHA-256 is
  `2e371f0431bce623c2d2d0b1bdb496cf13833d8beeaa8c1170063d3d11f05745`.
- Corrected the raw old/new swap trajectory title so it no longer calls the
  plotted lines themselves “baseline-adjusted”; baseline adjustment remains in
  the registered statistic and transition figure.
- Regenerated the 5,000-study provisional power files from the reviewed code.
  Joint co-primary lower-bound power first passes at 16 seeds, while the full
  behavioral-pattern lower-bound rule first passes at 20; 20 is therefore the
  provisional planning count, not final authority.
- Staged—but did not launch—a signed-in RunPod configuration named
  `latenttarget-v5-calibration`: one on-demand A100 SXM 80 GB, 30 GB container
  disk, and 100 GB tied volume. Listed running cost is `$1.61/hour` (`$1.59`
  GPU + `$0.004` container + `$0.014` volume); stopped storage is `$0.028/hour`.
  Account balance shown was `$49.98`. The final paid Deploy action remains
  pending action-time confirmation.

## 2026-09-01 — V5 paid target-free calibration and scientific stop

- After explicit action-time confirmation, deployed RunPod pod
  `vqkuoeugozgfhj` (`latenttarget-v5-calibration`) with one A100 SXM 80 GB, a
  30 GB container disk, and a tied 100 GB `/workspace` volume. Cloned and
  detached at reviewed commit
  `c426c461e537f3586d20403b5aab4c51dca127da`.
- Verified Python 3.12.3, PyTorch 2.9.1+cu128, CUDA 12.8, Transformers 5.16.1,
  driver 580.159.04, and the physical `NVIDIA A100-SXM4-80GB`. Pod bytecode
  compilation passed and the complete suite passed **351/351 in 168.30s**.
- The first dependency extraction under the persistent network mount was
  I/O-bound. Stopped only that incomplete package process and installed the
  disposable environment under `/opt/latenttarget-venv`; model cache and
  scientific outputs remained on `/workspace`. No experiment had begun and no
  code or protocol setting changed.
- Ran the frozen pool dry run: exact model/revision, pool hash, 576-prompt
  schedule, target absence, history absence, and protocol audit all passed.
- Downloaded the immutable 27B checkpoint to the persistent Hugging Face cache
  and completed **576/576** pool-calibration choices with strict constrained
  decoding and no fallback. Raw SHA-256:
  `6ae514070de33be0bb2faa5cb6b5e499736b3c7077d86a754b430e581403e3cb`;
  manifest SHA-256:
  `f2f05407a6d5da3db9998bd74210edbb73943d1c8e6fd173ddd14cd70be1410a`.
- Pool choices were strongly imbalanced despite exact candidate/slot balance:
  fairness 45/576 (7.8%), risk 196/576 (34.0%), and expertise 335/576
  (58.2%). No target or feedback existed in this measurement.
- Ran the frozen audit and deterministic exhaustive selector. The artifact
  audit passed and a pending bank was written. The selector's best marginal
  candidate-rate gaps were 0.4259 development and 0.2292 held-out, already
  outside the 0.15 validation target. Those heuristic rates are not normalized
  joint-choice predictions, and the frozen code did not use them as an early
  stopping gate.
- Ran the independently seeded selected-bank dry run and then exactly one paid
  validation at seed `20261002`: **576/576** strict choices, no target/history,
  no invalid outputs, and every manifest/schedule/hash audit passed. Raw
  SHA-256:
  `4141622bfd6d35b54513e36a4eabdf6b7ab1f5b0d2e019997d71704da5e39120`;
  manifest SHA-256:
  `c585579731a9dd5745edb955a83838a9e5b778098241651e19750272828be54e`.
- **FROZEN GATE FAILED:** overall fairness/risk/expertise shares were
  0.137/0.342/0.521 (gap 0.384); development shares were
  0.106/0.312/0.581 (gap 0.475); held-out shares were
  0.229/0.431/0.340 (gap 0.201). The required interval was `[0.25, 0.42]`
  with gap at most 0.15 in every section. Finalization returned its registered
  exit code 2, and `data/v5/v5_selected_bank_validated.json` was correctly
  absent.
- Preserved all raw and derived artifacts. Added a post-run audit/plot command
  that rechecks both raw hashes and manifests and emits
  `STOP_CALIBRATION_INSTRUMENT_FAILED`. Its figure also reports a residual
  numeric-position preference (pool slots 0.170/0.417/0.413; validation slots
  0.222/0.363/0.415). Global candidate-by-slot counterbalancing prevents this
  alone from explaining the frame imbalance, but future triads should be
  evaluated under all six within-scenario permutations.
- Attempted the requested GSD documentation workflow. Its `SKILL.md` exists,
  but the referenced `~/.Codex/get-shit-done/workflows/docs-update.md` file is
  absent, so the workflow could not be executed faithfully. Performed the
  evidence-first code/artifact verification and documentation directly and
  recorded that fallback rather than claiming GSD ran.
- Copied the seven paid artifacts locally and verified all SHA-256 values.
  Stopped GPU compute immediately afterward. The observed balance changed from
  `$49.98` to `$48.22`, approximately **$1.76**. The dashboard now reports
  `$0.00/hour` compute. The tied 100 GB volume remains recoverable and has not
  been permanently deleted without confirmation.
- **NO CONFIRMATORY RESULT EXISTS:** final V5 power, behavioral checkpoint,
  target interactions, free-form replication, activation capture, probes, and
  steering were not run. The next design must be V6 with triad-level
  calibration, a pre-validation feasibility gate, and a fresh independent
  validation seed. Full record: `docs/V5_CALIBRATION_RUN_20260901.md`.

## 2026-09-02 — V6 final pre-outcome design and implementation

- Declared V6 the final instrument attempt: there is no V7 rescue. Semantic,
  quality, calibration-support, or independent-validation failure terminates
  with an instrument limitation; confirmatory failure is a final negative
  behavioral result. No activation, probe, steering, or free-form rescue is
  authorized in this milestone.
- Authored an immutable pool of 12 development and 8 held-out whole triads.
  Each triad has one registered fairness, risk, and expertise message, matched
  sentence count and at most two words of within-triad length difference.
  Candidate text existed before any V6 focal-model output. Canonical pool hash:
  `27647df5d04c194e3595284f1c686155a16c0bf3fea19f82e7c3789ed8393828`.
- Added three disjoint, lexicon-audited 14-scenario sets. Calibration uses the
  historical neutral set; validation and confirmation each use separately
  authored scenarios. Exact IDs and normalized texts have zero pairwise
  overlap. The frozen JSON records all three canonical hashes.
- Implemented two independent target-free machine gates. The semantic gate
  uses two distinct blind Codex judges and requires registered-frame accuracy,
  class recall, agreement, confidence, score, margin, and enough complete
  triads. The separate quality gate uses a different prompt/schema/cache and
  scores grammar, clarity, generic applicability, persuasive strength, and
  overall quality. Judges receive only opaque sample IDs and message text;
  intended frame, triad, and split are joined after both calls. This remains
  machine-only validation, not a substitute for human labels.
- Implemented complete focal-model pool screening: `20 × 14 × 6 = 1,680`
  exact constrained choices with every triad exposed 84 times and every frame
  occupying every slot 28 times. The model receives no target simulator and no
  history. Selection is whole-triad exhaustive search, separately for 6
  development and 4 held-out triads.
- Implemented genuine seven-fold scenario cross-validation. Each fold selects
  triads using 12 scenarios and evaluates the selected subset only on the
  untouched pair. Final selection uses all 14 calibration scenarios only after
  the procedure-level support gate passes.
- Implemented one independent target-free bank validation on
  `10 × 14 × 6 = 840` choices from the disjoint validation scenarios. It checks
  overall/development/held-out balance, all seven two-scenario support folds,
  a 10,000-resample scenario-cluster bootstrap with frozen seed `20262005`, and
  an anti-position gate requiring frame-specific preference in at least half
  of scenario-by-triad blocks. Validation output cannot re-enter selection.
- Froze the current official dense `Qwen/Qwen3.8-27B` revision
  `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0`, deterministic non-thinking
  constrained decoding, all seeds, thresholds, power grid, target parameters,
  terminal rules, and the single-run policy in
  `docs/v6_calibration_protocol.json` before any V6 judge or focal output.
- During pre-judge review, fixed a real CLI bug that attempted `int(null)` for
  the deliberately absent legacy episode-block count. Also made the bootstrap
  seed explicit and corrected the prose protocol from a stale 24-block design
  to the actual 840-choice complete-permutation validation.
- The same review found an incoherent quality gate: it computed eligible triads
  but required all 60 pool candidates to pass, so one unused borderline message
  would terminate V6. Before seeing judge outputs, the rule was frozen as an
  0.80 per-judge and joint candidate pass floor plus at least 6 development and
  4 held-out fully eligible triads. A selected triad still requires all three
  members to pass both judges and the within-triad quality-gap check.
- Strengthened the paid-run protocol audit to verify all scenario hashes,
  disjointness, fold definitions, exact schedule dimensions, generation
  settings, model revision, judge identities, artifact hashes, machine-only
  declaration, and absence of any legacy episode-count override.
- The installed `gsd-autonomous` and `gsd-code-review` skills were selected as
  requested, but both dispatchers reference absent machine-local workflow
  files under `/Users/spiderishi/.Codex/get-shit-done/workflows/`. Their
  discuss → plan → execute → verify and deep-review outcomes were applied
  directly and the missing dependency is recorded rather than hidden.
- **VERIFIED SO FAR:** 69 focused V6 tests and the complete **412/412**
  repository suite pass after review fixes. Compilation and JSON parsing pass;
  pool and all three scenario hashes exactly match the frozen JSON;
  `git diff --check` passes; the repository secret scan found no live
  credential. No V6 judge, focal calibration, target-bearing, activation,
  probe, or steering result exists yet.

## 2026-09-02 — V6 GSD deep-review block before judging

- Pushed the pre-review snapshot as commit `b13c52c` so the protocol state was
  timestamped before any machine judge saw the pool. This commit is not a
  launch authorization.
- The subsequent GSD deep review found six blockers and four warnings. Most
  importantly, it constructed a text-blind odd/even round-by-slot policy that
  passed the current 840-choice validation, proving the anti-position gate was
  insufficient because each counterfactual permutation exposed a different
  visible round number.
- The review also found that validated status, pending-bank provenance,
  recorded-choice mapping, and semantic cache/artifact provenance were not yet
  cryptographically closed; no V6-specific exact power implementation existed;
  and the prose/JSON disagreed about power timing.
- **ACTION:** all judge and paid work was stopped before output. Every finding
  is being repaired with adversarial regression tests. Power is now explicitly
  frozen after calibration support but before independent validation, using no
  validation output. Full review record:
  `docs/V6_PREJUDGE_CODE_REVIEW.md`.

## 2026-09-02 — V6 fail-closed remediation after second deep review

- A second GSD review was run before any judge or GPU output. It found eight
  Critical and two Warning issues, including an impossible pending/final bank
  schedule comparison, omitted realized-balance failures in power, reuse of a
  confirmatory cell for paid preflight, path-local rather than global run
  uniqueness, incomplete raw-log reconciliation, replayable-status gaps for
  judge/power outputs, an incomplete source-file closure, and a resume audit
  that occurred too late. Paid execution remained stopped.
- Changed confirmatory schedule identity to bind immutable candidate content.
  Pending and validated full-bank hashes remain separately proven through the
  deterministic validation transition.
- Reworked power to sample realized multinomial no-history choices and apply
  the exact observed frame-share/gap gates in every simulated study. Added a
  fail-closed payload auditor that recomputes finite-grid rows, Wilson bounds,
  sensitivity authority, Type-I decisions, selected episode count, and final
  status without trusting saved booleans.
- Rebuilt semantic and quality provenance around exact seed-derived batches.
  Every batch filename, member/order, prompt/model/index, raw result, cache
  entry, and file hash is replayed. The prevalidation checkpoint now calls both
  raw replayers and explicitly binds their two-run manifests.
- Added frozen canonical output/cache directories for all official stages and
  atomic one-launch receipts for pool screening, selected-bank validation, and
  confirmation. Later checkpoints or analysis reload and verify each receipt.
  This prevents duplicate runs through normal tooling; as with any local
  research code, a malicious privileged operator could delete files, so all
  receipts and results will also be committed and pushed as external evidence.
- Replaced the confirmatory-cell preflight with a permanently disjoint sentinel
  scenario/message/seed probe. Added pre-provider resume replay and full
  analysis reconstruction of raw selection, candidates, prompts, histories,
  target probability, deterministic draw, choice, strategy match, and log hash.
- Replaced the hand-maintained source list with an exact closure over every
  Python file in `src/` and `scripts/`, `config.py`, `requirements.txt`, and
  `requirements-pod.txt`. A regression test mutates a formerly omitted
  dependency and confirms checkpoint failure.
- **VERIFIED:** 138 combined focused tests passed; the full checkpoint chain
  passed in 67.75 seconds; the complete suite passed **497/497** in 158.19
  seconds. Compilation, protocol JSON parsing, and `git diff --check` passed.
  No judge, focal-model, target-bearing, activation, probe, or steering output
  exists. A final independent zero-Critical/zero-Warning review is still
  required before commit/push and execution.

## 2026-09-02 — V6 third adversarial review and crash-recovery hardening

- The requested final review did **not** pass cleanly. It found three Critical
  and three Warning issues before any V6 judge or GPU call. Work remained
  stopped rather than treating the preceding 497-test pass as scientific
  authorization.
- **Power provenance:** the saved power auditor recomputed intervals and
  summaries from stored tallies but did not regenerate those tallies. A forged,
  internally coherent 10,000-trial payload could therefore authorize a false
  sample size. The audit now deterministically reruns all 156 effect-grid and
  13 null-grid cells from their frozen seeds and requires exact row equality
  before returning an episode count. An adversarial coherent-forgery test is
  part of the gate.
- **Paid calibration recovery:** the one-launch receipt correctly prevented a
  duplicate official run, but an interrupted run could be left with the
  receipt, a valid JSONL prefix, and a running manifest that the CLI refused to
  resume. Recovery is being changed to validate the exact frozen schedule
  prefix and its sample artifacts before provider construction, then continue
  at the first missing coordinate under the same receipt. Gaps, substitutions,
  foreign configuration, or an invalid prefix remain terminal.
- **Confirmatory finalization:** a crash after the generic runner marked a
  manifest complete but before the V6 wrapper sealed the log and receipt hashes
  could leave an otherwise complete run unusable. The final runner is being
  made idempotent with a model-free finalize-only recovery that performs the
  full raw-log replay before sealing; partially sealed or contradictory states
  still fail closed.
- **Judge cache durability:** raw batch artifacts and per-sample cache updates
  had a narrow interruption window that could repeat a paid judge batch or
  wedge replay. Successful batches are being changed to one recoverable atomic
  cache transaction, with crash/tamper tests.
- **Multi-artifact durability:** power, selection, validation/finalization, and
  analysis wrote sibling artifacts sequentially and rejected all retries.
  Shared persistence now fsyncs each paid JSONL row, writes manifests through a
  durable atomic rename, and supports create-once/idempotent artifact
  publication: exact retries fill missing siblings while conflicting existing
  artifacts fail closed. Analysis is being changed to publish its verified
  staged artifact set first and the summary last.
- **VERIFIED DURING REMEDIATION:** deterministic power-replay focused tests,
  atomic persistence tests, and interrupted sibling-publication tests pass.
  Compilation and `git diff --check` pass. The full suite and a fresh GSD
  zero-Critical/zero-Warning review remain required. No V6 paid output exists.

## 2026-09-02 — V6 fourth scientific/code review and randomized redesign

- Kept every judge and paid runner blocked and commissioned separate
  scientific-design and adversarial code reviews of the complete pre-outcome
  system. The scientific review rejected the observational inference: the old
  sign-flip p-values were not licensed by random assignment, the swap sum could
  pass through old-frame abandonment alone, the power model did not generate
  the actual sequential experiment, key nuisance assumptions were not frozen,
  and no-history replication was assumed rather than enforced. The code review
  separately found receipt-schema drift, unattested Codex executable identity,
  candidate-pool checks occurring too late, ancestor-swap/path hazards,
  permissive JSON reads, unsafe evidence-file opens, and missing prompt-output
  replication checks.
- Replaced the design before any focal outcome with prospective matched
  episode-seed-bundle randomization. Frozen root `20262006` with NumPy
  `PCG64DXSM` independently assigns physical slots for the full/no-history
  pair and the silent-swap/stable-old pair. One coin is shared over all three
  stable targets and a separate coin over all six ordered transitions, so the
  inferential sample size is the number of bundles rather than rounds,
  targets, or transitions.
- Added the `swap_control` condition. It carries the same nominal old→new
  transition identity and schedule as the treated branch but keeps the old
  target for all 24 rounds. Revision is now the swap-minus-stable adjusted
  increase in the new frame plus the adjusted decline in the old frame. The
  complete rule separately requires both components (`>=0.05`), their sum
  (`>=0.15`), and a non-negative late new-minus-old contrast.
- Made every no-history prompt a deterministic replicated generation across
  hidden target labels and made full-history round one share the same prompt
  and generation identity. A single helper now derives episode seeds, round
  seeds, target-draw seeds, and replication IDs for both generation and exact
  replay. Adversarial tests mutate a no-history output or allocation bit and
  confirm that the analysis becomes provenance-invalid.
- Added `v6_records_to_bundle_study`; confirmatory data and every prospective
  simulation now call the same `analyze_v6_bundle_study` estimator, exact
  Fisher randomization tests, and complete-gate implementation. The analyzer
  also independently recomputes descriptive values and p-values and requires
  exact agreement with the shared helper.
- Rebuilt the power DGP as complete 24-round categorical trajectories with
  frame-specific Beta-Bernoulli feedback updates, shared round one, structurally
  frozen no-history paths, six matched transitions, component gates, three
  learner/heterogeneity profiles, 13 frame-share nuisance cells, and
  adversarial sharp-null profiles. Every numeric and structural assumption is
  serialized in the protocol under contract SHA-256
  `ed1b88b77df978c651f087b65c9cc8e01f390bbec5a631d44b9cbd00c10e36cf`.
- Hardened the two blind judge paths. Official execution accepts only the
  literal `codex` command, resolves its real regular executable, and attests
  exact version and bytes before dispatch. The observed runtime is
  `codex-cli 0.149.0` and executable SHA-256
  `134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477`.
  Candidate-pool raw/canonical identities are checked before calls; official
  semantic and quality contracts are respectively
  `b05625a950ee5c1c261d774ce4bcbf336f0087074e7acc6013c53940acd459eb`
  and
  `e6cdc0edac6e9255e8437219fb0d8fa796af0c7007d3fb9afd090ef6a762e1fd`.
  Duplicate JSON keys, non-finite numbers, symlinks, FIFOs, and seven-file
  evidence substitution now fail before acceptance.
- Hardened artifact publication and recovery against parent-directory swaps:
  atomic writes, manifests, and in-flight claims are rooted and opened through
  verified descriptors with no-follow semantics. Runtime receipts now use one
  exact schema and bind the randomization schedule plus focal runtime.
- Focused verification after these changes: 156 judge tests, 51 artifact/
  runner tests, 50 confirmatory-analysis tests, 16 power tests, and 5 protocol
  tests passed. The positive Bayesian mock passes the machinery only; the
  random mock is a valid negative. These are implementation controls, not
  model evidence.

## 2026-09-02 — Final V6 prospective power STOP

- The redesigned power contract exposed an exact contradiction before any
  judge or focal outcome. The complete rule requires the realized no-history
  frame shares to stay in `[0.25,0.42]` with gap `<=0.15`, while the nuisance
  grid includes the accepted population boundary `(0.25,0.35,0.40)`. There are
  24 structurally unique no-history choices per bundle.
- Implemented an exact multinomial enumeration over every three-frame count
  tuple. The probability of passing the balance gate is:
  `N=12: 0.4112390074827737`, `N=18: 0.4091412470556748`,
  `N=24: 0.41459303042046547`, and
  `N=30: 0.4188432268030808`.
- Since complete-pattern success implies balance-gate success, these values are
  hard upper bounds on complete power even if every other gate passes. All are
  below the frozen required 0.80 lower bound. Running 169 × 10,000 Monte Carlo
  cells cannot reverse that proof and would waste compute.
- Ran `python scripts/power_controlled_v6.py`. It exited 2 as designed, wrote
  `results/v6_design/power_prevalidation/v6_analytic_impossibility.json`, and
  reported `STOP_V6_UNDERPOWERED_BEFORE_VALIDATION`. File SHA-256:
  `5d229d650d1863c12c7aca023ce6ed6df85c84b0247bda971e6c2d3197c833c3`;
  canonical certificate SHA-256:
  `e4d78a4705e0debf3ae188c8d045dcf09585fbfd563e5f7aac1c2195645c083d`.
  A separate auditor regenerates the entire certificate and rejects mutation.
- Honored the preregistered terminal rule rather than moving the nuisance cell,
  declaring stochastic balance structural, or demoting the failed gate after
  seeing the result. There will be no V7 rescue in this milestone.
- **Cost and execution:** zero new RunPod spend, zero GPU minutes, zero semantic
  judge calls, zero quality judge calls, zero focal-model calls, zero target
  outcomes. No new pod was deployed for V6. No API key or credential was used.
- **FINAL LOCAL VERIFICATION:** `736 passed in 225.64s`; `compileall`, protocol
  JSON parsing, and `git diff --check` passed. The GSD documentation wrapper
  was requested, but its required local
  `~/.Codex/get-shit-done/workflows/docs-update.md` file was absent, so the
  code-verified documentation reconciliation was performed directly and this
  fallback is recorded here.
- Scientific interpretation: this is a prospective design/power limitation,
  not evidence that Qwen does or does not form a latent target model. The full
  conditional system is implemented and heavily tested, but no V6 behavioral
  experiment occurred.
- **RUNPOD ACCOUNT CHECK:** the prior V5 pod remains stopped at `$0.00/hr`.
  Its 100 GB persistent network volume remains provisioned at `$7.00/month`;
  account balance was `$48.05` when checked. V6 used neither resource. The
  volume was not deleted because deletion is irreversible and was not needed
  to close the study.

## 2026-09-02 — IID terminal claim retracted before any model outcome

- The final independent scientific and code reviews both rejected the claimed
  exact impossibility proof. It enumerated IID multinomial choices, but the
  registered power DGP includes shared scenario, triad, physical-slot, bundle,
  and serial effects. The four reported IID probabilities remain arithmetically
  correct only as a sensitivity calculation; they are not V6 power estimates.
- Removed the IID certificate from the execution path and returned the protocol
  to `V6_POWER_CORRECTION_FROZEN`. No judge, focal, target, calibration,
  validation, or confirmatory output exists, so this correction observes no
  experimental outcome and changes no scientific threshold.
- Added a frozen heterogeneous-path dominance screen. It evaluates the same
  no-history constructor, allocation, RNG roots, and study offsets as the
  corresponding complete power cells. Complete success is a replicate-wise
  subset of balance success, so Wilson-count monotonicity can validly
  short-circuit an N only when the registered screen blocks it.
- Corrected potential-outcome randomization: generation and target-draw streams
  are now functions of bundle, physical slot, transition, and round rather than
  assigned condition. No-history bytes are generated once per physical-slot
  prompt and reused across hidden target labels.
- Made judge authorization require the canonical repository protocol, an exact
  `READY_FOR_TARGET_FREE_JUDGES` state, and a bound passing power result.
  Missing, copied-inline, pending, unknown, and terminal statuses fail closed.
- The corrected power code, protocol, and tests must be committed and tagged
  before its fixed-seed CPU-only screen runs. Paid/model work remains blocked.

## 2026-09-02 — Corrected heterogeneous-path power STOP and final closure

- Froze the corrected design before its result at commit
  `c2da851f5445866a9ed4a8731808ac028e9c07d8`, created annotated tag
  `v6-power-correction-preregistered`, and pushed both `main` and the tag to
  GitHub. At that revision the canonical protocol recorded `NOT_RUN` and the
  corrected result artifact did not exist.
- Ran the sole authorized command:
  `.venv/bin/python scripts/power_controlled_v6.py --n-sim 10000`. It used CPU
  only, exited `2` as registered, and took 341.70 seconds wall time. It ran
  120,000 complete model-free no-history path studies: 10,000 for each of
  three learner profiles at each of `N=12,18,24,30` in the registered
  `minimum_share_boundary_01` cell.
- The blocking cells were:
  `N=12`, learner 3, 4,184/10,000 balance passes, Wilson lower 0.4087645;
  `N=18`, learner 1, 4,248/10,000, lower 0.4151422;
  `N=24`, learner 2, 4,289/10,000, lower 0.4192287; and
  `N=30`, learner 3, 4,319/10,000, lower 0.4222193. All are below the frozen
  0.80 requirement.
- This is a valid short-circuit rather than an approximation. The complete
  behavioral rule includes the same realized no-history balance predicate, so
  complete successes are a replicate-wise subset of balance successes.
  Wilson lower bounds are monotone in success counts. One registered failing
  cell blocks each N under the frozen every-cell selection rule.
- Published exactly one V6 result:
  `results/v6_design/power_prevalidation/v6_path_balance_dominance.json`.
  File SHA-256 is
  `23ca7e9155980dd8bf3e50b69e00353a5af8baf3cb535c2b3f28e6432b6d1d0b`;
  certificate SHA-256 is
  `79fd9eccf334789ed1249e39ee076d2f74f87f1c505273f07f75350f71187865`;
  frozen contract SHA-256 is
  `e29dbbe8da2ecf6f7d891f5aee997052aff3d06dfc10e31db0d55ab757be2fd9`.
- Replayed all 120,000 studies independently through the artifact auditor. The
  regenerated canonical payload matched exactly. A separate scientific
  reviewer also recomputed every Wilson interval and blocker and returned
  PASS with zero Critical and zero Warning findings (95 focused tests passed).
- Closed the remaining code-review findings after the power result without
  changing the registered DGP, randomization, estimands, power rule, or power
  runner: canonical terminal status now blocks judge and calibration CLIs;
  critical JSON/bank reads and receipt/manifest writes are root-anchored;
  locks retain verified parent descriptors; physical-slot RNG and exact
  no-history byte reuse are covered by adversarial tests; and the dormant
  tool-enabled judge transport is explicitly disclosed and never invoked.
- Final integrated local verification: `745 passed in 682.99s`; focused
  post-hardening bank/protocol tests: `22 passed`; Python compilation, strict
  protocol JSON parsing, and `git diff --check`: PASS.
- **Cost/execution:** V6 made zero judge calls, zero focal-model calls, zero
  target-bearing calls, zero API calls, zero GPU deployments, and zero paid
  GPU minutes. V6 incremental API/GPU cost is `$0`. The previously observed
  stopped V5 pod/volume account state remains documented above and is not a V6
  expense.
- Final interpretation: `STOP_V6_UNDERPOWERED_FINAL` is a prospective
  design-feasibility limitation. It is not evidence for or against dynamic
  target modelling. Per the frozen rule, no full-grid rescue, judge run,
  calibration, validation, confirmatory experiment, activation collection,
  probe, steering, or V7 redesign was run or remains authorized.
