# Partner state study design work log

7 September 2026. Repository HEAD when this work finished: `a61ddfde6aa3ed133e8cf36b10dbe3fcf4fa059e`.

## Scope

The user asked to continue the earlier experimental design and supplied the note proposing participant binding, transfer, selective causal intervention and a later silent update test. I read that attachment in full and treated it as the research direction, not as evidence that any proposed test had already succeeded.

The repository already contained uncommitted baseline and history diagnostic work, along with two unfinished partner study drafts. Those unrelated changes were preserved. This turn completed the design documentation, hardened its local checker, added tests and linked the proposal from the local README. It did not run paid compute, call a focal model or judge, collect activations, label messages, alter old result files, edit Google Docs, commit, or push.

## Completed artifacts

- [Study design](PARTNER_STATE_STUDY_DESIGN_20260907.md): the question, limits of each claim, exact target logic, independent unit, controls, estimands, provisional inference, missing outputs, sample planning, proposed causal and update stages, and stopping conditions.
- [Machine readable draft](partner_state_study_20260907.json): 24 calls per future bundle, all dispatch permissions false, no selected model or confirmation N, unfinished human validation, and unchanged historical gates.
- [Three illustrative prompt bundles](PARTNER_STATE_EXAMPLE_PROMPTS_20260907.md): 24 simulator records per history, eleven complete user requests, exact system prompts, analyst frame labels, target probabilities and random draws. These are constructed examples, not focal model transcripts.
- [Offline checker](../scripts/check_partner_state_design.py): mathematical contrasts and bounds, example rendering, parser checks and a read only command line audit. It does not import a provider, read credentials or write experiment files.
- [Tests](../tests/test_partner_state_design.py): contrast invariance, type assignments, candidate permutations, invalid data, exact rendering, metadata isolation, separated branches and output parsing.
- [Saved local check report](partner_state_design_checks_20260907.json).
- [Proposed GSD source manifest](partner_state_gsd_ingest.yaml), pending the required discovery approval.

## Decisions and scientific review

1. Kept the claim narrow. A successful identity interaction shows that behaviour uses information associated with a recipient. It cannot by itself distinguish a hidden type belief from a participant specific reward table.
2. Added an exact equivalence test. Under the declared additive simulator, `q_f = 0.38 + 0.34 b_f` gives the same composite probabilities as a belief over types. A feature reward learner is therefore an essential alternative, not something to omit from the baseline set.
3. Specified supplied histories rather than claiming spontaneous exploration. This is a new task and prompt. Earlier failed revision and validity gates remain failed.
4. Defined the four request identity contrast. Reassigning IDs in a history also reassigns the analyst ground truth. It is not a real target swap or a corrupted history control.
5. Kept forecast requests on separate branches. They cannot enter later histories or alter the choice branch through conversational memory.
6. Declared compositional target behaviour as a new assumption. Human semantic validation, plausible messages and a production stimulus bank are still missing. The saved three canonical cases are not a randomization or leakage validation of that future bank.
7. Added strict missing output handling. No digit extraction from prose, no random choice fallback, and no semantic retry. Invalid selections produce conservative contrast bounds. JSON forecasts reject duplicate keys, booleans, nonfinite values and unexpected fields.
8. Distinguished the no history two recipient score from the four request score. Random response controls use independent pseudo labels for scoring; their actual target probability remains 0.5.
9. Found and documented a power planning issue before sample selection. A continuation rule requiring an observed mean at least 0.10 cannot generally have 80% continuation probability when the true mean is exactly 0.10. The future screen must report significance against zero separately from the complete continuation decision.
10. Kept causal work locked. Prefix capture, matched donors, selectivity, wrong participant and random controls, ablation/restoration, cache handling and later updating are proposals. They require their own validation, power analysis, registration and explicit resolution of the old AI contract.

## Verification actually run

### Initial consistency check

The unfinished checker ran successfully before edits. It checked 72 mathematical cases: six ordered type pairs, two candidate banks and six slot permutations. It also checked 36 rendered requests from three illustrative histories. This established only those limited invariants, not run readiness or scientific power.

### First new test run and repair

Command: `.venv/bin/python -m pytest -q tests/test_partner_state_design.py`.

Result: **64 passed, 1 failed**. The failing exact reproduction test found a trailing newline difference between the generated Markdown and the saved artifact. The renderer was changed to end with exactly one newline. The test was retained unchanged; the mismatch was not ignored.

### Regression runs after repair

The new design tests plus the baseline and history diagnostic suites passed: **114 tests in 7.22 seconds**.

The expanded local regression command was:

```bash
.venv/bin/python -m pytest -q \
  tests/test_partner_state_design.py \
  tests/test_choice_baselines.py \
  tests/test_history_diagnostic.py \
  tests/test_controlled_target.py \
  tests/test_controlled_focal_agent.py \
  tests/test_controlled_analysis.py \
  tests/test_controlled_experiment.py \
  tests/test_checkpoint_gate.py
```

Result: **166 passed in 30.96 seconds**, with no warnings reported in that test output. This was a selected relevant regression suite, not the entire repository test suite. No focal models or paid services were invoked.

The final checker reports `DESIGN_CONSISTENCY_CHECKS_PASS_NOT_A_SCIENTIFIC_GO`, 72 mathematical cases, 36 example requests, three histories of 24 records each, and zero model or paid calls. It explicitly reports that participant feature reward can pass and that power has not been estimated.

`git diff --check` passed. A tracked file comparison confirmed no changes to existing `src/` files, `docs/AI_SPEC.md`, `docs/V4_DESIGN_PROTOCOL.md`, `docs/behavioral_checkpoint_v4.json`, or tracked V4 results. The preexisting untracked source files and result directories were not altered in this turn. A text scan found no em dashes or en dashes in the newly authored design, example prompts, checker, tests or machine readable plan.

## Skills and GSD status

The experimental design skill informed the use of paired requests, complete history bundles as the independent unit, blocked allocation and information boundaries. The statistical power skill prompted explicit treatment of joint decision power, missing outputs, control precision and the threshold problem. The interpretability skill informed prefix capture, matched interventions and token/cache cautions; no framework was installed and no hooks were run.

The restored GSD ingestion workflow and its required references were read completely. Its initialization command ran and confirmed an existing Git repository with no `.planning/` project. The import workflow requires the user to see and approve a source list before classification or roadmap generation. It has no automatic bypass for that gate. The import therefore stopped before classification, with no `.planning/` files or GSD commit created. The research design was completed independently in `docs/`; it is not presented as a completed numbered GSD phase.

The six proposed sources are:

1. `README.md`
2. `docs/AI_SPEC.md`
3. `docs/V4_DESIGN_PROTOCOL.md`
4. `docs/BASELINE_COMPARISON_FINDINGS_20260907.md`
5. `docs/HISTORY_DIAGNOSTIC_FINDINGS_20260907.md`
6. `docs/PARTNER_STATE_STUDY_DESIGN_20260907.md`

All six were read. The last is classified as a proposed document, not a specification that overrides the older frozen contracts. Any contradiction involving a locked decision must be surfaced during future ingestion, not resolved by silently replacing an old gate.

GSD still reports missing agents because the pinned presence checker does not recognize existing Codex TOML agent files, as established in the [repair log](GSD_SUPPORT_REPAIR_20260907.md). That warning was not suppressed. This turn did not test agent dispatch.

## Source verification

Primary publication pages for Feng and Steinhardt, Makelov and colleagues, Wu and colleagues, and Bortoletto and colleagues were opened and checked. The study design cites them next to the limited methodological claims they support. The literature was used for design context, not to claim novelty, guarantee a positive result, or assert that Neel Nanda would accept the project. No current model release or pricing claim was made.

## Artifact hashes at handoff

SHA256 values allow this design snapshot to be distinguished from a future approved protocol. This is not a public preregistration.

| Artifact | SHA256 |
| --- | --- |
| Machine readable plan | `ef68ae00ea8421bb21e99ef2901af0a69365f3c07adda0d3f8229969566a6dda` |
| Offline checker | `e2a45a0fb624c76494153b20e8e02e7da3510354011a3d4465549e5a13e58aa4` |
| New tests | `b188e8944232bc979acb4d456dceb1961a35e00e10ff661cb985e96d85ada5d6` |
| Study design | `d8d447200864005943e92d5e8897b50a406177dd95c000e0ab4e50518d6aabb4` |
| Example prompts | `aec1f54435d4752275af74dc732906cf56d4de63052df00db3490295b1e86226` |
| Saved check report | `fc1fd0feda55260e568eca9d17246ccb294da0e0247fbc33e5fe849c7d3480dc` |
| Proposed GSD manifest | `93422ff40a6daf7090228b3f2f8ac8b0b900a23a8a4cfc5361d888427243a030` |

## Problems and exact next step

The design is reviewable, not runnable. The next technical task is an offline production allocation and baseline/power screen with complete bundle resampling. That task must validate the planned statistics and control precision before selecting a sample size or requesting a tiny pilot budget. It must retain semantic and feature based reward learning as legitimate alternative explanations.

Human semantic validation, current model selection, production bank freezing, an actual three bundle pilot, budget approval and any activation experiment remain unfinished. A future user approval of the design or GSD source list does not by itself authorize model calls or remove these scientific conditions.
