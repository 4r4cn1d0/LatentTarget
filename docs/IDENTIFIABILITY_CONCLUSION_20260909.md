# What the current simulator can and cannot identify

This conclusion does not depend on the pending presentation diagnostic. It
follows from the exact response rule already used by the project.

## The claim we can establish

In the current additive task, a belief over the three target types and a
suitable vector of expected rewards contain the same information and produce
the same message predictions. Choice performance alone cannot tell us which
description corresponds to the model's internal computation.

Let `x` contain a message's fractions of fairness, risk and expertise clauses.
These fractions sum to one. Let `b` be any probability distribution over the
three target types. The simulator's predicted probability is:

```text
p(A | x, b) = 0.38 + 0.34 * sum_i b_i * x_i
```

Now define `q_i = 0.38 + 0.34 * b_i`. Then:

```text
sum_i q_i * x_i
  = 0.38 * sum_i x_i + 0.34 * sum_i b_i * x_i
  = 0.38 + 0.34 * sum_i b_i * x_i
  = p(A | x, b)
```

This equality holds for every candidate, including mixtures not shown in the
history. If two policies use these identical predicted probabilities with
the same choice rule, their choice distributions are identical. Adding more
rounds does not remove the equivalence: define `q_t` from `b_t` at each time.

The transformation is also invertible on these vectors:
`b_i = (q_i - 0.38) / 0.34`. This is not a claim that every possible reward
learner is Bayesian, or that the LLM uses either algorithm. It means these
particular internal summaries are two descriptions of the same information.
Recovering one from activations would not, by itself, rule out the other.

This does not make a recipient specific reward representation uninteresting.
It can itself be a compact model of how that recipient responds. Demonstrating
its internal representation, causal use and revision would answer a narrower
but useful version of our original research question. What the equivalence
prevents is distinguishing these two descriptions by prediction accuracy alone,
not studying a target specific predictive state at all.

The requirement that clause fractions sum to one matters. The proof is for
this simulator, not arbitrary environments or human persuasion.

## What follows for the project

We can test operational behavior: does message choice track which participant
received which feedback, does that transfer to new wording, and does it revise
after a change? We can compare predictions from explicitly specified learning
algorithms. We cannot turn success on this assay into a unique mechanistic
interpretation merely by calling one internal vector a belief and another a
reward value.

The original Qwen run showed an increase in target matched choices under its
original prompt. Revision and replication limitations remain. The subsequent
720 choice grounded diagnostic did not produce convincing binding or transfer
relative to simpler baselines. Those are empirical results; the equivalence
above is a separate design limitation. It must not be used to erase either
positive or negative observations.

The final presentation diagnostic asks a narrower question about task access.
Even a positive result there will not remove this limitation. It can tell us
whether a more compact presentation changes behavior and whether recorded
outcomes can be retrieved. It cannot certify a psychological profile or a
unique latent target representation.

## Check of the algebra

An exact rational arithmetic check used all 66 probability vectors whose
three entries are multiples of 0.1 and sum to one, paired with the same 66
candidate vectors. All 4,356 predictions agreed exactly. The inverse mapping
also recovered every belief vector. This made zero model calls. The algebra
above establishes the general equality; the finite check only verifies the
arithmetic implementation on a grid.

The earlier [equivalence implementation](../src/grounded_partner.py) and
[grounded diagnostic findings](RUNPOD_EXTENSION_FINDINGS_20260909.md) retain
the original numerical audit and empirical evidence. No claim here implies
that a latent partner model is absent from the LLM.
