**Problem.** Chen et al. showed LLMs model static user attributes. I asked the dynamic version, in persuasion: given only a goal and a yes/no outcome each round, does a model learn which kind of argument this partner responds to, revise when the partner silently changes, and hold any belief about the partner that is separate from its choice? A persuader that models and updates on its target is a different safety problem from one with a fixed style.

**Takeaways.**
- Qwen3.8-27B learns which argument frame works, from outcomes alone, on unseen wording, and the effect survives rewording the prompt. Controls rule out "any history helps" and "the partner is not really responding".
- After a silent switch it moves toward the new frame but never past the old one, and the movement follows its default frame: 34 of 40 switches into expertise adapted, 9 into risk, 0 into fairness.
- Two stress tests break the stronger reading. Gemma-4-31B shows no learning under the identical design. Forcing Qwen to state a probability per message removes the learning, and its stated belief and its choice were identical in 3,600 of 3,600 records.

**Setup.** Each of 20 rounds shows three unlabelled candidate messages, one per frame (fairness, risk, expertise), and the model answers 1, 2, or 3. A simulated partner picks A with probability 0.72 if the frame matches its hidden type, else 0.38. "Match" means the chosen frame equals the partner's type; chance is 1/3. Rounds 16 to 20 use held-out wording. In swap episodes the type changes silently after round 10. Conditions: own history, no history, shuffled history (another episode's transcript), random partner, swap. 360 episodes and 7,200 choices per run. Thresholds and seeds were frozen before each run, which was analysed once.

**Experiment 1, learning (V4).** With its own history the held-out match rate rose from 0.383 to 0.570. Learning gain (late held-out minus early) was 0.187 [0.083, 0.290] and the randomization test against no history passed. No history stayed at 0.333, shuffled history fell to 0.233, random partner was flat. Learning is anti-default: with no history the model picks expertise 0.922 of the time, and the gains come on fairness (0.24 vs 0.05) and risk (0.61 vs 0.10) partners.

[FIG: fig_w1_v4_learning_by_condition.png] Figure 1. V4, Qwen3.8-27B: match rate by round, four stable conditions; grey band is held-out wording.

**Experiment 2, revision (V4 swap).** After the switch, new-frame use rose 0.108 and old-frame use fell 0.105, both past the 0.10 thresholds, but the new frame never overtook the old (difference 0.000, p = 0.50), so the registered revision test failed.

[FIG: fig_w2_v4_swap_by_transition.png] Figure 2. V4 silent swap: change in new-frame and old-frame use per transition, with the number of episodes that adapted.

**Experiment 3, three stress tests, predictions written before each outcome.** Reworded prompt, same Qwen: replicates, gain 0.207 [0.110, 0.307], p = 0.0002 against no history. Gemma-4-31B, same design: gain 0.040 [-0.007, 0.093]; it repeats its frame 0.972 after a success and 0.941 after a failure (Qwen 0.876 vs 0.693). Same Qwen forced to state a probability per candidate: gain -0.020 [-0.053, 0.010]; its choice was the argmax of its stated probabilities in every record, and its stated confidence was a fixed ranking (expertise 0.69 > risk 0.58 > fairness 0.49) that never changed the choice.

[FIG: fig_w11_whole_story.png] Figure 3. With-history match rate by round: V4, reworded prompt, Gemma, and Qwen forced to state beliefs. Dashed: V4 no history.

**Reading.** A real, wording-robust behavioural effect on one model. No evidence of a partner model separate from the choice: I have not ruled out a model-free policy, repeat what worked and otherwise fall back to expertise, plus a strong default.

**Limitations and next.** Simulated partner with a fixed rule; choice among pre-written messages; one positive model of two; the elicited arm changed output format and history at once, and its prompt was never tuned. Next: a third model, a two-frame design plus a distractor to remove the default, an elicited arm with predictions hidden, and probes only if an effect survives all three.

**Process.** Four redesigns to remove the default stopped at pass/fail rules I wrote down before their outcomes. Nearly all code was AI-written; the design, rules, stops, and checks were mine (listed after the examples). [CONFIRM in your words]
