# Work log: local preparation through RunPod readiness

Date: 8 September 2026. Repository: LatentTarget. This log covers the current
local preparation stage, not all historical experiments.

## Authority and continuity

The user asked to keep implementing and improving everything up to RunPod.
I treated that as authority to finish local engineering, perform the announced
machine measurement, and prepare an exact small GPU run. I did not create a
paid pod, run a large confirmation experiment, modify Google Docs, commit or
push. I did not retrieve or use a RunPod credential. The previously pasted
secret was not copied into any file.

I used the GSD resume skill to restore context and the experimental design
skill to fix the comparison before outcomes. GSD found no `.planning` state
in this mature repository. Existing research documents remained the source of
continuity. No GSD phase execution, registered phase review or milestone
completion is claimed. The design guidance led to separate development and
evaluation scenarios, frozen shortcut fitting, retained controls, and a clear
boundary between diagnostic evidence and confirmation.

The working tree was already dirty. Historical source files and raw results
were preserved. Read only hash checks against four manifests found no changes
to their recorded inputs: 13 calibration inputs, 16 prior stimulus inputs,
nine original offline inputs, and 15 grounded audit inputs.

## Sequence and implementation

1. Read the current design, prior calibration failures, wording audit and
   source code. Wrote `POD_READINESS_PLAN_20260908.md` before the new bank's
   outcomes. Fixed 36 development and 36 evaluation bundles, seeds 202609086
   and 202609087, five shallow similarities and three annotated references.

2. Added `grounded_partner_bank_20260908.json` with three development and
   three evaluation families. Each supplies nine explicit facts and nine
   paraphrases. Plan B has a modest timing advantage. Scenario facts are
   shuffled without frame headings; target assignment does not change them.
   The bank was not changed after its results or machine reviews.

3. Added `src/grounded_partner.py` and `scripts/prepare_grounded_partner.py`.
   The pipeline retains the original balanced target and candidate allocation,
   feedback draws and identity rebinding. It projects only visible fields
   into prompts, checks exact facts, keeps development histories out of the
   evaluation scenario families, and fits similarity direction on development
   only. Complete prompts and synthetic responses are archived for both splits.

4. Ran the full 72 bundle grounded audit. Each split has 864 planned requests,
   including forecasts retained offline. Eight policies produce 13,824 saved
   synthetic responses across both splits. Additional positive and reversed
   development trials are retained in the frozen fit results. No focal model
   was called for this audit. Strong wording shortcuts remain visible.

5. Added the algebraic belief/value equivalence check. Ran 10,000 random cases
   with seed 202609088. Maximum prediction difference: 2.22e-16. Choice
   disagreements: zero. This is a simulator identification limit, not a finding
   about what an LLM internally represents.

6. Added `src/grounded_review.py` and `scripts/review_grounded_messages.py`.
   Both reviewers receive 54 opaque item IDs with scenario, options and message
   only. Fixed models: gpt-5.6-sol and gpt-5.6-luna. Fixed batch size: 18.
   Isolated Codex invocations use no repository context, ignore user rules and
   configuration, request no tools, and use a strict JSON schema. A durable
   claim precedes each call. Uncertain calls cannot automatically repeat.

7. Actually completed three calls per judge, six calls total. Both runtime
   headers reported the requested model. All 108 assessments and their exact
   inputs, outputs and metadata were retained. Sol agreed with 53 registered
   labels and Luna with 52. Their three disagreements concern two distinct
   messages. No valid unfavorable judgment was rerun. This consumes account
   capacity, but no RunPod GPU. Dollar cost cannot be inferred from the CLI
   output. Human labels remain zero.

8. Added `scripts/report_grounded_machine_review.py`. It reconciles each
   complete review with raw batches, input hashes, exact prompts and reported
   model IDs. Ran it successfully. No acceptance threshold was declared, so
   it reports scores and disagreements rather than inventing a gate.

9. Verified the official Qwen model identity and revision through the public
   Hugging Face API. Read the official model card and RunPod pricing and stop
   documentation. Fixed the diagnostic parameters in
   `diagnostic_pilot_20260908.json`. Selected the first indexed bundle for each
   evaluation family without selecting on response patterns or judge scores.

10. Added `src/diagnostic_pilot.py` and `scripts/run_diagnostic_pilot.py`.
    The runner verifies package hashes, the pinned model, exact generation
    settings, all 60 request IDs, full branch coverage and prompt hashes.
    Model inputs contain only system/user strings and an empty context.
    Every request has a deterministic seed and a durable claim before dispatch.
    Output records have hashes, timing, validity and failure status. Completed
    calls can resume; uncertain or failed calls halt without replacement.
    Real mode cannot inject a mock provider or alter the schedule.

11. Added a live runtime guard for one A100 80GB, pinned dependencies, BF16,
    no CPU/disk offload, no activation capture and an input token ceiling.
    Real collection requires explicit execution and a packet specific approval
    with live price, pod ID, deadline, persistent storage and a verified
    external watchdog. No approved execution file has been generated.

12. Added `scripts/build_diagnostic_packet.py`. It verifies the full offline
    ledger before selecting the pilot. Only eight explicit source/dependency
    files enter the portable package, plus packet, local requirements and run
    instructions. No `.env`, Git history, credentials, old datasets or analyst
    labels enter the GPU archive. All files and the archive have hashes.
    Source data, annotations and complete history transcripts remain locally
    alongside the package, outside the focal inputs.

13. Built `results/diagnostic_pilot_package_20260908`. Archive size: 69,388
    bytes. Packet digest:
    `418f24b657eff7bb731ddb93a066889c63507fcab5cadc414231c3257ecba4f1`.
    It contains 60 prompts from bundles 00003, 00000 and 00001, covering all
    three evaluation families. Each bundle has 20 choice queries. Forecasts
    are excluded. These are teacher forced counterfactual queries, not a
    sequential silent target swap or freeform interaction.

14. Added `scripts/check_diagnostic_tokenizer.py`. Installed tokenizer tools
    in a separate temporary environment, leaving the project environment
    unchanged. Used transformers 5.16.1, tokenizers 0.23.2, huggingface_hub
    1.30.0 and Jinja 3.1.6. Downloaded tokenizer/configuration files, not model
    weights. All 60 prompts passed: 391 to 5,114 tokens. Choices 1, 2 and 3
    map to tokens 16, 17 and 18. Saved rendered text and token sequence hashes.
    This checks the tokenizer fallback, not the GPU multimodal processor path.

15. Added `src/diagnostic_analysis.py` and `scripts/analyze_diagnostic_pilot.py`.
    Every planned cell survives analysis. Missing and invalid responses retain
    worst case bounds. The report includes all eight reference policies and
    every raw focal choice. It produces no confidence interval or p value at
    three bundles. Its contrast calculation was checked against the existing
    independent vectorized implementation for all eight policies.

16. Ran the portable runner through all 60 mock choices and generated the
    complete mock report. Both the report and metadata explicitly identify
    mock outputs as engineering fixtures, not research findings. An isolated
    archive extraction also ran successfully outside the repository.

17. Added `src/diagnostic_watchdog.py` and `scripts/watch_diagnostic_pod.py`.
    The future local watchdog reads and stops only its explicitly named pod.
    It handles deadline expiry, excessive live price, repeated read failure
    and uncertain stop responses. It saves only a restricted status projection,
    never the full pod response, environment or authentication header. It
    refuses existing network volume pods, which require different lifecycle
    handling. No live RunPod request was made. Stopping does not delete results
    or eliminate persistent storage charges.

## Tests, warnings and implementation mistakes

- Initial focused checks passed: 12 grounded bank tests, seven review tests,
  21 collection/packaging tests, five analysis tests and six watchdog tests.
  The combined 51 test run passed in 7.92 seconds.
- Cases exercised include reproducible allocation, hidden metadata isolation,
  source tampering, development only fitting, reversed shortcut fitting,
  strict judge scores, absent IDs, duplicate IDs, changed prompts, request
  limits, invalid outputs, simulated provider interruption, safe resume,
  archive portability, analyst reconciliation, and simulated pod stop failures.
- The first config draft had a copied revision suffix repeated. The public API
  check caught it before packaging or any focal call; it was corrected to the
  verified revision. No model was run under the incorrect identifier.
- One exploratory inspection requested a nonexistent `simulator` key instead
  of `target`. It raised `KeyError` and was corrected in the inspection. It did
  not change an experiment or artifact.
- The first attempt to save historical source verification found that the
  pytest output directory had not yet been created. Checks had printed no
  changed inputs, but the export raised `FileNotFoundError`. I created the
  intended output directory and reran successfully. The saved file is the
  successful run, not a claimed export from the failed attempt.
- The isolated tokenizer environment warned that PyTorch was not installed.
  That was intentional: only tokenizer utilities were used there. The actual
  GPU model path remains untested.
- The complete repository suite passed **1,046 tests in 229.37 seconds**,
  with zero failures, errors or skips. Results are recorded in
  `results/pod_readiness_verification_20260908/pytest.xml`. The command was
  `.venv/bin/python -m pytest -q --junitxml=results/pod_readiness_verification_20260908/pytest.xml`.
- Python compilation checks passed for the new collection, analysis, watchdog,
  packaging, tokenizer and report code. `git diff --check` passed. The new
  human readable planning, findings and work log documents contain no em dashes.
- Final artifact verification checked all 16 packaged/supporting files,
  rebuilt the archive in a temporary directory with a byte identical SHA256,
  and verified a fresh extraction outside the repository. The result is saved
  in `results/pod_readiness_verification_20260908/final_verification.json`.

## What remains

The hardware step is a small diagnostic, not the end of the research project.
It still needs approval of the exact packet and proposed $5 allocation, a
fresh price/availability check, a new scoped pod, secure credentials supplied
through the environment, live watchdog verification, and model loading.
There is no need for the user to write code.

After collection: retrieve all outputs and failures, run the prepared analysis,
show the three complete bundles, and stop. Do not scale automatically. Strong
wording baselines, ambiguous composite strength, unfinished human validation
and the belief/value identification limit remain scientific problems even if
every infrastructure test passes.
