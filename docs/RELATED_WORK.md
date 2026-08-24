# Related work and positioning

Initial broad retrieval: 2026-08-19. Targeted verification updated 2026-08-25.
This remains a discovery-oriented reading list; the narrower, claim-level audit
and source ledger are in [`../report-source.md`](../report-source.md).

---

## Where this project sits

Four literatures touch the question.

**0. Internal user models.** The closest model-biology anchor is Chen et al.,
*What Kind of User Are You? Uncovering User Models in LLM Chatbots* (ICML 2025
Actionable Interpretability workshop). Its public abstract reports residual-
stream linear directions for inferred user attributes, causal mediation, and
steering. The gap for LatentTarget is therefore not generic decodability; it is
dynamic inference from outcome-only feedback and revision after a silent
change. [Official ICML page](https://icml.cc/virtual/2025/49559)

**1. LLMs in repeated strategic interaction.** The closest empirical anchor is
Akata et al., *Playing repeated games with large language models*
(Nat Hum Behav 2025, `10.1038/s41562-025-02172-y`), which puts LLMs in repeated
matrix games and finds systematic failures to coordinate with a changing partner.
A fast-growing agent-engineering strand *builds in* opponent models rather than
testing whether one forms: `2505.08459` (Strategy-Augmented Planning via Opponent
Exploitation), `2605.07301` (SOM: Structured Opponent Modeling via a structural
causal model), `2604.15687` (Preference Estimation via Opponent Modeling in
Negotiation), `2602.19309` (Opponent Simulation for online strategic adaptation
in repeated negotiation), `2407.07086` (Hypothetical Minds: scaffolding theory of
mind for multi-agent tasks). Benchmarks: `2402.16499` (LLMArena), `2605.29512`
(MINDGAMES), `2605.23238` (GENSTRAT), `2604.04157` (emergent ToM-like behaviour
in LLM poker agents).

> **Gap.** These either scaffold an explicit opponent model into the prompt or
> score end-task performance. Almost none isolate *whether an unscaffolded model
> spontaneously forms a target-specific model*, and fewer still measure how that
> model is **revised** when the partner silently changes.

**2. LLM persuasion and personalisation.** Strong, well-powered human-subject
work exists on whether LLM-generated argument beats human argument, and on
whether personalising to a known trait profile adds anything: Matz et al.
(`10.1038/s41598-024-53755-0`), Salvi et al. on GPT-4's conversational
persuasiveness (`10.1038/s41562-025-02194-6`, arXiv `2403.14380`), Hackenburg &
Margetts on political microtargeting (`10.1073/pnas.2403116121`), the diminishing
returns of scale for single-message persuasion (`10.1073/pnas.2413443122`), and a
survey (`2411.06837`). Notably `10.1038/s44271-025-00188-8` finds warning people
they are being microtargeted does not remove the advantage.

> **Gap.** In essentially all of this work the model is *handed* the target
> profile, and persuasion is *single-shot*. Nobody asks whether the model can
> **discover** the profile from behavioural feedback alone, over repeated turns,
> without being told that profiles exist.

**3. Sycophancy and user modelling.** A large and still-growing literature —
`2308.03958` (synthetic data reduces sycophancy), `2503.11656` (TRUTH DECAY:
multi-turn sycophancy), `2505.23840` (sycophancy in multi-turn dialogue),
`2509.21305` (sycophancy is not one construct), plus surveys of LLM user
modelling and evidence that LLMs infer personality from free-form interaction
(`osf.io/apc5g`).

> **Relation.** Sycophancy is *accommodation to expressed preference*. This
> project studies *inference of an unexpressed susceptibility from binary
> outcomes* — a strictly harder inference problem, and one where the target never
> states what it wants.

**4. Belief updating and stickiness in context.** The stale-model half of our
question connects to `2512.18489` (LLMs as **discounted** Bayesian filters —
directly relevant: it predicts systematic over- or under-weighting of new
evidence), positional/primacy effects (`2510.10276` Lost in the Middle,
`2508.18427` positional bias in financial decisions), and `2605.12412`
(in-context learning trajectories in belief space).

> **This is the most promising framing.** "How fast does an LLM revise a model of
> another agent once it has formed one?" is a *belief-revision* question with an
> existing quantitative literature to connect to, and our swap condition is a
> clean instrument for it.

---

## What is genuinely novel here

1. **Susceptibility is never stated and never scaffolded.** The focal agent is
   given one neutral objective sentence. It is not told a type exists.
2. **Ground truth is known and cheap.** A transparent simulator, not an LLM
   target, so the environment's learnable structure is exactly specified.
3. **The swap condition measures revision, not just acquisition.** The
   literature above measures whether a model can be used; this measures how
   sticky one is once formed.
4. **The controls are the point.** `no_history`, `shuffled_history` and
   `random_target` are designed to make the negative result legible.

## What is *not* novel, and should be cited as prior art rather than claimed

- That LLMs can persuade, and that personalisation helps — established.
- That LLMs can use an opponent model when given one — established.
- That LLMs adapt to stated user preferences (sycophancy) — established.

## Positioning risk to watch

If the result is only "match rate rises with rounds", a reviewer can reasonably
say this reduces to win-stay/lose-shift bandit behaviour, which is not
interesting. The defensible claims are the **swap-inertia** measurement and the
**shuffled-history** dissociation. Design the write-up around those.

---

## Provenance

Access date 2026-08-19. No API keys were available; all calls at anonymous rate
limits.

| # | Database | Endpoint | Query |
|---|---|---|---|
| 1 | arXiv | `export.arxiv.org/api/query` | `abs:"large language model" AND (abs:"opponent modeling" OR abs:"opponent modelling" OR abs:"partner model" OR abs:"user model")`, `max_results=25`, `sortBy=relevance` |
| 2 | OpenAlex | `api.openalex.org/works` | `search=large language model persuasion personalization microtargeting`, `filter=from_publication_date:2023-01-01`, `per-page=20` — 329 total hits, first 20 inspected |
| 3 | arXiv | `export.arxiv.org/api/query` | `abs:"language model" AND (abs:sycophancy OR abs:sycophantic OR (abs:"belief" AND abs:"in-context" AND abs:"update"))`, `max_results=30` |
| 4 | OpenAlex | `api.openalex.org/works` | `search=large language model theory of mind repeated interaction adapt partner belief`, `from_publication_date:2023-01-01` — 12,017 total hits, first 20 inspected (query too broad; low precision) |
| 5 | arXiv | `export.arxiv.org/api/query` | belief-revision / anchoring / primacy + `in-context` — low precision, few usable hits |
| 6 | arXiv | `export.arxiv.org/api/query` | in-context learning + non-stationary / partner policy — 6 hits, mostly off-target |

**Warnings.**

- Two Semantic Scholar queries returned **zero results** (`{"total": 0}` and a
  body with no `data` key) at the anonymous rate limit. Semantic Scholar coverage
  is therefore **not represented** below. An `S2_API_KEY` would fix this, and the
  citation-graph view it gives is the main thing missing from this sweep.
- Queries 4-6 were low precision; the OpenAlex "theory of mind" query returned
  12,017 hits and only the first 20 by relevance were inspected. This is **not**
  an exhaustive retrieval and should not be described as one.
- No abstracts or full texts were read. Relevance judgements above are inferred
  from titles and venues and may be wrong.
- Several results carry 2026 dates; they were returned by the live API and have
  not been independently verified.
