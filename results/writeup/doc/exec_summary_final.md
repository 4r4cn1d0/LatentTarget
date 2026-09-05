**Problem.** Chen et al. showed LLMs form accurate models of static user attributes. I asked the dynamic version, in the setting where it matters most: persuasion. Given only the goal "get Option A chosen" and a yes/no outcome each round, does a model learn which kind of argument this partner responds to, revise when the partner silently changes, and hold any belief about the partner that is separate from its choice? A persuader that models and updates on its target is a different safety object from one with a fixed style.

**Takeaways.**
- Qwen3.8-27B learns which frame works, from outcomes alone, on unseen wording, and the effect survives rewording the prompt. Three controls rule out any-history and a partner that ignores it.
- It does not revise after a silent switch, and the reason is a strong default frame (expertise) rather than a partner model.
- Two stress tests break the stronger reading: Gemma-4-31B shows no learning under the identical design, and forcing Qwen to state a probability per message removes the effect entirely. Its stated belief and its choice were the same object in 3,600 of 3,600 records.

**Setup.** Each of 20 rounds shows three unlabelled candidate messages, one per frame (fairness, risk, expertise); the model answers 1, 2, or 3. A simulated partner picks A with probability 0.72 if the frame matches its hidden type, else 0.38. Rounds 16 to 20 use held-out wording; swap episodes change the type silently after round 10. 360 episodes and 7,200 choices per run. Thresholds and seeds were frozen before each run and each arm was analysed once.

**Experiment 1, learning (V4).** With its own history the held-out match rate rose from 0.383 to 0.570; learning gain 0.187 [0.083, 0.290], randomization test passed. No-history stayed at 0.333, shuffled history fell to 0.233, random target was flat. Learning is anti-default: expertise is chosen 0.922 of the time with no history, so the gains come on fairness (0.24 vs 0.05) and risk (0.61 vs 0.10) targets.

[FIG: fig_w1_v4_learning_by_condition.png] Figure 1. V4, Qwen3.8-27B: match rate by round, four stable conditions; grey band is held-out wording.

**Experiment 2, revision (V4 swap).** The registered test failed. Adaptation ran only toward the default: 34 of 40 swaps into expertise, 0 of 40 into fairness. New-frame gain and old-frame drop were symmetric at 0.24.

[FIG: fig_w2_v4_swap_by_transition.png] Figure 2. V4 silent swap: change in new-frame and old-frame use per transition, with adapted counts.

**Experiment 3, three stress tests, predictions declared before each outcome.** Reworded prompt, same Qwen: replicates, gain 0.207 [0.110, 0.307], p = 0.0002 against no-history. Gemma-4-31B, same design: gain 0.040 [-0.007, 0.093]; it repeats its frame 0.972 after a success and 0.941 after a failure (Qwen 0.876 vs 0.693). Same Qwen forced to state a probability per candidate, with its past predictions shown in its history: gain -0.020 [-0.053, 0.010]; choice equals the argmax of its stated probabilities in every record; stated confidence is a fixed ranking (expertise 0.69 > risk 0.58 > fairness 0.49) that moves about 0.05 with feedback and never changes the choice.

[FIG: fig_w11_whole_story.png] Figure 3. With-history match rate by round: V4, reworded prompt, Gemma, and Qwen forced to state beliefs. Dashed: V4 no-history.

**What this supports.** A real, wording-robust behavioural effect on one model, with no evidence of a separable partner model. A model-free policy, repeat what worked and otherwise fall back to expertise, fits every result.

**Limitations and next.** Simulated partner with a fixed rule; choice among pre-written messages; one positive model of two; the elicited arm changed format and history at once. Next: a third model, a two-frame design with a distractor to kill the default, an elicited arm with predictions hidden, and probes only if an effect survives all three.

**Process.** Four redesigns to remove the default stopped at gates I wrote down first. Nearly all code was AI-written; the design, gates, stops, and checks were mine (listed after the examples). [CONFIRM in your words]
