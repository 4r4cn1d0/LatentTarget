# What simpler rules explain the existing choices?

Declared 7 September 2026, before fitting this comparison. The earlier outcomes
have already been inspected. This is an exploratory analysis, not a new
confirmatory result or a preregistration. The original protocols and verdicts
will not change.

## Question

Does a model that explicitly tracks a hidden partner type predict the LLM's
next message choice better than fixed preferences, repetition, or ordinary
reward learning? Better prediction would motivate a more discriminating
experiment. It would not identify a representation inside the LLM. A simple
rule winning would not prove that an internal partner model is absent.

## Data and information boundary

Use all four completed V4 family logs, fitting each run separately. No new
generations, API calls, GPU work, human labels, or raw data publication. The
machine readable companion lists the exact inputs and numerical settings.

Predict the next selected **frame**, not the target's choice or hidden type.
Each predictor receives the frames and A/B outcomes of the exact history the
focal model saw. No history means an empty history. Shuffled history means the
actual donor history, not the recipient's unobserved earlier interactions.
Reject missing donors, ambiguous message mappings, incomplete episodes,
inconsistent histories, and cross seed donor links rather than silently fixing
them. Keep the full logs unchanged.

Frame labels are analyst supplied annotations of visible messages. This gives
the numerical baselines easier semantic access than the LLM had. They do not
receive hidden target type, initial or final type, swap timing, condition,
current or future target feedback, response probability, random draw, or stated
E1 probabilities as predictive features. The belief models know the registered
0.72/0.38 likelihood. That is another advantage not given to the focal model.
They do not know when or whether an episode swaps. E1 is a restricted feature
comparison because its past stated probability vectors are visible to the LLM
but not used by these baselines.

## Models

All models put a fixed 2% mixture mass on a uniform distribution to avoid
infinite log loss. Shared frame preferences are Laplace smoothed frequencies
from training choices only. No parameters are estimated from a test episode.

1. Uniform choices.
2. Fixed expertise preference (before the common lapse mixture).
3. Training frame frequencies, independent of history.
4. Repeat the last visible frame with a fitted strength; otherwise use the
   training frame frequencies. With no history, use those frequencies.
5. Repeat the last visible frame after A, otherwise prefer expertise; mix this
   rule with training frame frequencies at a fitted strength.
6. History frequency: Laplace smoothed counts of prior frame choices, ignoring
   rewards. This checks self consistency beyond just the last frame.
7. Reward learning: start each frame value at 0.5 and update only the chosen
   frame, Q[a] = Q[a] + alpha * (reward - Q[a]). No hidden type is represented.
8. Static belief: start uniformly over three possible target types, update by
   Bayes' rule after each observed reward, never reset.
9. Dynamic belief: the same update, but mix the posterior with a uniform prior
   at a constant fitted hazard between interactions. No special reset at round
   11. The hazard is a probability of uniform redraw, including the same type.

For models 6 to 9 the choice logits are beta * value + prior_power * log(training
frame frequency) + stickiness * last_frame_indicator. Model 6 uses smoothed
history frequency as value. Models 8 and 9 use expected reward 0.38 + 0.34 *
posterior as value. The companion JSON fixes every grid before fitting.

Also evaluate two selected model sets. Select the best simple family and the
best belief family using inner validation only. The primary comparison is
their outer test log loss difference, simple minus belief. Positive means
better prediction from the belief set. Report every individual family too.

## Evaluation

Use five outer folds of the 20 scenario seed indices, four indices per fold.
Use the same deterministic fold assignment in each run. All rounds, target
types, conditions and donor episodes with one episode_index stay together.
The outer training set has 16 indices. Use four inner folds to choose each
family's parameters and the two model set winners. Refit only the smoothed
training frequencies on all outer training choices after selecting parameters.

Fit and select on own history stable and swap conditions only. Give these two
conditions equal weight, despite their different episode counts. The fitting
objective uses rounds 2 to 20. Training frame frequencies use the same rows.
Generate outer test predictions for **all** conditions without refitting on
controls. Round 1 is retained and reported separately, but cannot supply
evidence of feedback use. Every episode receives predictions from models that
were fitted and selected without that episode or its seed bundle.

This holds out seed bundles, not unseen templates, scenario identities, model
checkpoints, or an untouched scientific dataset. The bank and original outcome
patterns were already known. Sequential prediction conditions on the observed
past, not on simulated rollouts of each baseline. It measures imitation of
choices, not how much reward the baseline would earn when deployed.

## Metrics and uncertainty

Primary: multiclass negative log probability of the observed frame, in nats.
Secondary: multiclass Brier score (sum over the three categories) and accuracy
with equal credit across exact probability ties. Save row probabilities and
scores, selected parameters, inner validation losses, and exact fold IDs.

Primary scoring retains all logged selections, including frozen fallback
choices. A separately labelled valid response subset uses the **same fitted
models**. Dropping invalid responses cannot remove their influence on later
history and is not an unbiased correction. Never reinterpret P1 as passing
its original validity gate.

Report each condition, stable target, all six directed swaps, post swap rounds
11 to 20, late rounds 16 to 20, and round 1. Hidden labels are used only for
these outcome summaries, never for prediction or parameter selection. Include
controls even when their prediction errors look inconvenient.

Resample 20 whole seed bundles, paired across models, for 5,000 bootstrap
draws. Give stable and swap conditions equal weight in pooled own history
summaries. Show mean differences and descriptive 95% percentile intervals.
These intervals condition on the fitted cross validation predictions. They
omit uncertainty from retraining, and overlapping training folds can correlate
predictions. They are not confirmatory hypothesis tests. No significance gate,
equivalence claim, new p values, or multiple subgroup discovery claims.

Check completeness, finite normalized probabilities, history chronology, donor
grouping, missingness by condition, and seed level loss distributions. Report
mean, SD, median, range and IQR outliers without removing any observations.
Rows within episodes are dependent, which motivates bundle resampling.
Gaussian residuals and equal variances are not assumed. Do not choose a new
test based on a normality test. Include calibration bins and raw bundle loss
differences in the outputs so prediction errors are inspectable.

## Verification and delivery

Before fitting real data, test analytic Bayes updates, reward updates, empty
history, success and failure rules, exact history reconstruction, probability
normalization, grouped folds, selection isolation, missing data rejection,
fallback scoring, tie handling, and synthetic recovery. Recheck deterministic
outputs after a repeated synthetic run. Record hashes of raw logs, manifests,
this plan, its JSON and the analysis source in the run manifest.

Save a separate report, tables, diagnostic plots, test record and work log.
Update the README with the actual result and one reproduction command. Do not
edit the Google Doc, original result files, or frozen gates in this stage.
Any plan amendment must be dated and explained, not silently substituted.
