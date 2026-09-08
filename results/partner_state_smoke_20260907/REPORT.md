# Partner study offline screen

Status: **SMOKE_ONLY**.

These are mathematical mock policies and synthetic studies, not LLM results. No paid calls ran.
The original design snapshot and historical scientific gates are unchanged.

## What ran

Prepared 36 confirmation bundles and 864 requests, all undispatched.
Evaluated 13 mock policies on that fixed bank.
Ran 1,200 fresh simulated studies across 12 declared cells.

## Complete decision versus primary tests

A primary pass alone is insufficient. The complete decision also requires three control equivalence intervals and 98% validity in every choice branch.
Monte Carlo intervals describe uncertainty in simulated pass rates, not uncertainty about real LLM performance.

| Scenario | N | Both primary | All controls | Validity | Complete pass [95% MC interval] |
| --- | ---: | ---: | ---: | ---: | --- |
| uniform_null | 36 | 0.000 | 0.000 | 1.000 | 0.000 [0.000, 0.037] |
| global_reward_null | 36 | 0.000 | 1.000 | 1.000 | 0.000 [0.000, 0.037] |
| global_recency_null | 36 | 0.000 | 1.000 | 1.000 | 0.000 [0.000, 0.037] |
| name_bias_null | 36 | 0.000 | 0.000 | 1.000 | 0.000 [0.000, 0.037] |
| belief_full | 36 | 1.000 | 0.000 | 1.000 | 0.000 [0.000, 0.037] |
| belief_half_shared | 36 | 0.990 | 0.060 | 1.000 | 0.060 [0.028, 0.125] |
| belief_half_independent | 36 | 0.950 | 0.000 | 1.000 | 0.000 [0.000, 0.037] |
| belief_half_mcar_1pct | 36 | 0.960 | 0.010 | 0.340 | 0.010 [0.002, 0.054] |
| belief_half_selective_1pct | 36 | 0.980 | 0.000 | 0.850 | 0.000 [0.000, 0.037] |
| belief_mcar_3pct | 36 | 1.000 | 0.000 | 0.000 | 0.000 [0.000, 0.037] |
| feature_reward | 36 | 1.000 | 0.000 | 1.000 | 0.000 [0.000, 0.037] |
| dynamic_belief | 36 | 1.000 | 0.000 | 1.000 | 0.000 [0.000, 0.037] |

![Synthetic sensitivity](power_screen.png)

## Mock policies on the saved bank

One fixed bank per policy. These results test the pipeline and alternative explanations; they are not power estimates.

| Policy | BIND mean | TRANSFER mean | NEAR mean | Complete mock pass |
| --- | ---: | ---: | ---: | --- |
| expertise | 0.000 | 0.000 | 0.000 | False |
| fixed_slot | 0.000 | 0.000 | 0.000 | False |
| name_bias | 0.000 | 0.000 | 0.000 | False |
| uniform | -0.014 | 0.083 | 0.014 | False |
| global_reward | 0.000 | 0.000 | 0.000 | False |
| global_recency | 0.000 | 0.000 | 0.000 | False |
| participant_reward | 0.764 | 0.722 | 0.764 | False |
| participant_recency | 0.528 | 0.611 | 0.528 | False |
| participant_feature_reward | 0.764 | 0.722 | 0.764 | False |
| static_belief | 0.736 | 0.806 | 0.736 | False |
| dynamic_belief | 0.750 | 0.778 | 0.750 | False |
| lexical_retrieval | 0.764 | 0.028 | 0.014 | False |
| typed_history_oracle | 1.000 | 1.000 | 1.000 | True |

## Decision and limitations

Conditional sample candidate: None. This is not permission to deploy.
The required sensitivity scenarios and sample ceiling were written before this screen. No failed scenario was removed.
The finite convolution computes the marginal empirical bootstrap distribution, not exact population coverage. Null rejection rates are separately recorded in power_summary.json.
The mathematical policies have frame annotations and known likelihoods where declared. They do not model a real LLM's language understanding.
Development and confirmation use disjoint aliases, scenario families and exact wording. Semantic family independence and human validity remain unverified.
The additive composite rule remains an assumption. No new model has been selected; no activation experiment is authorized.
Shared versus independent mixture routing and selective invalidity are explicit stress assumptions, not estimates from old LLM results.
All planned requests, mock responses, per-study decisions, plans and hashes are archived. Full event arrays for Monte Carlo studies are deterministically regenerated from the saved config and cell seeds.

This is a smoke run only and cannot select a sample size.
