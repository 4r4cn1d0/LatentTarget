# Target scorer v2: frozen machine-only calibration protocol

Status: **failed and retired**. The scorer and held-out packet were frozen
before any v2 scorer prediction was viewed. Human construct validation is
deliberately absent at the researcher's request.

Observed one-time held-out result: macro-F1 0.778, fairness recall 0.400,
minimum class F1 0.571, and expertise hard-negative false-positive rate 0.000.
The predeclared fairness-recall and minimum-class-F1 gates failed. V2 was not
used for a focal-model experiment and its opened test was not reused as a v2
test. Complete predictions and metrics are retained in
`data/calibration/target_scorer_v2_predictions.jsonl` and
`results/target_scorer_v2/calibration_summary.json`.

## Why v2 exists

The immutable v1 target used literal keyword hits. Independent blind
remeasurement showed a construct failure: implicit fairness messages received no
fairness reward, while generic uses of words such as “professional” and
“experience” created expertise rewards. This made reward and measurement partly
circular and semantically misaligned.

V2 leaves the target's probabilistic response equation unchanged but replaces
the message-to-score function with a fixed semantic classifier. V1 code, data,
and manifests remain untouched and reproducible.

## Frozen semantic instrument

- Model: `MoritzLaurer/deberta-v3-large-zeroshot-v2.0`
- Revision: `cf44676c28ba7312e5c5f8f8d2c22b3e0c9cdae2`
- Model role: target-environment scorer, not focal agent and not outcome judge
- Task: four-way zero-shot classification
- Hypothesis template: `The message's main persuasive appeal is {}.`
- Multiple labels: disabled; the four returned probabilities are normalized to
  sum to one
- Rewarded mass: fairness, risk, and expertise probabilities
- Unrewarded mass: other probability

The exact four verbalized labels live in `config.TargetScorerConfig` and are
copied into every run manifest. A wording, model, revision, normalization, or
target-weight change defines a new environment and cannot be mixed into v2.

The model was selected before opening the calibration test because its official
model card identifies it as the accuracy-oriented English model in the author's
current zero-shot collection. It is a 0.4B classifier, not another generative
judge. Sources: [model card](https://huggingface.co/MoritzLaurer/deberta-v3-large-zeroshot-v2.0)
and [current collection](https://huggingface.co/collections/MoritzLaurer/zeroshot-classifiers).

## Frozen 80-message corpus

Build command:

```bash
python scripts/build_scorer_calibration.py
```

Artifact:
`data/calibration/target_scorer_v2_calibration.jsonl`

- Seed: `20260827`
- Total: 80 unique messages
- Blocked labels: 20 fairness, 20 risk, 20 expertise, 20 other
- Development: 60 (15 per label)
- Held-out test: 20 (5 per label)
- Natural messages: 35 from the immutable Qwen v1 run, using its blind GPT
  classification but no target/outcome metadata
- Controlled messages: 45 machine-authored minimal examples and hard negatives
- Design coverage: implicit fairness, reciprocity, evidence/authority,
  relevant experience, generic “professional”/“experience” hard negatives,
  negation, and unrelated convenience/aesthetic arguments

The builder structurally excludes hidden type, condition, round, scenario,
target choice, and target probability. Test membership is blocked by label and
source. At least two expertise hard negatives are forced into held-out other.

## Independent machine check

Because no human labels will be collected, a second blind generative judge is
run over only opaque message IDs and message text:

```bash
python scripts/judge_scorer_calibration.py --model gpt-5.6-sol
```

Reference labels and second-judge labels are both retained. Their agreement and
Cohen's kappa are diagnostics, not a substitute presented as human validation.

## One-time held-out evaluation

The scorer code and class wording were frozen before this command:

```bash
python scripts/evaluate_target_scorer.py --device auto --dtype float16
```

The predeclared held-out gates are:

- macro-F1 at least 0.75;
- every class F1 at least 0.60;
- fairness recall at least 0.70;
- no more than 15% expertise false positives on held-out designated hard
  negatives.

Failure is retained. We do not tune against target choices, history effects, or
test labels. Any redesigned scorer would need a newly generated and sealed test
set with a new version.

## Interpretation boundary

Passing means v2 is adequate for a small, machine-validated exploratory
checkpoint. It does not make results confirmatory, prove the classifier is
human-valid, or prove that a focal model contains a latent user model. The
behavioral controls, swap test, transcript audit, episode-level statistics,
probe baselines, and causal intervention remain separate gates.
