# What the simpler explanations tell us

7 September 2026. [Full results and tables](../results/baseline_comparison_20260907/REPORT.md).
[Plan written before fitting](BASELINE_COMPARISON_PLAN_20260907.md).
[Work log](BASELINE_COMPARISON_WORK_LOG_20260907.md).

## The short answer

The original Qwen result does not need a model that explicitly tracks a hidden
partner type to achieve the best prediction among the rules we tested. A
simple reward learner predicted its next choices slightly better.

That makes the interpretation narrower. We still observed behavioural
adaptation in the original experiment. But these data do not distinguish that
adaptation from learning which message category has recently paid off.

The result was not uniform across models. A static belief model predicted
Gemma better than the selected simple model set. We should report this too,
without turning it into a claim about Gemma's internal representations.

## What I actually compared

I used the 25,200 existing records across V4, R1, E1 and P1. There were no new
model calls. Each run was analysed separately.

The simple rules included always preferring expertise, repeating the last
message category, repeating it after success, counting prior choices without
using their rewards, and updating an estimated reward for each category.

The belief rules maintained probabilities over the three possible partner
types. One assumed that the type stayed fixed. The other allowed a constant
chance of change between interactions, without knowing the actual swap time.
Both used the simulator's known likelihoods. The reward learner did not need
a variable representing partner type.

The flexible rules also included a learned preference for each frame and a
tendency to repeat the previous frame. This matters. The comparison is not
between an elaborate belief model and a deliberately weak alternative.

I split the 20 scenario seed indices into five folds. For each fold, models
were fitted and selected using the other 16 indices. All rounds, target types,
conditions and shuffled history donors with the same index stayed together.
An additional inner split selected the parameters and the best model within
each set. The outer test choices were not used for that selection.

The primary score covers rounds 2 to 20 with own history, giving stable and
swap conditions equal weight. Lower prediction loss is better. Accuracy is
agreement with the model's selected frame, not the target's Option A rate.

## Results

| Run | Simple set loss | Belief set loss | Simple accuracy | Belief accuracy |
| --- | ---: | ---: | ---: | ---: |
| V4, original Qwen | 0.4973 | 0.5128 | 80.9% | 79.9% |
| R1, Gemma | 0.2017 | 0.1750 | 94.4% | 95.6% |
| E1, stated probabilities | 0.2127 | 0.2118 | 93.7% | 93.5% |
| P1, reworded Qwen | 0.7338 | 0.7368 | 68.6% | 67.4% |

### Original Qwen

Reward learning was selected in all five outer folds. Its loss was 0.0155
nats per choice lower than the selected dynamic belief model. The descriptive
95% interval for simple minus belief loss was [-0.0249, -0.0076].

This is a small advantage, about one percentage point in accuracy. It is not
evidence that we have recovered Qwen's algorithm. It is enough to show that
an explicit partner type model did not improve prediction in this comparison.

The same direction appeared in the valid response subset and in the planned
post swap summary. Reward learning also had lower mean loss in all six
directed post swap groups. Those subgroup differences are descriptive, not
six separate discoveries. The complete intervals remain in the tables.

The selected reward learner used alpha = 0.1 in every fold: each observed
outcome shifted the chosen frame's estimated reward by 10% of its prediction
error. It also used frame preferences and repetition. Alpha was at the lowest
tested grid value, so it is not a precise estimate of a psychological learning
rate. The selected dynamic belief model likewise used the lowest nonzero
hazard in its grid. I did not expand either grid after seeing the scores.

### Gemma

The static belief model was selected in all five folds. It had lower loss than
the selected simple set by 0.0267 nats, with a descriptive interval of
[0.0082, 0.0497] for simple minus belief loss.

There is an important qualification. The simple set switched between reward
learning and history frequency across folds. The individual reward learning
family scored 0.1792, close to the static belief family's 0.1750. The larger
primary gap partly reflects the simple set's unstable family selection. We
cannot replace that primary comparison with whichever family looks best on
the test scores, but we also should not hide the instability.

The belief model included a strong repetition term and a strong expertise
preference. Its success at predicting choices does not establish a belief
inside Gemma. Gemma's original learning and revision tests still failed.

### Stated probabilities and reworded Qwen

E1's selected sets differed by only 0.0009 nats. P1 differed by 0.0030 nats in
the other direction. Both descriptive intervals included zero. This does not
establish equivalence. It means these comparisons do not separate the models
clearly with this analysis.

P1 still contains 733 invalid responses replaced by the frozen fallback rule.
Its valid response subset moved the difference to approximately +0.0003 nats.
That subset is not an unbiased correction: failed selections also affect
later histories. P1 remains a failed validity checkpoint.

E1's baselines did not use the past stated probability vectors that the LLM
saw. Its result is therefore a comparison under a restricted feature set,
not a complete account of the information available to that model.

## What remains uncertain

These are predictions of recorded choices given the recorded past. They are
not simulated deployments of the baselines. A baseline choosing a different
message would create a different later history, which this analysis does not
measure.

The baselines were given explicit frame categories. The belief models also
knew the simulator's true response likelihoods. The focal model was not given
either piece of information explicitly. These are useful reference models,
not fully information matched competitors.

The held out units were seed bundles, not entirely new scenario identities or
message templates. The original results were already known when this analysis
was designed. This work is exploratory.

The intervals resample seed bundles while holding fitted predictions fixed.
They omit uncertainty from retraining, and overlapping training folds may
correlate predictions. They are descriptive, not confirmatory significance
tests. No rows or outliers were removed to improve the result.

## What we should do next

The next useful step is a small test that makes the two explanations disagree.
Another broad run of the same task would not resolve this issue by itself.

Use the fitted rules to find pairs of histories where their predicted next
choices differ. Control obvious cues such as the last message category, recent
success, history length and expertise preference. Check that known synthetic
policies can be distinguished under the proposed design, then calculate power
before collecting any new model outputs. The diagnostic design must be fixed
before those outputs are inspected.

If that test cannot distinguish the explanations within a sensible budget,
we should keep the project's claim at behavioural adaptation and document the
limit. If it can, it gives us a focused reason for another small experiment.
Neither outcome removes the unfinished human validation gate or justifies
activation probing and steering yet.

No new paid experiment has been started or approved by this analysis.
