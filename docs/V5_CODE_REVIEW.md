# V5 calibration-ready code review

Date: 2026-09-01
Scope: all V5 source, scripts, tests, frozen inputs, generated mock/power
artifacts, and V4 compatibility changes present before paid focal calibration.

The requested GSD code-review dispatcher could not run because its referenced
workflow file, `~/.Codex/get-shit-done/workflows/code-review.md`, is absent on
this machine. The review below applies the same release gate manually. This is
not recorded as a GSD pass.

## Resolved findings

1. **High — raw calibration provenance was incomplete.** The future freezer
   referenced manifests and summaries but not the paid JSONL logs used for bank
   selection and validation. The checkpoint now hashes both raw logs and
   cross-checks them against manifests, selection/validation reports, the final
   bank, semantic gate, and power source. A corruption test changes a raw log
   and confirms the audit fails.
2. **High (scientific) — effect-pair choice remained open.** The freezer accepted
   a CLI-selected power pair after calibration. The population smallest-effect
   pair is now frozen before focal calibration at stable DID `0.20` and revision
   shift `0.25`; the freezer rejects drift. Selected-bank shares may change only
   the required seed count.
3. **Medium — controlled-run resume did not verify the bank.** A resume could
   have used the same task version/config/provider with a different protocol
   bank. Resume now checks bank SHA-256, strict selection policy, and frozen
   provenance before reading or appending records.
4. **Medium — constrained-choice token budget was too strict.** The provider
   required one extra token for EOS, rejecting a valid two-token choice under a
   two-token budget. A complete trie path may now stop at the token limit; exact
   decoded-text validation still rejects any non-choice output.
5. **Low — one figure title overstated its transform.** The old/new trajectory
   was raw but titled baseline-adjusted. The title now describes strategy
   revision; baseline-adjusted quantities remain in the registered summary and
   transition plot.

## Verification

- Full suite: **351 passed** in 102.76 seconds.
- Focused post-fix tests: 37 passed, then 31 passed during review iterations.
- Python compilation: passed for `config.py`, `src/`, `scripts/`, and `tests/`.
- All ten new V5 command-line entry points return successful `--help` output.
- Frozen 576-prompt calibration dry run: passed without loading weights or
  generating outcomes.
- JSON integrity: 240 files parsed successfully.
- `git diff --check`: passed.
- Repository secret scan: no RunPod key or API-key assignment found.
- Provisional exact power artifact regenerated from reviewed code: 5,000
  studies per design cell; frozen 0.20/0.25 pair requires 20 seeds under the
  stricter complete-pattern lower-bound rule with placeholder balanced shares.

## Residual risks and hard stops

- Semantic validity is supported by two blind machine judges, not humans.
- The environment studies choices among controlled, pre-authored message
  frames. A behavioral pass would show feedback-conditioned target-specific
  policy revision, not by itself an explicit internal representation.
- The real focal model may retain a frame prior or fail selected-bank balance.
  Either failure stops the design; thresholds must not be relaxed.
- Final power cannot be frozen until separately seeded selected-bank validation
  supplies real nuisance frame shares.
- No V5 target-bearing outcome, activation, probe, steering result, or
  free-form replication exists. The only next permitted paid action is the
  target-free pool calibration.
