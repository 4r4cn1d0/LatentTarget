# V6 pre-judge code review

Date: 2026-09-02  
Reviewed snapshot: `b13c52c`, followed by the uncommitted remediation snapshot  
Status: **BLOCKED pending one final clean re-review**

No semantic judge, quality judge, focal calibration, or paid V6 output had been
generated when this review was performed. Commit `b13c52c` is a transparent
pre-review snapshot, not an authorization to run the experiment.

The installed `gsd-code-review` dispatcher referenced an absent local workflow
file, so its deep-review outcome was run directly with the GSD code-reviewer
agent. The reviewer ran 70 focused V6 tests and the complete 412-test suite,
then performed adversarial cross-file inspection.

## Blocking findings

1. **Round-by-slot false positive.** Counterfactual slot permutations exposed
   different visible round numbers. A text-blind policy choosing slot 1 on odd
   rounds and slot 2 on even rounds reproduced a full validation pass, including
   the existing anti-position gate.
2. **Fabricable validated status.** Confirmatory bank loading trusted the
   `selected_bank_validated` status string without cryptographic evidence of the
   independent validation transition.
3. **Editable pending bank.** Validation accepted an arbitrary pending bank and
   did not prove its selected objects exactly matched the source pool, raw
   calibration outputs, and deterministic selection report.
4. **Recorded-choice reconciliation gap.** Calibration audit did not derive
   selected slot/frame/candidate from raw model output and a regenerated frozen
   schedule.
5. **Judge cache/artifact binding gap.** Semantic cache values and independently
   self-consistent batch artifacts were not required to be the same outputs.
6. **Missing V6 power implementation.** The only exact blocked power core used
   V5 thresholds, while the V6 JSON and Markdown also disagreed about whether
   power was frozen before or after independent validation.

During remediation, an additional power inconsistency was found: the draft
made the observed point-estimate gates equal to the simulated population
effects, which caps decision power near one half. Before any output, V6 restored
observed gates of 0.10/0.15 while retaining population planning alternatives of
0.20/0.25.

## Warnings treated as required fixes

1. Freeze and enforce judge models, seeds, batch sizes, rubric/prompt versions,
   and hashes before any call.
2. Use the canonical full V6 bank audit in semantic validation rather than a
   hard-coded structural-pass flag.
3. Never include raw semantic-judge stderr in raised errors.
4. Pin the confirmatory scenario set, scheduler, and exact generated schedule in
   the checkpoint and resume audit.

## Remediation gate

Judging and paid work remain prohibited until all items above have adversarial
regression tests, the full suite passes, a second deep review reports no
Critical/Warning issue, and the corrected pre-judge commit is pushed. The
round-by-slot reproducer is a mandatory regression test, not merely a prose
warning.

## Second deep-review findings and remediation

After the first six blockers were repaired, a second independent GSD review
deliberately re-opened the entire artifact chain. It reported eight Critical
and two Warning findings; no judge or GPU call had occurred. All ten were
treated as blockers:

1. The prevalidation schedule included the pending bank's full hash, while the
   runtime regenerated it from the finalized bank. The schedule now binds only
   immutable candidate content; the two checkpoints separately prove the exact
   pending and validated full-bank transitions.
2. Power omitted random failure of the observed no-history balance gate. It now
   simulates realized multinomial frame counts and applies the exact final
   balance bounds inside every complete-pattern trial.
3. The paid preflight reused the first official confirmatory cell. It now uses
   a permanently disjoint sentinel scenario, messages, split, and seed and
   proves no overlap with any official schedule coordinate.
4. Alternate output directories allowed duplicate nominally official runs.
   Judge, power, pool, validation, and confirmatory commands now enforce frozen
   repository-relative destinations. Pool, validation, and confirmatory runs
   additionally create atomic one-launch receipts that are replayed by later
   checkpoints/analysis.
5. Confirmatory analysis did not fully re-derive logged outcomes. It now
   validates every record, regenerates candidates and prompts, derives the
   selection from raw `1|2|3` output, regenerates deterministic target
   probabilities/draws/choices, verifies histories, and binds the completed
   JSONL hash and reconstructed-record hash to the manifest.
6. Semantic, quality, and power pass fields were still hand-editable. Both
   judge gates now rebuild the exact frozen batch plan and replay every raw
   batch plus cache. The checkpoint calls those replayers. Power stores the
   complete finite-grid aggregate rows and its checkpoint audit recomputes
   intervals, summaries, Type-I decisions, selected sample size, and status.
7. The hand-written source list omitted transitive imports. Both checkpoints
   now hash every Python file under `src/` and `scripts/`, `config.py`, and both
   dependency requirement files, with an exact file-set audit.
8. Judge seeds and batch sizes did not determine the accepted artifact
   partition. Artifact filenames, batch membership/order, model, prompt,
   batch index, and cache order are now regenerated from the frozen contract.
9. Resume could consume more paid compute before detecting a corrupted prior
   log. The runner now replays all completed records against the frozen schedule
   before constructing the provider.
10. Invalid confirmatory input exited zero. The analysis CLI now exits nonzero
    for invalid provenance/input while retaining zero for a valid negative
    scientific result.

The integrated remediation suite passed 138 focused tests, the full checkpoint
replay passed, and the complete repository suite passed **497/497** in 158.19
seconds. Compilation, frozen-JSON parsing, and `git diff --check` also passed.
The final prerequisite remains a fresh independent review reporting zero
Critical and zero Warning findings, followed by a pushed pre-judge commit.

## Third deep-review findings (execution remains blocked)

The requested fresh review found three Critical and three Warning issues. This
is a useful failure of the gate: no judge or GPU call had started.

1. Stored power tallies were only checked for internal coherence; they were not
   regenerated from frozen random seeds. A fabricated coherent payload could
   select an unauthorized sample size.
2. The one-launch pool/validation receipt could strand an interrupted paid run:
   the same run could neither resume nor safely start over.
3. A confirmatory crash between generic completion and V6 hash sealing could
   leave a complete log with an unsealed manifest that no path could recover.
4. Judge batch artifacts were durable before all per-sample cache records,
   allowing either duplicate paid calls or a wedged partial cache.
5. Selection, power, and finalization published multiple files sequentially and
   rejected exact retries, so a crash between siblings could make the frozen
   pipeline unusable.
6. Analysis wrote its summary before every table/figure, so an interruption
   could leave a summary that appeared to certify stale or incomplete outputs.

All six are treated as release blockers. Remediation adds deterministic replay
of all 169 power cells, exact-prefix paid-run resume, finalize-only confirmatory
recovery, atomic/recoverable judge batches, idempotent create-once sibling
publication, and summary-last staged analysis. Authorization still requires a
new full-suite pass and another independent adversarial review with zero
Critical and zero Warning findings.

## Fourth scientific-design and code-review findings

The next review again refused authorization before any judge or GPU output. Its
scientific review found four Critical and two Warning issues:

1. The co-primary sign-flip tests had no prospective random assignment to
   license their null distribution.
2. The swap revision sum could pass through old-frame abandonment without
   increased use of the new frame and lacked a matched stable-old trajectory.
3. The power generator sampled aggregate windows rather than complete adaptive
   round-by-round feedback paths.
4. Important power nuisance parameters were not frozen in the protocol.
5. No-history output identity was assumed rather than enforced.
6. The machine-only semantic validation did not justify claims beyond the
   registered frames and frozen scenarios.

The concurrent code review found four Critical and four Warning issues:

1. The launch-receipt reader rejected the writer's own runtime-bound schema.
2. The exact Codex executable target/version/bytes were not attested.
3. Candidate-pool identity could be checked after a judge dispatch.
4. Root-relative artifact protection did not fully cover ancestor swaps.
5. No-history and shared round-one generations were not byte-identical by
   construction.
6. Power omitted the shared round-one constraint.
7. Some provenance JSON reads accepted duplicate keys/non-finite values.
8. Seven-file judge replay opened evidence paths in a way that could follow a
   symlink or block on a FIFO.

## Fourth-review remediation

- Added prospective bundle randomization with frozen `PCG64DXSM` root
  `20262006`; one coin assigns all three stable trajectories and an independent
  coin assigns all six swap/stable-old transition trajectories.
- Added stable-old counterfactual episodes and separately required adjusted
  new-frame gain, adjusted old-frame drop, their revision sum, and late
  crossover.
- Rebuilt power as sequential 24-round categorical/Beta-Bernoulli studies and
  froze every allocation, DGP, heterogeneity, nuisance, null, estimand,
  inference, and gate field under contract hash
  `ed1b88b77df978c651f087b65c9cc8e01f390bbec5a631d44b9cbd00c10e36cf`.
- Made the confirmatory adapter call the identical shared analysis helper used
  by power and require exact agreement with independently constructed
  descriptive estimates.
- Shared deterministic prompt/generation identities across every no-history
  target replicate and full/no-history round one; added direct corruption
  tests.
- Unified the launch receipt schema and bound focal runtime plus allocation
  schedule. Root-anchored descriptor/no-follow operations now protect atomic
  files, manifests, and in-flight claims.
- Froze and attested literal Codex command, resolved executable bytes, exact
  version, candidate raw/canonical identity, and complete official judge
  contracts before dispatch. Strict JSON and regular-file descriptor reads now
  cover the full evidence graph.

## Prospective terminal power finding

The corrected power design itself produced a final blocker before any model
outcome. At nuisance population shares `(0.25,0.35,0.40)`, exact multinomial
enumeration gives realized balance-gate pass probabilities from 0.409141 to
0.418843 across the entire registered N grid. Complete success implies this
gate, so its required 0.80 power lower bound is impossible. The replayable
certificate is
`results/v6_design/power_prevalidation/v6_analytic_impossibility.json`.

The official power command exited 2 and no sample size was authorized. Per the
frozen terminal rule, no gate/nuisance redesign, judge call, focal calibration,
GPU deployment, validation, or confirmatory run followed. The final integrated
suite passed **736/736** in 225.64 seconds; compilation, protocol JSON parsing,
and `git diff --check` also passed. A final read-only code review and independent
scientific review are now running solely to audit this terminal closeout—not to
reauthorize execution.

## Final review rejection and correction gate

The final reviews rejected the closeout before commit. Most importantly, the
IID multinomial certificate did not represent the registered heterogeneous,
correlated path DGP. The terminal claim and artifact were withdrawn; V6 is
unresolved pending a corrected fixed-seed path simulation.

The code review also found that arbitrary/missing protocol status could bypass
judge blocking, generation RNG was not consistently attached to physical
randomized slots, replicated no-history prompts reran inference instead of
reusing bytes, the tool-enabled judge transport was unsuitable for untrusted
candidate text, and several dormant artifact paths still made stronger TOCTOU
claims than their implementation justified. These remain release blockers.

This correction revision freezes the actual-DGP dominance screen and repairs
canonical authorization, physical-slot RNG derivation, and no-history byte
reuse before any power output. No judge/model execution is authorized. A final
status requires the corrected power result plus remediation and re-review of
the remaining transport and artifact findings.
