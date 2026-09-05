# Latent Target Writeup

- Document ID: 1n42djKj_BI6uJdwVk2bNp-0n1fIrwgjdv_AmNqIGBUo
- Revision ID: unavailable
- Selected tab: t.0
- Protected controls: 0
- Opaque controls: 0
- Authoritative dropdowns: 0

Protected-control annotations are preservation instructions. Do not insert their displayed placeholder text to recreate a native control.

## Tab 1 (t.0)

[P00001 | 1:82 | TITLE]
LatentTarget: do LLMs learn which persuasion frame a hidden partner responds to?

[P00002 | 82:292 | NORMAL_TEXT]
Aayush (Rishi) Ghosh · MATS 12.0 application · repository: github.com/4r4cn1d0/LatentTarget · every number below is generated from committed artifacts by scripts/make_writeup_materials.py and names its source.

[P00003 | 292:293 | NORMAL_TEXT]
⟦EMPTY PARAGRAPH⟧

[P00004 | 293:311 | HEADING_1]
Executive summary

[P00005 | 311:652 | NORMAL_TEXT]
Question. I asked whether an LLM, told only to get Option A chosen and given binary feedback, learns which persuasion frame a hidden partner responds to, and whether it revises that when the partner silently changes. I ran it as a preregistered study: thresholds frozen before data, each real run analysed once, a failed gate stops the arm.

[P00006 | 652:1147 | NORMAL_TEXT]
Design. The focal model is Qwen3.8-27B (open weights). Each round it sees three unlabelled candidate messages, one per frame (fairness, risk, expertise), and replies with a digit. The hidden target picks A with probability 0.72 if the frame matches its type and 0.38 otherwise. The type is swapped silently after round 10, and rounds 16 to 20 use held-out wording. Three controls: no-history, shuffled-history from another target, and a random target. One run is 360 episodes and 7,200 choices.

[P00007 | 1147:1798 | NORMAL_TEXT]
Positive result. With its own history, the match rate rose from 0.383 in early rounds to 0.570 on held-out rounds. No-history stayed at 0.333, shuffled-history fell from 0.287 to 0.233, and random-target was flat. The learning gain was 0.187 [0.083, 0.290], and the registered randomization test passed. Learning was anti-default. Expertise is the default (0.922 of no-history picks), so gains against no-history came on fairness (0.24 vs 0.05) and risk (0.61 vs 0.10) targets. The preregistered revision test failed. After a swap the model re-acquired expertise in 34 of 40 episodes and fairness in 0 of 40. That is default attraction, not updating.

[P00008 | 1798:3075 | NORMAL_TEXT]
Stress tests. I then declared three arms, each with its predictions written before its own outcome, and ran the frozen design once per arm. Gemma-4-31B-it does not replicate: gain 0.040 [-0.007, 0.093]. It makes the same choice as with a shuffled history 90.5% of the time (Qwen 63.7%) and repeats a frame 0.972 after a success versus 0.941 after a failure (Qwen 0.876 versus 0.693). It barely uses history or feedback. Asking Qwen to state a probability per candidate before choosing, with those predictions shown back in its history, removed the effect: gain -0.020 [-0.053, 0.010]. In 3,600 of 3,600 records the choice was the argmax of the stated probabilities: belief and choice were one object. Rewording the spontaneous prompt reproduced the effect: gain 0.207 [0.110, 0.307], same anti-default pattern. That arm still failed the revision gate, as predicted, and a validity gate (0.898 against 0.98). About 10% of history rounds began a reasoning preamble and were truncated, and the random fallback dilutes learning (parsed-only late match 0.632 versus 0.600). My conclusion: a real but narrow effect for one model under this task. It is robust to wording, absent in Gemma, absent under belief elicitation, and has no stated belief separate from the choice (Figure 1).

[P00009 | 3075:3763 | NORMAL_TEXT]
Process. Four successors, V5 through V8, each stopped at a gate I had written down first. V5's calibrated bank could not be balanced. V6's balance gate was infeasible at every allowed N. V7 failed its own feasibility rule, and an adversarial review showed its pooled revision rule would pass on pure default attraction. V8 controlled Type I error but was underpowered against the weakest registered learner. I also withdrew a planned first-crossing "probe leads behaviour" metric: in simulation a chance-level probe appears to lead by 0.91 rounds, CI excluding zero in 87% of runs. I used AI for code. The gates, stops and readings are mine. [CONFIRM this sentence is true in your words]

[P00010 | 3763:4060 | NORMAL_TEXT]
Next. A larger token budget to recover the truncated paraphrase rounds. A third model under the spontaneous prompt, to separate "Qwen" from "feedback-sensitive". Human labels for the message bank (a 45-template blind sheet exists). Only then a probe, and only on an effect that survives revision.

[P00011 | 4060:4062 | NORMAL_TEXT]
[INLINE_OBJECT kix.kkaj72metvo6]

[P00012 | 4062:4447 | NORMAL_TEXT]
Figure 1. Match rate by round with the model's own history. Left to right: Qwen3.8-27B under the V4 prompt (learns); the same model under a reworded prompt (Arm P1, still learns); Gemma-4-31B under the identical design (Arm R1, flat); the same Qwen forced to state a probability per message before choosing (Arm E1, flat). Dashed: V4 no-history reference. Grey band: held-out wording.

[P00013 | 4447:4448 | NORMAL_TEXT]
⟦EMPTY PARAGRAPH⟧

[P00014 | 4448:4449 | NORMAL_TEXT]
⟦EMPTY PARAGRAPH⟧

