# Verification checklist

Things **you** need to check by hand, ordered by how much damage they do if
wrong. Every item has the command to run, what a pass looks like, and a place to
record what you actually found. Fill in the "found" column as you go — the
filled-in version is evidence for the write-up, not busywork.

The standing assumption should be that a plausible-looking result is wrong until
you have personally looked at the thing it rests on.

---

## Tier 1 — if these are wrong, everything downstream is noise

### 1.1 Does the classifier agree with you?

The whole project reduces to "which persuasion frame did the model use". If the
classifier's answer differs from yours, every match rate is meaningless.

```bash
python scripts/make_label_sheet.py --log data/raw/<run>.jsonl --n 40 --seed 0
# fill in the human_label column in data/processed/label_sheet.csv — blind,
# no target type or judge label visible. Don't open the .key.json first.
python scripts/score_labels.py --sheet data/processed/label_sheet.csv
```

**Pass:** Cohen's kappa ≥ 0.6, and the headline match rate recomputed from your
labels tells the same story as the classifier's. **Fail:** kappa < 0.4 — stop
and fix the classifier before running anything else.

_Found: ______ (kappa = ____, n = ____, date ____)_

### 1.2 Read the raw transcripts

```bash
python scripts/print_transcripts.py --log data/raw/<run>.jsonl --random 5 --seed 0 --prompts
```

Read all of them, prompts included. Questions to answer for yourself:
- Does the message actually read like a persuasive attempt, or like a model
  hedging and refusing to commit?
- Does the model ever say out loud that it's tracking the other participant?
  (Worth quoting either way.)
- Does it keyword-stuff? Does message length climb across rounds?
- Does it ever ignore the format instruction, or write 200 words?

_Found: ______

### 1.3 Does the effect exist at all in your model?

Before any mechanistic work: does the model you plan to probe actually adapt?

```bash
python scripts/run_pilot.py --provider <p> --model <m> --conditions full_history no_history \
    --episodes 4 --rounds 8
```

**Pass:** `full_history` match rate rises across rounds and `no_history` doesn't.
**Fail:** flat in both — the model isn't adapting and there is no latent belief
to decode. Say so and pivot; a documented negative here is worth more than a
probe trained on nothing.

_Found: ______

---

## Tier 2 — the alternative explanations that will be raised

### 2.1 Is it just self-consistency?

An agent that picks one frame and repeats it can produce a rising aggregate
curve without modelling anything.

```bash
# results/tables/recovery_after_wrong_start.csv and strategy_persistence.csv
```

**The question:** among episodes whose round-1 frame was *wrong*, does the match
rate rise? If it stays flat, you're measuring stubbornness, not learning.

_Found: ______

### 2.2 Is the classifier the same instrument as the reward?

With the keyword classifier, argmax agreement with the target's scorer is
**1.00** — they share a word list. Re-run with the LLM judge:

```bash
python scripts/analyze_results.py --log data/raw/<run>.jsonl --reclassify llm \
    --judge-provider <p> --judge-model <m> --prefix llm_
```

**Pass:** effect survives, agreement drops well below 1.0. Report both numbers.

_Found: ______

### 2.3 Does it show up where it can't?

`random_target` has nothing to learn. Any trend there is an artefact of the
prompt or the classifier, not adaptation. Check `permutation_tests.csv`.

_Found: ______

### 2.4 Different seed, different target parameters

```bash
python scripts/run_experiment.py --seed 99 ...
python scripts/run_experiment.py --w-match 1.8 --logit-noise-sd 0.9 ...
```

_Found: ______

---

## Tier 3 — if you do the probing extension

### 3.1 Baselines, before you believe the probe

Neel lists *"failing to compare to baselines"* as a common mistake and names
these: **random vector, choose randomly, ask an LLM, use a linear probe.**

- **Random direction** of the same norm, same layer → probe must beat it.
- **Just ask the model**: "what do you think would persuade the other
  participant?" A probe that doesn't beat black-box prompting has not earned
  the extra machinery. Do this one *first* — it's ten minutes and it might just
  work, which is a fine outcome.
- **Behavioural readout**: predict the target type from the frames the model has
  already used. The probe is only interesting if it beats this — otherwise it's
  reading the model's own output back to you.
- **Shuffled labels** → accuracy must collapse to chance.

_Found: ______

### 3.2 Is the probe reading the target, or the history?

The prompt literally contains the outcome sequence. A probe could be decoding
"how many A's are in the context" rather than any belief about the target.

**Test:** hold out by episode, and check the probe on `shuffled_history`
episodes, where the visible history belongs to a *different* target. If the
probe tracks the donor's type rather than the real one, it's reading the
context, which is a different (and less interesting) claim.

_Found: ______

### 3.3 Does the probe generalise off-distribution?

Train on stable episodes, test on swap episodes. If it only works where it was
trained, the "belief" reading is not supported.

_Found: ______

---

## Tier 4 — write-up integrity

- [ ] Every number in the write-up recomputed independently at least once —
      a fresh one-liner over the JSONL, not the same code path.
- [ ] Randomly-sampled qualitative examples included, right after the exec
      summary. Not cherry-picked. `PILOT_REPORT.md` §4 generates these.
- [ ] Limitations stated plainly, including the ones that hurt.
- [ ] Every claim traceable to a table or figure in `results/`.
- [ ] Negative and inconclusive results included, not buried.
- [ ] Exec summary and application-form answers written by you, in your voice.
- [ ] Hours logged.

---

## Known weaknesses to state up front, not defend

1. The target rewards **lexical surface features**. Distinct-term counting with
   saturation limits keyword-stuffing but does not eliminate it.
2. **Specialisation is designed to pay** (`share × intensity`). We test whether
   the model discovers *which* frame, given that committing is rewarded — not
   whether committing is a good idea.
3. **Three discrete types** stand in for something continuous.
4. **Behaviour ≠ latent model.** The swap narrows the gap between "has a model"
   and "runs a win-stay/lose-shift policy"; it does not close it. This is
   exactly what the probe is for, and why probe-vs-behaviour *timing* is the
   interesting comparison rather than probe accuracy alone.
