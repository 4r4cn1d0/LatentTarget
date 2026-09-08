# Completing the fixed diagnostic bank

The user requested: "run the experiments" after the 60 request pilot had
completed. The next bounded action is to collect the remaining 33 bundles from
the same fixed bank. This adds 660 choices to the original 60, giving 720
choices from all 36 existing evaluation bundles. It does not repeat the pilot,
draw new histories, choose favourable cases, change the model or introduce
activation experiments.

## Before additional model calls

The full repository suite passed 1,053 tests in 601.07 seconds. The additional
history evidence regression also passed separately after suite collection.

The complete fixed history bank audit then verified all original input hashes
and all 36 bundles. Of 72 participants, 46 histories uniquely favoured the true
type, 16 tied while including the true type and 10 favoured a wrong type. This
helps explain why the first three bundles cannot be used as a population verdict.
All participants and histories remain in the data. The audit made zero new
model calls and zero new history draws.

The experimental design skill guided retention of the full fixed allocation and
the correct unit of analysis. Thirty six bundles are the units, not 720
independent samples. This extension was chosen after seeing pilot outcomes, so
the combined result is descriptive followup work, not an untouched confirmation
set or a retrospective pass of a scientific gate.

The model, revision, system and user prompts, candidate orders, simulator,
history draws and per request seeds are unchanged. New request order follows the
original ledger with the 60 completed requests and all forecast queries removed.
The earlier records will be linked by their original hashes, not rewritten as
new responses. All eight original baselines will be included.

The primary descriptive scores remain the original binding and transfer
contrasts, including all controls. Supplementary evidence based regret is
explicitly relative to a privileged static Bayesian observer. It is not a new
ground truth for human persuasion and cannot separate equivalent belief and
reward representations. No p values or confirmatory gate verdicts will be used.

## Runtime and spending boundary

The approved total allocation is capped at $5 including the first pilot. The
pilot's estimated GPU cost was about $0.35. Resume only the new diagnostic pod
`cgy7iwpf6z74qr`, retaining its downloaded public model cache. Do not start or
alter the old project pod `vqkuoeugozgfhj` or its network volume.

At most 90 more minutes of pod runtime is allowed, including startup. The runner
has a separate 80 minute limit. The external watcher must be armed and alive
before the model loads, and the live rate must be no more than $2/hour. At the
verified rate of $1.59/hour, 90 minutes costs $2.385 in compute. Storage and the
first pilot leave the planned run below $5. This is a bounded execution policy,
not a provider enforced hard billing cap.

No response fallback, automatic model retry or replacement for a failed response
is permitted. A failed request is preserved and stops collection. Retrieve and
verify every output before stopping compute. Permanent volume removal still
requires the pending user confirmation through the console; the user's request
to run experiments is not interpreted as permission to delete stored data.

## Package validation

The extension packet hash is
`ef4b8243492970c09849f74bfa0e999ef0e18b32003755bbfa199b2c9b91b0b1`.
The current deployable archive hash is
`dc0b397123dc5dc9b5100b47eaed99733573e0d97ddadbc2d81470b6aae50a15`.
It contains 660 exact new prompts and original pilot provenance.

Seventeen focused tests passed for collection, prefix resumption in mock mode,
scope checks, refusal to change model settings, rejection of reused pilot IDs,
preservation of failed responses and watchdog safety. A real model override is
not permitted in the extension runner.

The first standalone package verification failed because Python created bytecode
cache files inside the immutable package before its membership check. The CLI
now disables bytecode creation before importing project modules. The original
attempt was moved to `results/diagnostic_extension_package_20260909_attempt1`,
not deleted. The clean rebuilt package passed standalone verification. Its
scientific packet hash is unchanged. No paid model call was made by that attempt.

## Results

Execution details and measured outcomes will be appended here. At this writing,
the extension has not yet resumed GPU compute or collected a model response.

Relevant artifacts:

- `results/fixed_history_bank_audit_20260909/REPORT.md`
- `results/diagnostic_extension_package_20260909/manifest.json`
- `results/runpod_extension_20260909/control/`
- [Completed original pilot](RUNPOD_DIAGNOSTIC_FINDINGS_20260909.md)

## Resume failure and fresh pod fallback

The attempt to resume `cgy7iwpf6z74qr` returned RunPod HTTP 500. The response
body was not logged. Repeated read-only status checks confirmed `EXITED`, and
the watchdog confirmed the stopped state. No extension model call occurred.
The old public IP was absent and no SSH port was assigned. The cause of the
server error is not established; it is not described as a proven GPU shortage.

A fresh availability query reported A100 80GB stock at $1.59/hour. The control
process for the failed restart was closed. A new scoped control process created
`i0szqs87ifg0id`, named `latenttarget-diagnostic-extension-20260909`, at
20:34:44 UTC on 8 September (02:04:44 on 9 September in India). It has one
A100-SXM4-80GB, a fresh 150 GB pod volume and a 20 GB container disk. There is
no network volume attachment. The exact deadline is 22:04:43.166975 UTC.

The guard reported `ARMED` and was confirmed alive while the pod was running.
SSH confirmed 81,920 MiB of GPU memory and `/workspace` as a mountpoint. The
approved packet was uploaded to `/workspace/latenttarget-extension-20260909`.
Only the public SSH key was supplied to the pod. The API key remains in the
local control process memory and is not in the pod environment or logs.

The approval validator was changed to accept the exact scoped pod ID supplied
by the deployment approval rather than hard coding the failed restart pod ID.
This is an operational fallback, not a model or stimulus change. The prior
package is retained as `diagnostic_extension_package_20260909_attempt2`. The
scientific packet hash remains unchanged. The current archive hash is
`1222c954fafc71c8ddaa1641af53fc88ece0f552018f3edf1ce43c074197ebf6`.
Standalone package verification passed, and the extension plus watchdog tests
passed all 16 cases after this correction.

The bootstrap uses the NVIDIA wheel library directories themselves in
`LD_LIBRARY_PATH`, correcting an unnecessary parent-directory construction in
the older bootstrap. The earlier run succeeded, so this is not asserted to
explain its results. Shell syntax checking passed before upload. Dependencies
and hardware are checked again before any new model call.

Both previous pods remain stopped. Their volumes were not deleted. The failed
restart did not trigger an automatic repeated start command. The fresh pod uses
the same 90 minute runtime limit and $5 total allocation including the pilot.

## Collection is underway

The uploaded archive hash matched locally before extraction. Dependency
installation and the new runtime preflight passed: PyTorch 2.9.1+cu128,
Transformers 5.16.1, CUDA 12.8 and one A100-SXM4-80GB. The exact packet verified
again on the pod. The public checkpoint downloaded successfully, with only the
same unauthenticated Hugging Face rate limit warning as the pilot.

The model loaded and began returning valid digit choices. Progress monitoring
reads the completed request count, not interim scientific scores. At the first
recorded collection check, 35/660 had completed; a later check reached 73/660.
The watchdog remained alive. No interpretation of extension results has yet
been made.

The combined analyzer was written before inspecting extension choices. It joins
the original records using their frozen hashes and checks the complete 720
request identity set. It uses all 36 fixed bundles, retains conservative bounds
for missing or invalid cells, and separately identifies the 144 forecasts from
the parent ledger as not requested. It does not count them as failed choices.
Three analyzer tests passed, including missing responses, duplicate pilot
records and strict invalid output handling.

One compatibility detail is handled explicitly: the older generic parser accepts
surrounding whitespace, whereas the new collector requires an exact digit.
The combined analyzer respects the strict collection status. An invalid raw
response is preserved verbatim but treated as unknown when calculating bounds.
There is no rescue through a more permissive parser.

Export and retrieval were extended for the new scoped directory. Seven tests
passed for original and extension exports, archive corruption, unsafe paths,
complete file hashes and refusal to overwrite an existing backup. The exporter
has been uploaded, but will only archive after collection ends. A final full
repository regression is running concurrently on the local CPU, not RunPod.

## Final local regression

The full repository suite passed all 1,067 tests in 546.45 seconds. Its JUnit
record is `results/runpod_extension_20260909/full_regression.xml`. The additional
scalar scoring cross-check passed all three focused analysis tests, including
the incomplete and invalid-output cases. This check was added while the full
suite was already running, so its separate result is recorded rather than
implying it was included in the earlier test collection.

At the next progress check, 408/660 new model requests had completed with no
collection failure reported. Analysis of the model's extension choices still
awaits completed retrieval. The exact reporting contract and analyzer hash were
saved in `results/runpod_extension_20260909/analysis_contract.json` before those
choices were inspected.

## Completed collection, backup and shutdown

The SSH collection process exited successfully with all 660 planned new
responses and status `COMPLETE`. There was no response failure or rerun.
The exporter then created a 1,116,578 byte result archive containing 1,345
payload files and its manifest. The SHA256 was
`7f306512087019023bf6bd83fb1ff5a88241ca0e58906b81afcadc9291c3c46a`.
All member hashes, extracted file hashes, safe archive paths, the exact pod ID
and scientific packet identity passed verification. The local backup receipt
was written at 21:06:45.020326 UTC on 8 September, or 02:36:45 on 9 September
in India. All 660 new responses are present.

Only after verified retrieval, a stop command was sent for `i0szqs87ifg0id`.
RunPod reported `EXITED`, then the watchdog independently logged
`STOP_CONFIRMED` and ceased running. The local controller exited cleanly,
releasing its in memory credential. It did not restart or delete any pod.
The original pilot pod `cgy7iwpf6z74qr` remains stopped. The old calibration
pod `vqkuoeugozgfhj` and network volume `xkp8i0jxul` remain untouched.

The extension used about 32 minutes of pod time, approximately $0.85 at the
quoted $1.59/hour. Including the pilot, GPU compute is estimated at about
$1.20. This is not a final invoice. Stopped volumes continue to incur storage
charges. Explicit confirmation was requested to permanently delete only the
two temporary pods and their 150 GB disks. No deletion has occurred while
that decision is pending.

## Completed analysis and checks

The unchanged primary analyzer joined the 60 original records and 660 new
records. It verified source hashes, packet identity, all prompt hashes and
per request seeds. All 720 choices were valid, with no replacements. The
144 forecast queries in the parent ledger were reported as unrequested,
not invalid. Every original baseline and all 36 bundles remain in the report.

Combined mean scores, in the frozen metric order, were:

| Binding | Transfer | Paraphrase | No history familiar | No history composite | Random |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.076389 | -0.027778 | 0.006944 | 0.069444 | -0.194444 | 0.013889 |

These are contrasts, not success rates. The independent scalar scorer
reproduced every bundle and aggregate score, with maximum difference
`1.1102230246251565e-16`. The reporting contract's analyzer hash still matches
the current script. No primary scoring rule was changed after inspection.

A supplementary complete collection audit checked all request IDs, indices,
claims, response hashes, failure fields, completion records and raw digits
against the report. All passed. Input lengths ranged from 391 to 5,118 tokens.
The recorded generation calls total 1,578.42 seconds across both collections;
this excludes setup, loading, preflight, retrieval and idle time. Digits 1, 2
and 3 occurred 364, 313 and 43 times. These imbalanced counts do not by
themselves establish a position effect.

The supplementary audit was written after viewing the outcomes and is labeled
postcollection descriptive work. It adds no inferential test and makes no
model calls. Twelve final focused tests passed in 2.21 seconds for audit
descriptives, missing and invalid analysis, independent scoring, archive
export and safe retrieval. The new two audit tests were not part of the
earlier 1,067 test suite; their separate timing and JUnit file are retained.

Bootstrap inspection found the unauthenticated Hugging Face download warning
already seen in the pilot. No new traceback or generation failure was found.
Earlier package and resume failures remain documented above.

The [findings report](RUNPOD_EXTENSION_FINDINGS_20260909.md) includes all
conditions, baseline comparisons, bundle variation, raw pattern observations,
the history evidence limitation and the belief versus reward equivalence.
The README now states that the complete bank was collected and that the result
does not establish a latent partner model. The Google Doc was not changed,
and no commit or GitHub push was made. No human labeling, activation
collection, probe, steering intervention or further paid run was started.

## Final reproducibility check

The primary analysis was run again locally into
`results/runpod_extension_20260909/replay`. The summary, complete Markdown
report and manifest were byte identical to the first analysis. This replay
made zero model calls. The summary SHA256 is
`e3a00946316bec727d2fd8e23531330204d0a4018f43c64e2a2ec10fac633341`.
Local links in the findings, work log and README resolved successfully, and
`git diff --check` passed. A scoped credential pattern scan returned no
matches in the source, tests, new report, work log or extension results.
This scan is not a general security audit. Existing unrelated worktree
changes were preserved.
