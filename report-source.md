# LatentTarget research and design audit

Audience: project researcher and future workshop reviewers  
Date: 2026-08-25  
Scope: scientific positioning, literature verification, current-model choice,
and the pre-GPU evidential standard. No paid model or real GPU result is used.

## Executive answer

LatentTarget is worth running, but its publishable contribution is not the
simple observation that a model repeats successful persuasion frames. The
defensible contribution is a controlled test of **dynamic user-model revision**:
after a silent change in the same interaction partner, do internal evidence,
decodable state, and outward strategy change on different timescales, and does
intervening on a probe-derived direction causally change the strategy?

The apparatus is now strong enough to test that question without making a
positive result inevitable. The main remaining scientific blocker is empirical:
no real open-weight model has been run. The eight-seed run should therefore be
treated as a GO/NO-GO and variance pilot. It cannot, by itself, support a strong
null or a precise population claim.

## Where this sits in the literature

Chen et al.'s 2025 workshop paper, *What Kind of User Are You?*, is the closest
model-biology anchor. Its public abstract reports linear directions for inferred
user attributes in chatbot residual streams, causal mediation, and steering.
LatentTarget should not claim novelty for “user information is linearly
decodable.” Its narrower contribution is outcome-only inference that must be
revised online after an unannounced change, with evidence-only and behavioral
baselines. [ICML virtual paper page](https://icml.cc/virtual/2025/49559)

GLEE provides a benchmark for sequential language-based bargaining,
negotiation, and persuasion, with economic outcome measures. Its latest arXiv
record is version 3, updated March 2, 2026. LatentTarget is intentionally not a
GLEE leaderboard agent: it removes strategic-game complexity to isolate one
latent variable and its update dynamics. [GLEE v3](https://arxiv.org/abs/2410.05254)

Raifer et al. built an automatic agent for repeated language-based persuasion
using receiver-action prediction, linguistic signals, future-payoff prediction,
and Monte Carlo tree search. That is strong precedent for adaptive repeated
persuasion, but not an internal-representation study and not a silent target-
identity swap. [TACL paper](https://aclanthology.org/2022.tacl-1.18/)

Matz et al. found that generative-AI messages personalized to measured
psychological characteristics were more persuasive than unmatched messages in
their human studies. That supports the importance of matching messages to
recipient characteristics, but does not show that a language model autonomously
infers and updates such characteristics from repeated binary feedback.
[Scientific Reports](https://www.nature.com/articles/s41598-024-53755-0)

## Audit of the ten-paper GLEE strategy list

The bibliography is mostly real and relevant to GLEE, but several competitive
“policies” in the pasted summary are implementation extrapolations, not results
proved by the cited papers. They should not be represented as direct theorems.

| Paper | Metadata check | What is safe to say | Important boundary |
|---|---|---|---|
| Rubinstein (1982), *Perfect Equilibrium in a Bargaining Model* | Econometrica, DOI [10.2307/1912531](https://doi.org/10.2307/1912531) | Characterizes stationary subgame-perfect alternating-offer bargaining under discounting. | Exact GLEE offers require matching horizon, information, and utility assumptions. |
| Rubinstein (1985), incomplete information about time preferences | Econometrica, DOI [10.2307/1911016](https://doi.org/10.2307/1911016) | Hidden patience can affect signaling and bargaining dynamics. | The discrete Bayesian filter in the pasted text is an engineering translation, not a quoted algorithm. |
| Ochs & Roth (1989), sequential bargaining experiment | AER 79(3), indexed without a DOI by OpenAlex | Documents systematic experimental departures from simple equilibrium predictions. | “Use aggressive anchors against conciliatory language” is not established by this paper. |
| Myerson & Satterthwaite (1983) | JET, DOI [10.1016/0022-0531(83)90048-0](https://doi.org/10.1016/0022-0531(83)90048-0) | Establishes an impossibility result for efficient bilateral trade under private information and standard constraints. | It is a guardrail, not an offer-generation policy. |
| Chatterjee & Samuelson (1983) | Operations Research, DOI [10.1287/opre.31.5.835](https://doi.org/10.1287/opre.31.5.835) | Studies bargaining under incomplete information with type-dependent strategies. | Its protocol is not GLEE's alternating-offer protocol. |
| Riley & Zeckhauser (1983) | QJE, DOI [10.2307/1885625](https://doi.org/10.2307/1885625) | Under its assumptions, commitment to a price can dominate haggling. | It does not prove that a fixed or “firm” schedule is generally optimal in repeated bilateral GLEE games. |
| Bergemann & Schlag (2011) | JET, DOI [10.1016/j.jet.2011.10.018](https://doi.org/10.1016/j.jet.2011.10.018) | Studies robust pricing under uncertainty about demand. | A minimax-regret solver needs an explicitly defined ambiguity set; generic random pricing is not the result. |
| Crawford & Sobel (1982) | Econometrica, DOI [10.2307/1913390](https://doi.org/10.2307/1913390) | Information transmission depends on preference alignment; equilibria may partition information. | Cheap talk is not always babbling. Babbling is a specific equilibrium/parameter conclusion. |
| Kamenica & Gentzkow (2011) | AER, DOI [10.1257/aer.101.6.2590](https://doi.org/10.1257/aer.101.6.2590) | Formalizes optimal information design by a sender who can commit to a signal policy. | The pasted binary “deception budget” formula belongs to a special model; GLEE sellers lack formal commitment. |
| Best & Quigley (2024) | JPE, DOI [10.1086/727282](https://doi.org/10.1086/727282) | Shows how long-run reputational incentives can sustain informative persuasion. | Endgame defection is a theoretical prediction under specified reputational dynamics, not a universal LLM behavior. |

The extra Raifer et al. citation is correct; Crossref reports DOI
[10.1162/tacl_a_00462](https://doi.org/10.1162/tacl_a_00462), not
`10.1162/tacl_a_00443`.

## Why the design changed

The behavioral environment was not discarded. It became the first layer of a
stronger model-biology study. A pure leaderboard agent asks, “Can economic
theory improve score?” The current study asks, “What target-specific state does
the model infer, how does that state update, and does it drive behavior?” This
shift reduces game-specific confounds and creates falsifiable internal and
causal tests. It also prevents a generic prompted-agent implementation from
being mistaken for a scientific result.

## Consequential design decisions

1. **Known ground truth first.** A controlled target is artificial but makes
   latent identity and evidence likelihood exact. An LLM target would improve
   ecological validity while weakening identifiability; it is a replication,
   not a replacement for the controlled experiment.
2. **All six ordered swaps.** Earlier code associated swap partner with scenario
   index. Full counterbalancing removes that accidental pair/scenario link.
3. **Evidence-only comparator.** A residual probe can merely decode the outcome
   history written in the prompt. The Bayesian observer sets the strongest
   transparent baseline under the simulator assumptions.
4. **Honest probe test.** Layer and L2 selection happen on train/dev episodes;
   test episodes are untouched. Only full-history stable episodes enter fitting.
5. **Trajectory, not first crossing.** A chance three-way probe “crosses” early
   by noise. The baseline-corrected trajectory statistic does not turn random
   flicker into an apparent lead.
6. **Causal intervention.** Probe-derived steering, with zero/opposite/random
   controls and paired seeds, asks whether the readout direction controls the
   output. A positive result remains local to the tested intervention.

## Evidence-gap matrix

| Claim needed | Current evidence | Confidence | Remaining action |
|---|---|---:|---|
| Current loader matches primary model | Official Qwen model card and Transformers 5.12 docs specify processor/multimodal loading | Medium until execution | Run one-generation preflight on rented hardware. |
| Model behavior adapts to target-specific feedback | Mock agents only | None for real LLMs | Run GO/NO-GO; inspect complete transcripts. |
| Classifier measures framing independently | Blind interface and human-audit tooling exist | Medium for architecture, none for real messages | LLM-judge pass plus blinded human sample. |
| Probe contains information beyond prompt evidence | Honest split and baselines implemented | None empirically | Capture activations; compare held-out probe with transcript and Bayesian baselines. |
| Probe direction causally controls strategy | Hook and paired controls pass local tests | None empirically | Run preregistered steering grid on untouched prompts. |
| Finding generalizes beyond one simulator/model | No data | None | Replicate seeds/parameters/model generation only after primary result. |

## Recommendation

Do not add another environment before the GO/NO-GO. Run the official current
dense model through the preflight, then the smallest transcript-readable pilot.
If valid history does not directionally outperform no history, inspect the
failure and run at most one preregistered easier-target sensitivity. If behavior
does adapt, complete the judge/human audit, freeze sample size from episode-level
variance, then run activations, probe, and steering. The project becomes strong
through honest negative controls and causal evidence, not through more code.

## Claim-to-source ledger and retrieval provenance

| Claim | Source | Access/provenance |
|---|---|---|
| User attributes can be linearly decoded and steered in chatbot residual streams | Chen et al., ICML 2025 Actionable Interpretability workshop, [paper page](https://icml.cc/virtual/2025/49559) | Official conference page accessed 2026-08-25. OpenReview API was blocked by a challenge, so the public abstract—not unavailable full text—supports the summary. |
| GLEE defines sequential language-based economic game families | Shapira et al., [arXiv:2410.05254v3](https://arxiv.org/abs/2410.05254) | arXiv Atom API `id_list=2410.05254`; 1/1 record retrieved; v3 updated 2026-03-02; accessed 2026-08-25. |
| Repeated language persuasion agents have been built with predictive/planning components | Raifer et al., [ACL Anthology](https://aclanthology.org/2022.tacl-1.18/) | Official ACL Anthology and Crossref title lookup; DOI 10.1162/tacl_a_00462; accessed 2026-08-25. |
| Matched AI-generated persuasion can outperform unmatched messaging in human studies | Matz et al., [Scientific Reports](https://www.nature.com/articles/s41598-024-53755-0) | OpenAlex bounded search (10 of 10,482 returned; discovery only) resolved DOI and official OA article; accessed 2026-08-25. |
| Primary model identifier/loading family | Qwen, [Qwen3.8-27B model card](https://huggingface.co/Qwen/Qwen3.8-27B); Hugging Face, [Qwen 3.5 docs](https://huggingface.co/docs/transformers/v5.12.0/en/model_doc/qwen3_5) | Official model/documentation pages accessed 2026-08-25. Actual loading remains GPU-blocked. |
| Economic-paper metadata | Crossref DOI API and OpenAlex exact-title queries | Targeted Crossref/OpenAlex calls on 2026-08-25. Ochs & Roth had no DOI in the retrieved OpenAlex record. No exhaustive citation search was attempted. |

Stopping rule for research: targeted primary/official sources covered every
consequential positioning claim; further broad search was unlikely to alter the
pre-GPU design. The OpenAlex discovery query was deliberately bounded to ten
results and was not treated as exhaustive.
