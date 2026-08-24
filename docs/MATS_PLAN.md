# Scoping this against the MATS 12.0 application

Deadline **Fri Sept 4, 11:59pm PT** (extensions to Sept 11). Today is 2026-08-19.
Budget: **~16h (max 20h) of active project work, +2h for the write-up.**

---

## 1. Is this a problem Neel is interested in? Yes — it's on his list

From *Recommended Research Problems → Model Biology → Interesting phenomena*:

> **User models**: Chen et al shows that LLMs form surprisingly accurate and
> detailed models of the user... They can find these with **probes**, and
> **steer** with these to change the model's actions in weird ways.
> - **Do LLMs form dynamic models of users for attributes that vary across
>   turns**, eg emotion, what the user knows, etc.
>   - As a stretch goal, **do LLMs ever try to intentionally manipulate
>     these?**

That is this project, almost word for word. Problem choice is not the risk here.

**Two things in that bullet we are currently not doing**, and both are the part
he flags as interesting: *probes* and *steering*. Chen et al. is the anchor
paper and we have not read it — that needs doing before any write-up. (Our
[RELATED_WORK.md](RELATED_WORK.md) sweep missed it; it was not in the queries
we ran.)

## 2. The main risk: "purely behavioural"

From his own notes on a past application (*What Impacts CoT Faithfulness*,
which he scored "higher end of borderline accept"):

> It was **purely behavioural**, while most applications were mechanistic, and
> mechanistic work is slower, so I would have expected more output from a
> strong application.

Also listed under common mistakes: **"Doing a very common/generic type of
project"** — with *"showing that a safety-related concept has a linear
representation"* given as the example of generic.

So the two failure modes are symmetric:
- **Behaviour only** → "nice, but purely behavioural, and I'd have expected more."
- **Probe only** → "you showed a concept is linearly represented. So does everything."

The thing that is neither: **compare the two.** Does the model's *internal*
estimate of the target revise at the same rate as its *behaviour* does after the
silent swap? A dissociation in either direction is a real finding:

- probe updates **before** behaviour → the model knows the user changed and
  keeps using the old strategy anyway. That's a sticky-policy result, and it is
  directly a monitoring story: you could catch the stale model before the
  behaviour reveals it.
- behaviour updates **before** the probe → the behavioural adaptation is
  model-free bandit-like updating and there is no latent user model doing work.
  That's a negative result about "latent user models", and a clean one.

Either outcome is publishable-shaped, which is the property you want under a
hard time limit. A null on the probe is also fine and must be reported as such.

## 3. What this implies for the model

The provider abstraction supports APIs, but the preregistered probing subject
is open weight.

From the doc's recommended-resources tab, cross-checked against the HuggingFace
API on 2026-08-19:

- **`Qwen/Qwen3.8-27B`** — newest official dense release verified as of
  2026-08-25,
  the primary subject.
- A second model is out of the scoped run. If later needed, verify the current
  open-weight landscape again and choose a then-current independent model,
  rather than an old small checkpoint selected only for cost.
- Two ID/loading traps: **no `-Instruct` suffix**, and these are multimodal
  (`Qwen3_5ForConditionalGeneration`), so the current official path uses
  `AutoProcessor` plus `AutoModelForMultimodalLM` rather than relying on
  `AutoModelForCausalLM`.
- Listed as a mistake: **only studying old models (GPT-2, Pythia, Gemma 2)**.
  `pythia-410m` from the other project in this workspace is not an option here.
- The paired mistake, equally listed: **"working with a model that's just way
  too dumb for the task"** — which is why the subject is 27B, not 4B.
- `nnsight` or plain PyTorch hooks. Rent a GPU (runpod/vast) — **generic GPU
  setup does not count against the 20 hours.**

**Prerequisite, non-negotiable:** *"Trying to investigate some phenomena without
checking if it's really there"* is a listed mistake. Before any probing, check
that the chosen open-weight model **actually adapts behaviourally** in this
environment. If Qwen3.8-27B doesn't shift its framing in response to feedback,
there is no latent belief to decode and the project pivots or dies. That check
is ~1 hour and comes first.

## 4. Honest scope call

The infrastructure built so far is more than a 20-hour application needs. That
is a real cost already paid, not a reason to use all of it. Recommended cuts:

| keep | cut / park |
|---|---|
| `full_history` (main) | `mismatched_feedback` (redundant with `shuffled_history`) |
| `no_history` (Control 1) | The 5-condition × 3-type × 20-episode full matrix |
| `shuffled_history` (Control 2) | Judge-vs-scorer disjoint-lexicon sweep |
| `random_target` (Control 5) | Target-parameter robustness sweep (unless time remains) |
| `swap` (the point) | The `mismatched_feedback` analysis paths |

Statistics: keep bootstrap CIs and the two permutation tests. The
cluster-robust logistic regression is already written so it costs nothing, but
don't build more — *"Do not introduce complicated statistics unless justified"*
is your own instruction and it agrees with his *"Simplicity"* criterion.

## 5. Rough hour budget (only you can fill in the actual numbers)

| # | block | est. hours |
|--:|---|--:|
| 1 | Environment + controls + analysis (**already built**) | ? — you were directing, only you can count it |
| 2 | Read Chen et al. + 2-3 adjacent papers | 1.5 |
| 3 | Tiny API pilot, read every transcript by hand | 1.0 |
| 4 | Open-weight behavioural replication (does Qwen adapt at all?) | 2.0 |
| 5 | Blind hand-labelling of ~40 messages + judge agreement | 1.0 |
| 6 | Activation capture + linear probe for target type, w/ baselines | 4.0 |
| 7 | Probe-vs-behaviour dynamics across the swap (**the result**) | 3.0 |
| 8 | Red-teaming your own result (see checklist) | 2.0 |
| 9 | Figures + write-up | 2.0 (+2h exec summary) |

Track it with Toggl from now on — he encourages a screenshot with the doc.
*General prep, GPU setup, breaks, and waiting for jobs to finish do not count.*

## 6. The part I can't do for you

Two of his rules bear directly on how this project has been run so far:

> An application that is clearly "an agent did a project and a human forwarded
> it to me" will be rejected; I can get that myself, in twenty minutes, for free.

> Please do not just submit raw LLM output for the application form or executive
> summary. Write these yourself, in your own voice.

He also notes applicants who used agentic tools were accepted at **~3x** the
rate — so the tooling is an edge, conditional on you staying in control of it.
Concretely that means:

- **The experimental design, controls and interpretation should be yours.** Push
  back on my choices. Several are arguable: the `share × intensity` scoring rule
  builds the specialisation incentive into the environment by fiat; the three
  target types are a categorical stand-in for something continuous; the keyword
  target rewards surface lexical features.
- **You read the raw data.** [VERIFICATION_CHECKLIST.md](VERIFICATION_CHECKLIST.md)
  is the concrete list, ordered by leverage.
- **You write the exec summary and the form answers.** I'll draft figures,
  tables and technical description; the prose and the claims are yours.
- **Document what you verified.** *"I read 30 transcripts and confirmed X"* is,
  in his words, strong evidence of research skill. The checklist is designed to
  make that sentence true and specific.
