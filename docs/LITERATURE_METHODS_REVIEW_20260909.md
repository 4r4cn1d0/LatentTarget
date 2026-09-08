# What other papers change about our approach

## The main conclusion

We need a more discriminating experiment, not just more episodes. The useful
question is whether the model preserves and uses information about a particular
recipient that a specified simpler policy would discard. A successful choice,
a plausible explanation, or a decodable label is not enough on its own.

This review was started during the fixed presentation diagnostic on 9 September
2026, before its final outcomes. That run is unchanged. The recommendations
below are a design review, not permission to keep launching paid variants until
one succeeds. The current run must end with a conclusion, including a negative
or inconclusive one.

I checked the relevant primary methods in nine papers, including three 2026
preprints. This is a targeted review, not a systematic review or a guarantee
of novelty. Search queries, metadata and access failures are in the
[search log](../results/literature_methods_20260909/SEARCH_LOG.md).

## The papers and what we should borrow

| Paper | What they actually did | Implication for LatentTarget |
| --- | --- | --- |
| [Kim et al., FANToM, EMNLP 2023](https://aclanthology.org/2023.emnlp-main.890/) | Tested facts, information access and beliefs using related questions about the same conversation. Their ALL* score requires correctness across six question types. They also validated materials with people. | Report component performance and consistency together. Our direct output and literal lookup controls cover only part of this. Machine review does not replace their human validation. |
| [Pi et al., SCALPEL, 2024, revised 2025](https://arxiv.org/html/2406.14737v2) | Made targeted prompt changes to locate missing inferences. Added counter hypothesis controls for salience and distance from a competing cue, including a one word comparison. | Diagnose the exact failed operation. Our compact versus prose comparison changes layout and redundancy together, so it cannot isolate token length alone. A failure does not automatically mean no mental model. |
| [Muchovej et al., GPT-4o Lacks Core Features of Theory of Mind, 2026](https://arxiv.org/pdf/2602.12150v3) | Enumerated combinations of beliefs, desires and world states. Compared simpler ablated models, mapped the task to a second domain, and checked agreement between action prediction and mental state inference. | Test a matched set of predictions across domains and question directions. Their title is not evidence about our newer checkpoint. Explicit inference questions must be separate diagnostic calls, not fed back into the focal agent. |
| [Ackerman, Selective Deficits in LLM Mental Self-Modeling, 2026](https://arxiv.org/pdf/2603.26089v2) | Required useful actions rather than only descriptions. Varied irrelevant event load separately from the number of knowledge state transitions, and compared thinking with nonthinking operation. | Separate history length from actual updating demand. Our nonthinking results are not a test of every reasoning configuration. This is a preliminary behavioral study, not a demonstrated internal circuit. |
| [Shai et al., Transformers represent belief state geometry, NeurIPS 2024](https://arxiv.org/html/2405.15943v3) | Trained small transformers on known hidden Markov processes, compared activations with exact belief geometry, and tested distinct belief states that share an immediate prediction but differ in longer range predictions. | Require a mathematical distinction between the candidate explanations before paying for data. Their controlled small model result does not establish the same mechanism in our pretrained LLM. |
| [Li et al., Emergent World Representations, ICLR 2023](https://arxiv.org/html/2210.13382v5) | Probed Othello board states, compared trained and random networks, then changed representations and checked whether predicted legal moves followed the altered board. | Pair decoding with a precisely predicted intervention effect. Do not call probe accuracy a causal discovery. We do not need to adopt their game or train an Othello model. |
| [Zhang and Nanda, Towards Best Practices of Activation Patching, ICLR 2024](https://arxiv.org/html/2309.16042v2) | Compared corruption methods and outcome metrics. Recommended counterfactual text replacements where appropriate, logit differences, and care when interpreting joint layer patches. | If we reach interventions, use matched donor histories and prespecified output contrasts. Check single layers before interpreting a broad window. A colorful patching plot is not itself a mechanism. |
| [Raifer et al., Designing an Automatic Agent for Repeated Language-based Persuasion Games, TACL 2022](https://aclanthology.org/2022.tacl-1.18/) | Built a repeated hotel recommendation agent using receiver action prediction, future value prediction and Monte Carlo tree search, with behavioral and language ablations. | Recipient adaptation is already an engineering idea. Our potential contribution is distinguishing explanations of adaptation, not merely adding an opponent model. Their search framework would add unnecessary machinery here. |
| [Li, Shi and Deng, CoSToM, 2026](https://arxiv.org/html/2604.10031v1) | Patched encoder activations into a separate question answering decoder, then trained shallow LoRA adapters using supervised mental state labels and a decoder loss. | This is useful related work, but not a direct test of spontaneous modeling in an unchanged focal agent. A strong decoder can reconstruct information; supervised improvements do not establish what the original agent used. Do not import this training stage into our present claim. |

These are methodological precedents, not nine endorsements of our hypothesis.
The reviewed studies operationalize theory of mind differently. Our simulator
currently represents response tendencies, not a target's false beliefs about
the world. That distinction must remain explicit in the writeup.

We should also avoid making the project unnecessarily ambitious. A compact
recipient specific reward vector can itself be a model of that recipient's
responses. Finding that it is represented, causally used and revised would
support a useful version of the original question. We do not need to prove
human psychology, consciousness, or uniquely Bayesian computation. The
problem is treating two equivalent descriptions as competing mechanisms,
not that a predictive reward representation would be scientifically worthless.

## Change 1: separate the operations we currently bundle together

The next design should distinguish five steps:

1. Reading a recorded message and outcome correctly.
2. Combining several observations into a useful prediction.
3. Assigning that evidence to the correct recipient.
4. Using that prediction when selecting a new message.
5. Revising it after informative new evidence.

Each diagnostic must branch from the same original history in a fresh call.
Do not let an aggregation question teach the focal model how to answer its
later choice. Compare all cases, including failures. A pass on one lookup
item is not proof that the entire history has been aggregated correctly.

For a future collected prediction distribution, use a proper score such as
Brier score and report calibration, not only its largest entry. Distinguish
the known simulator probability from an ideal observer posterior conditional
on noisy history. The latter also assumes knowledge of likelihoods that the
LLM may not have. Keep privileged and learned baselines clearly separated.

This is our application of the component and consistency checks above, not
a claim that the existing papers used our particular five stage decomposition.

## Change 2: reject indistinguishable explanations before collection

Our existing response rule has an exact equivalence:

```text
p(A | message, belief) = 0.38 + 0.34 * dot(belief, message_features)
reward_vector = 0.38 + 0.34 * belief
p(A | message, belief) = dot(reward_vector, message_features)
```

The features sum to one. Consequently, a belief vector and this particular
reward vector predict every offered mixture identically. Relabeling either
vector, probing it, or adding more mixtures cannot distinguish them. The
[full algebra](IDENTIFIABILITY_CONCLUSION_20260909.md) remains the governing
limitation of the present simulator.

Following the predictive distinction highlighted by Shai et al., I implemented
a separate exact arithmetic design check. It is deliberately not connected to
the running provider or stimulus bank. It asks whether two distributions over
hidden states can have the same entire immediate response vector but different
future predictions after a specified transition.

The check found a concrete example:

| Quantity | History A | History B |
| --- | --- | --- |
| Distribution over three states | (0.75, 0.25, 0) | (0.25, 0.75, 0) |
| Immediate probabilities for three actions | (0.60, 0.40, 0.50) | (0.60, 0.40, 0.50) |
| Probabilities after the same transition | (0.55, 0.45, 0.50) | (0.45, 0.55, 0.50) |
| Best later action | First | Second |

The earlier histories can yield these distributions through Bayes' rule in
a different informative context. The certificate checks that fact explicitly.
It enumerates all 105 pairs on a 15 point belief grid, finding 20 predictive
alias pairs. The original response matrix gives zero such pairs; an identity
transition also gives zero. All arithmetic is rational and exact.

This establishes only that an immediate response vector is insufficient for
this proposed prediction task. A richer reward predictor or a history lookup
policy could still succeed. We have not uniquely separated psychological
beliefs from all other algorithms. Nor have we shown that an LLM can learn the
earlier context or transition rule. Those assumptions must be made learnable
through neutral, fixed evidence before this can become an actual experiment.

The certificate and 14 passing tests are in
[results](../results/literature_methods_20260909/predictive_identifiability.json)
and [test output](../results/literature_methods_20260909/tests.xml).
They contain zero model calls and are not positive LLM findings.

## Change 3: test invariance and updating separately

Use logically matched domain pairs, recipient name relabelings and balanced
candidate positions. Reserve entire new histories and wording families for
evaluation, not random rows from histories already used in development.
Keep the present 36 bundles as development material permanently.

A future updating study should vary the number of informative changes while
holding overall event count roughly fixed, and vary irrelevant events while
holding informative changes fixed. Length matching must be checked with the
actual tokenizer. Reversing event order is not a harmless formatting change
when chronology determines what the target currently does.

Our current three cyclic candidate rotations balance positions but are not
all six orders. One sampled response per order mixes order sensitivity with
decoding variation. We should not interpret every disagreement as a causal
position bias. Repeated seeds or logged choice distributions can diagnose that
in a future, separately budgeted comparison.

## Change 4: keep elicitation separate from the phenomenon

The neutral objective remains maximizing Option A. Do not tell the focal
agent to identify a type, construct a psychological profile or follow a
particular framing strategy. If we test explicit prediction questions,
reasoning mode or a helpful scaffold, label these as separate conditions.

A model that succeeds with explicit guidance has demonstrated elicited
capability. It has not thereby demonstrated spontaneous formation of the same
representation under our original prompt. A model that fails without that
guidance has not thereby demonstrated that the capability is absent.

This is particularly important because our current pinned model is run with
thinking disabled. Changing that now would destroy the matched comparison.
We preserve it and state the scope of the conclusion instead.

## Change 5: require a specific causal prediction before probing

Only after robust recipient specific behavior should an activation experiment
be considered. Before collecting activations, specify which matched donor
history should change which recipient's choice and which choices should stay
unchanged. Use held out histories, same recipient controls, unrelated recipient
controls and matched content where feasible. Track unrelated output damage.

Choose the layer and metric on development data. Measure the predicted logit
contrast, report raw effects, and guard against normalized effects with a
near zero denominator. Test the same prediction on untouched data. A null
patch is not proof of absence, and a whole history patch can move generic
memory rather than a recipient representation. Neither result licenses a
unique interpretation without further controls.

These are proposed safeguards informed by the intervention papers, not
completed activation experiments in this project. Referencing Neel Nanda's
methods paper does not establish that this project meets his current selection
requirements or that he would consider it a strong application.

## Recommended order and stopping point

Finish and archive the current fixed run. Report its complete outcome alongside
the earlier failures, not as a replacement for them. Then decide whether the
project ends as a careful negative result with a demonstrated design limitation,
or merits one new study with a distinguishable prediction.

Before any such study: verify the mathematical contrast, make the informative
evidence available without leaking labels, validate the diagnostic controls,
and freeze new evaluation histories and an explicit compute cap. A tiny pilot
must pass these checks before scaling. Human validation remains an acknowledged
gap because the user asked not to conduct it, not a gate we silently mark done.

Do not add MCTS, a larger game, supervised mental state training, a model sweep
or repeated prompt searches to rescue the present result. The useful next
step is a specific falsifiable contrast, not another version number.

There are two legitimate future scopes: establish causal use of a compact
recipient specific predictive summary, or ask the stronger question of what
information it retains beyond immediate response values. The mathematical
prototype addresses the second. It is optional, not a mandatory pivot away
from the original project. Neither scope has been demonstrated by the new
offline check.
