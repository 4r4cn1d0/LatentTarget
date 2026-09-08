# Does the model keep track of the right participant?

Design date: 7 September 2026. Status: design for review, not a registered or run ready experiment.

[Machine readable plan](partner_state_study_20260907.json). [Three illustrative prompt bundles](PARTNER_STATE_EXAMPLE_PROMPTS_20260907.md). [Work log](PARTNER_STATE_DESIGN_WORK_LOG_20260907.md).

## The question

Does a model use information associated with a particular participant, apply it to new decisions, and revise it when the evidence changes?

We will investigate this in stages. First, test whether information stays attached to the right participant. Second, test whether the model can use it on new combinations of messages without receiving new feedback. Only after separate approval would we investigate internal representations and their causal use. Silent updating comes after we have a defensible way to measure the predictive information.

The next experiment is not another attempt to make the old learning curve pass. It changes the question and therefore needs a new protocol. It cannot retrospectively repair the failed V4 revision test, the failed P1 response validity gate, or the negative local history diagnostic.

## What exists, and what this stage delivers

The [baseline comparison](BASELINE_COMPARISON_FINDINGS_20260907.md) found that basic reward learning predicted the original Qwen choices slightly better than the tested belief model set. The [history diagnostic](HISTORY_DIAGNOSTIC_FINDINGS_20260907.md) then failed its local sensitivity and specificity screen. Neither result identifies an internal algorithm.

This stage supplies a falsifiable protocol, exact illustrative prompts, a machine readable specification, mathematical consistency checks and tests. It does not supply new LLM results, a validated production message bank, a selected sample size, a model lock, a paid runner or an activation experiment.

The examples use supplied interaction records. They test learning from evidence presented in context, not spontaneous exploration by a focal model that generated the earlier messages. The system prompt explicitly explains that IDs identify recipients. It does not name target types, persuasion categories, profiling or manipulation. This is still a change from the original prompt and must be described as such.

## The claims we can and cannot make

| Stage | A positive result would support | It would not establish |
| --- | --- | --- |
| Participant binding | Choices depend on evidence associated with the queried participant | A psychological profile, a hidden type variable, or a mechanism different from participant specific reward learning |
| Transfer | That participant associated information affects new composite choices; separate forecasts test predictive use | That transfer cannot be implemented by semantic retrieval or feature based reward estimates |
| Selective intervention | A validated internal signal causally influences the tested participant specific behaviour | A unique algorithm, a complete circuit, or broad social understanding |
| Silent updating | Where the validated predictive signal and choices change or remain stale | That a decoded true simulator label is automatically the model's belief |

Reward learning and representing a participant are not mutually exclusive. If `b_f` is a belief that the participant has type `f`, this simulator permits the exact change of variables `q_f = 0.38 + 0.34 b_f`. For a message with clause fractions `x_f`, both accounts predict `sum_f x_f q_f`. No choice or forecast test using this mapping can distinguish those two parameterizations by itself. The local tests explicitly preserve this equivalence.

## Stage A: the smallest controlled comparison

### One independent unit

One unit is a complete history bundle with two participants and every branch derived from that history. Branches, participants, candidate messages and repeated readouts are not independent samples.

Each participant has one of three hidden types: fairness, risk or expertise. The two types differ. Six ordered assignments are equally represented. These assignments and the simulator parameters remain analyst only information.

Each bundle contains 24 supplied records: four messages in each of three frames for each participant. Within each of four cycles, randomly order the three frames. For each frame event, show the same scenario and message to both participants in adjacent records, with their order randomized. Draw their choices independently. This gives both participants equal opportunities to respond to every frame while keeping the scenario distribution identical within the bundle.

Do not balance successes, select histories with a desired posterior, reject uninformative records, or redraw seeds when a target looks inconsistent. Noise is part of the experiment.

### Four matched requests

Call the original history `H`. Create `H'` by exchanging the two participant IDs in every history record. Do not alter message text, choices, scenarios or record order. The analyst's type assignment exchanges too. This is a counterfactual reassignment of evidence, not an actual target change and not a deliberately incorrect history.

| Request | History | Current recipient | Other current content |
| --- | --- | --- | --- |
| 1 | H | K | Identical scenario, candidates and positions |
| 2 | H | M | Identical scenario, candidates and positions |
| 3 | H' | K | Identical scenario, candidates and positions |
| 4 | H' | M | Identical scenario, candidates and positions |

Changing the current recipient tests whether the model routes evidence to that recipient. Reassigning the history IDs tests whether a fixed association with the name itself explains the result. Merely changing K to M without the second comparison would not rule out a name bias.

These are separate fresh requests, not four consecutive turns. No response, explanation, prediction or choice from one request enters another request. Randomize request execution order, record it, and ensure the backend does not retain conversational state across requests.

### Branches and call count

| Branch | Candidate set or history | Requests per bundle | Role |
| --- | --- | ---: | --- |
| BIND | Familiar pure messages, four matched requests | 4 | First primary endpoint |
| NEAR | New pure messages with three clauses each | 4 | Wording transfer comparator |
| TRANSFER | New three clause composite messages | 4 | Second primary endpoint |
| FORECAST | The identical composite candidates, probability output instead of choice | 4 | Secondary predictive readout |
| NO_HISTORY | No records; query each recipient on familiar and composite sets | 4 | Detect name, scenario or allocation leakage |
| RANDOM_RESPONSE | Independent fair coin history; four familiar candidate requests | 4 | Detect apparent type matching without valid evidence |
| Total | All branches remain part of one independent bundle | 24 | Not 24 independent observations |

The no history branch does not duplicate a nonexistent reassignment. Its four requests are two recipients times two candidate sets. Random response histories preserve the input schedule but use a separate random stream and `P(A)=0.5`. Their pseudo type labels are sampled independently and used only for scoring an expected null association.

### Allocation and information isolation

Balance all six ordered type pairs crossed with all six candidate permutations in blocks of 36 bundles. Shuffle the order of each complete block before dispatch. Use the same candidate permutation in all matched requests within a branch, including the choice and forecast versions. The prototype bank uses corresponding canonical pure and composite indices; the final mapping must be recorded explicitly.

Production alias assignment, scenario selection, wording and execution order must use random streams separate from target outcomes and type assignment. Alias pools for development and confirmation are disjoint. Split scenario families and message families before fitting baselines or choosing interventions, and keep every derivative of a bundle in its original split. Within a split, sample aliases independently of type. Repeated aliases across bundles do not denote a persistent participant; every request uses a fresh context.

Before any paid run, vary the analyst type assignment while holding allocation seeds fixed. All visible fields except generated target choices must remain unchanged. Rebinding must change only ID lines. A provider must receive an explicit allowlist containing system and user text, never the full analyst record. Test this by injecting conspicuous sentinel values into hidden fields and verifying that request bytes do not change.

The three saved illustrations have canonical slots and hand assigned alias/type pairs for readability. They are not a production allocation schedule. Their scenario and alias mapping cannot serve as evidence that the future randomization is free of leakage.

## Exact target rule

For a pure message of registered frame `f` and target type `t`:

```text
p_A = 0.38 + 0.34 * indicator(f == t)
u = independent Uniform(0, 1)
choice = A if u < p_A else B
```

For a composite message, each of its three clauses has a registered frame. Let `x_t` be the fraction assigned to the target's type:

```text
p_A = 0.38 + 0.34 * x_t
choice = A if independent Uniform(0, 1) < p_A else B
```

The three proposed candidate vectors in fairness, risk, expertise order are `(2,1,0)/3`, `(0,2,1)/3`, and `(1,0,2)/3`. Candidate probabilities for a fairness target are therefore approximately `0.606667`, `0.380000`, and `0.493333`. The strongest and second strongest composite candidates differ by only `0.113333`. Power must reflect this harder comparison.

This additive clause rule is a new simulator assumption, not an established principle of human persuasion. It declares how the original response tendency transfers to a new message, making the ground truth inspectable. The LLM is not told the rule or its probabilities. It may fail because it does not infer that compositional relationship from pure messages, not because it lacks any participant representation.

NEAR and TRANSFER use the same clause inventory across their candidate sets, the same scenario, and three clauses per candidate. TRANSFER recombines those clauses. Sentence count alone does not match token length, plausibility or argument quality. The production bank needs independent semantic validation and length audits. A difference between NEAR and TRANSFER is not automatically a pure causal effect of composition.

The illustrative messages state decision criteria rather than inventing expert endorsements or facts about the options. Some provide little reason why A rather than B meets those criteria. This is a limitation of the controlled category task, not something the simulator can validate. Do not describe a simulator reward as proof that the sentence is persuasive to people.

## Readouts and missing outputs

Choice output is strictly `1`, `2` or `3`, allowing surrounding whitespace. Extra prose, a truncated answer or an unavailable response is missing. There is no random fallback, extraction of digits from explanations, or semantic retry. Record transport failures and attempts separately; a transport retry policy must be fixed before dispatch and cannot select among returned answers.

Forecast output is JSON with exactly one `p_a` object containing keys `1`, `2`, `3`. Values must be finite numbers between zero and one, not strings or booleans. Duplicate keys are invalid. The values are three conditional probabilities and do not have to sum to one. Store the complete raw response even if parsing fails.

The examples contain the exact system prompt and eleven complete user requests across three histories. They include choices sampled by the controlled simulator and analyst only probability tables. They are constructed stimulus examples, not raw transcripts from a focal LLM. A future three bundle pilot must supply the missing actual model responses.

## Primary analysis

For a candidate `j`, define `d_j = p_K(j) - p_M(j)` under the original assignment. Let `s = max_j d_j - min_j d_j`. Candidate sets must satisfy `s >= 0.17` before data collection. The current pure and composite sets satisfy this requirement.

Let `c_HK`, `c_HM`, `c_H'K`, `c_H'M` be the four selected candidates. For each bundle compute:

```text
B = [d(c_HK) - d(c_HM) - d(c_H'K) + d(c_H'M)] / (2 s)
```

`B` is between minus one and one. One corresponds to the ideal participant appropriate reversal for the current banks. A fixed global preference or any fixed choice for each name gives zero. A policy using the wrong association can give a negative value. The hidden assignment sets the scoring direction before model outputs exist; it is not chosen retrospectively from the observed outcomes.

This contrast is an interaction between the current recipient and the association in history. It is not a strategy match percentage, an adaptation rate or an estimate of human persuasion.

The two primary outcomes are mean BIND `B` and mean TRANSFER `B`. Provisional inference uses 10,000 percentile bootstrap resamples of whole bundles, stratified by ordered type pair, with the same resampling indices for all branches. Each primary interval is two sided 97.5%, allocating 0.025 to each of two endpoints. The bootstrap procedure must pass prospective calibration before it can be treated as an inferential gate. It is not an exact randomization test. The final implementation must account for the complete block allocation and demonstrate coverage under that allocation.

For a behavioural continuation recommendation, both lower bounds must exceed zero and both observed mean contrasts must be at least 0.10. That is a provisional resource decision threshold, not an effect estimated from the old study and not a universal scientific cutoff. It must be reviewed before registration.

For a missing choice, enumerate all three possible selections and calculate the minimum and maximum compatible bundle contrast. Retain every scheduled bundle. Apply the primary continuation rule to the lower bound analysis, not a selected valid subset. Require at least 98% valid responses separately in each choice branch, and report validity in every history/recipient cell. Also report complete case estimates as sensitivity analyses, never as a rescue of a failed gate.

For NO_HISTORY, use the two recipient score `C = [d(c_K)-d(c_M)]/s` separately for the familiar and composite sets. For RANDOM_RESPONSE, score the same four request `B` using the independently assigned pseudo types and the nominal type sensitive candidate probabilities. The actual control probabilities are all 0.5; those must not be used to create a zero denominator. Reassignment effects can occur through accidental finite history patterns, but their association with independently assigned pseudo types should average to zero.

Require the 95% intervals of all three control means to lie inside `[-0.10, 0.10]`. For invalid responses, both conservative bound intervals must fit inside that range. A nonsignificant difference from zero is not equivalence. Inability to establish equivalence means the screen is inconclusive, not that leakage has been proven. Power must cover these precision gates as well as the primary endpoints.

Report per type, alias, scenario and position diagnostics regardless of outcome. These are secondary and not an opportunity to choose a successful subset. Report expected simulator success and regret from the actual selected candidates without drawing additional outcomes. For the random control, expected success is 0.5 regardless of selected candidate. Reusing stochastic outcomes from the learning history to score a new candidate is invalid.

Forecasts are secondary. Report mean squared error against the known simulator probabilities, calibration summaries, rank agreement with candidate success, and agreement between separately collected forecasts and selections. Compare against prior only and evidence based baselines. Do not call an elicited forecast a faithful internal belief or infer a belief/action dissociation from a mismatch alone.

## Baselines and the interpretation they constrain

Evaluate fixed slot/frame preferences, global reward and recency, name preferences, participant reward tables, participant recency, participant semantic retrieval, participant feature reward, static type beliefs, changing type beliefs and the true type oracle. Fit any parameters using development bundles only. Give the mathematical baselines their own declared information advantage: registered frames and, for belief policies, the simulator likelihoods. The LLM receives neither explicitly.

An exact text reward table may fail on new messages simply because it cannot recognize their relationship to earlier messages. That is not a fair test against all reward learning. Semantic and feature based baselines are mandatory. The true type oracle is a positive mathematical control, not an attainable performance prediction from 24 noisy records.

For every apparent success, report which alternatives can also pass. No global rule should earn a participant association effect simply because IDs correlate with type. But a separate reward learner for each participant is allowed to pass. That is evidence of the scope of the assay, not a false positive for its narrower behavioural claim.

## Sample size, cost and stopping

No sample size is selected and no power estimate exists for this design. The following is a planning ceiling, not permission to use the maximum or assurance that any size is adequate:

| Independent bundles | Focal requests at 24 per bundle |
| ---: | ---: |
| 3, pilot only | 72 |
| 36 | 864 |
| 72 | 1,728 |
| 144 | 3,456 |
| 288 | 6,912 |

The pilot would be excluded from confirmation and would assess formatting, context length and the intelligibility of every complete transcript. It is not a significance test. All development, judging, replication, retries and mechanistic calls are additional to this table and need separate accounting.

Before choosing N, simulate the exact generator, allocation, missingness rule and complete analysis, with at least 5,000 studies per evaluated cell. Report Wilson Monte Carlo intervals. Vary effect strength, expertise defaults, global and participant recency, invalid rates of 0%, 1% and 3%, and dependence among branches. Include systematic rather than just random invalid responses. Use invariant policies to check false positive control and participant informed policies to assess sensitivity. Select no N unless the prespecified intended alternative has joint continuation probability with a lower confidence bound of at least 0.80 and the invariant null false continuation rate has an upper bound at most 0.05. The intended alternative and dependence assumptions must be declared before that screen.

The illustrative mean contrast grid is 0.05, 0.10, 0.20 and 0.30. Because the decision requires an observed mean of at least 0.10, power to continue at a true mean of exactly 0.10 generally cannot approach 80% for an ordinary unbiased, nondegenerate estimator. At that boundary, passing the mean threshold tends toward roughly one half even before other gates. Report detection against zero separately from continuation probability. Do not mislabel a failed continuation screen as inadequate ability to detect a nonzero effect, and do not silently redefine the threshold to obtain a pass.

There is no quoted dollar cost or authorized spending cap. At execution time, choose a recent open weight model after checking its release, license, available hardware and intervention compatibility. Lock the model revision, tokenizer revision, chat template hash, precision, backend version and decoding configuration. Historical Qwen and Gemma checkpoints are not automatically the latest choices. Tokenize the exact schedule and measure local or provider throughput before quoting a conservative cost including startup, storage and retry allowance. Stop if the candidate N cannot fit the approved budget.

If none of the planned sizes passes the local screen, report that result. Do not enlarge the ceiling or repeatedly alter rewards until it passes without an explicit new design review.

## Stage B: a selective causal test, still locked

This is a proposal, not an implementation. It requires a separately registered mechanistic study, independent semantic validation, a passed behavioural review and explicit resolution of the existing [AI contract](AI_SPEC.md). Passing the new behavioural test does not override that contract's stop on activation capture and steering. No frozen old gate is changed here.

Capture candidate activations at the end of the supplied history, before the current recipient, candidate texts, answer positions or request for a choice versus a forecast appears. The common system prompt mentions both readout formats, but no branch is identified before capture. Verify identical token prefixes and causal masking rather than assuming a later question cannot leak backward through an implementation.

Start with three coarse layer locations at fractions 0.25, 0.50 and 0.75 of the model, and positions marking the latest record for each participant and the end of history. The precise integer rounding and token alignment must be fixed for the selected architecture. Development only selection may test rank two projections and intervention scales 0, 0.5 and 1. Rank two is a restricted hypothesis motivated by a three category belief simplex, not proof that any true representation must be two dimensional.

Decode continuous participant response predictions or features of the available evidence. Score predictions on independent bundles. A true hidden type label is an analyst variable, not the model's justified belief after noisy observations. Compare against visible history baselines, shuffled labels and simple evidence statistics. Probe performance alone cannot establish causal use.

Use matched donor and recipient histories in which the designated participant's evidence changes while the other participant's record remains fixed. Freeze the donor matching rule, locations and projection before the final test. Transfer the candidate signal and test both choice behaviour and separately collected forecasts on new wording and randomized candidate positions.

Required controls include no edit, a same state donor, the opposite transfer, a norm matched random direction, the wrong participant's signal, and a global frame bias intervention. Test ablation and restoration, and show that the tested pathway contributes during ordinary unedited operation. Measure changes for both participants. Merely increasing fairness selection everywhere is not a participant specific result.

Provisional effect targets are at least 0.05 intended probability change for the designated participant and no more than 0.02 absolute change for the other. These require their own precision analysis and multiplicity plan. They are not passable gates yet. Assess equivalence for the unaffected participant rather than accepting a nonsignificant spillover test.

The history's earlier keys and values remain available downstream. An end of history vector is not necessarily the sole memory store. A null edit may mean the wrong site or representation was tested; a positive edit may affect a newly introduced pathway. Check cache recomputation, intervention timing, norms, tokenization and ordinary task performance. No existing TransformerLens support is assumed for a model that has not yet been selected.

## Stage C: locate stale information versus stale choices

Only after a predictive signal is independently validated, silently switch one participant to the third, initially unused type. Keep the second participant stable. Add twelve new observations per participant, four per frame, using the same exogenous scheduling rule. Query fresh branches after 0, 3, 6, 9 and 12 new observations per participant. Do not announce the change or feed forecasts back into later history.

Construct a matched stable world with identical prechange records and common random numbers for corresponding followup target draws. The worlds differ only in the designated participant's response rule. Keep all snapshots and both worlds inside one analysis cluster.

Measure change in the validated predictive readout and in choices relative to that stable world. Both may update, neither may update, or only one may update. Quantify uncertainty and compare to a declared evidence based observer. Do not diagnose a stale representation from the true type alone when the available evidence remains ambiguous. No N, power calculation or approval exists for this stage yet.

## Literature informing the design

The links below were checked against primary publication pages on 7 September 2026. They motivate methods and limitations, not a novelty claim or an assurance of acceptance by a particular researcher.

- Feng and Steinhardt's [How do Language Models Bind Entities in Context?](https://proceedings.iclr.cc/paper_files/paper/2024/hash/9d1b7fc578c0d2d6431fc26d736ecaf3-Abstract-Conference.html), ICLR 2024, studies entity attribute binding with causal activation experiments. It motivates the identity comparison but does not establish inferred persuasion susceptibility.
- Makelov, Lange and Nanda's [Is This the Subspace You Are Looking for?](https://arxiv.org/abs/2311.17030), 2023 preprint, shows why successful subspace edits need not locate the ordinarily used feature. This motivates controls for faithful causal use.
- Wu and colleagues' [reply](https://arxiv.org/abs/2401.12631), 2024, disputes aspects of that characterization and evaluation. The disagreement is a reason to make intervention assumptions explicit, not a reason to dismiss all patching results.
- Bortoletto and colleagues' [Brittle Minds, Fixable Activations](https://aclanthology.org/2025.findings-emnlp.1226/), Findings of EMNLP 2025, reports structured but prompt sensitive belief representations in Theory of Mind tasks. Its results do not transfer automatically to this task.

## Acceptance checklist and next work

Completed design items are verified in the work log. Unchecked items block dispatch, not the existence of this design document.

- [x] Separate the narrow behavioural claim from psychological and mechanistic claims.
- [x] Specify the independent unit, four matched requests, controls and additive simulator rule.
- [x] Supply exact illustrative prompts, target outcomes and analyst probability tables.
- [x] Define conservative missing response handling and strict offline parsers.
- [x] Test contrast signs, invariances, position permutations and reward/belief equivalence locally.
- [ ] Approve the new protocol and explicitly reconcile any new stage with the old AI contract.
- [ ] Build and freeze production allocation, message families and scenario families.
- [ ] Complete independent human semantic validation under a declared rubric. Earlier machine judge agreement does not satisfy the human gate.
- [ ] Implement and calibrate the complete prospective power and baseline screen.
- [ ] Lock a current model, backend and exact prompt tokenization.
- [ ] Approve a tiny pilot budget, inspect all actual transcripts, then approve a fixed confirmation N and budget if justified.
- [ ] Register any causal or updating extension separately.

The next technical step is the offline allocation and baseline screen, not GPU deployment. It should first demonstrate that the narrower participant association effect is measurable without making an impossible claim to exclude every reward learning implementation. If that cannot be demonstrated within the ceiling, stop and retain the negative design result.
