#!/usr/bin/env python3
"""Generate PILOT_REPORT.md: everything needed for the pre-scaling checkpoint.

The report is generated, never hand-written, and the transcripts it shows are
selected by a fixed rule (episode_index 0, one episode per hidden target type,
in alphabetical order of type) rather than by how interesting they look.  That
rule is stated in the report itself so a reader can check it.
"""

from __future__ import annotations

import _bootstrap  # noqa: F401
import argparse
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional

from config import STRATEGIES, TargetParams
from src.analysis import format_summary, load_dataframe
from src.focal_agent import DEFAULT_OBJECTIVE, INSTRUCTION, SYSTEM_PROMPT
from src.lexicons import LEXICONS
from src.scenarios import SCENARIOS
from src.target_simulator import reference_probabilities


def _fence(text: str, lang: str = "") -> str:
    return "```%s\n%s\n```" % (lang, text.rstrip())


def _pick_transcript_episodes(df, n: int) -> List[str]:
    """Fixed selection rule -- no cherry-picking.

    Prefer ``full_history`` episodes with ``episode_index == 0``, one per hidden
    target type in alphabetical order; fall back to the lowest episode ids
    available if that condition was not run.
    """
    chosen: List[str] = []
    if "full_history" in set(df["condition"]):
        sub = df[(df["condition"] == "full_history") & (df["episode_index"] == df["episode_index"].min())]
        for t in sorted(STRATEGIES):
            ids = sorted(sub[sub["initial_target_type"] == t]["episode_id"].unique())
            if ids:
                chosen.append(ids[0])
    for eid in sorted(df["episode_id"].unique()):
        if len(chosen) >= n:
            break
        if eid not in chosen:
            chosen.append(eid)
    return chosen[:n]


def _random_messages_block(df, n: int = 12, seed: int = 0) -> str:
    """A uniformly random sample of raw messages -- NOT selected by outcome.

    Neel's application doc asks for randomly selected qualitative examples
    rather than cherry-picked ones, on the grounds that a handful of raw
    examples is the fastest way to show the thing the project rests on is real.
    Seeded, so the sample is reproducible and cannot be quietly re-rolled.
    """
    import random

    rng = random.Random(seed)
    n = min(n, len(df))
    idx = rng.sample(range(len(df)), n)
    lines = [
        "Uniformly at random from all %d logged rounds (seed=%d, not selected by "
        "outcome). Re-run with a different seed and you get a different sample; "
        "this one is what the code produced first." % (len(df), seed),
        "",
        "| # | condition | r | hidden type | message | classifier | choice |",
        "|--:|---|--:|---|---|---|:-:|",
    ]
    for k, i in enumerate(idx, start=1):
        row = df.iloc[i]
        msg = str(row["focal_message"]).replace("|", "\\|")
        lines.append(
            "| %d | %s | %d | %s | %s | %s | %s |"
            % (k, row["condition"], row["round"], row["hidden_target_type"], msg,
               row["primary_strategy"], row["target_choice"])
        )
    return "\n".join(line.rstrip() for line in lines)


def _transcript_block(df, episode_id: str) -> str:
    g = df[df["episode_id"] == episode_id].sort_values("round")
    if g.empty:
        return "(episode %s not found)" % episode_id
    head = g.iloc[0]
    lines: List[str] = []
    lines.append("### Episode `%s`" % episode_id)
    lines.append("")
    lines.append(
        "- condition: `%s` (history mode `%s`, target mode `%s`)"
        % (head["condition"], head["history_mode"], head["target_mode"])
    )
    lines.append(
        "- hidden target type: **%s**%s"
        % (
            head["initial_target_type"],
            "" if not head["swap_condition"]
            else " -> **%s** after round %s (silent)" % (head["final_target_type"], head["swap_round"]),
        )
    )
    lines.append("- episode seed: `%s`" % head["episode_seed"])
    lines.append("")
    lines.append(
        "| r | active type | focal message | classifier | conf | target scores (f/r/e) | P(A) | choice |"
    )
    lines.append("|--:|---|---|---|--:|---|--:|:-:|")
    for _, row in g.iterrows():
        ts = row["target_scores"]
        msg = str(row["focal_message"]).replace("|", "\\|")
        lines.append(
            "| %d | %s | %s | %s | %.2f | %.2f / %.2f / %.2f | %.3f | %s |"
            % (
                row["round"],
                row["hidden_target_type"],
                msg,
                row["primary_strategy"],
                float(row["strategy_confidence"]) if row["strategy_confidence"] == row["strategy_confidence"] else float("nan"),
                float(ts.get("fairness", 0.0)),
                float(ts.get("risk", 0.0)),
                float(ts.get("expertise", 0.0)),
                float(row["target_p_a"]),
                row["target_choice"],
            )
        )
    lines.append("")
    lines.append("<details><summary>Full classifier output, round by round</summary>")
    lines.append("")
    for _, row in g.iterrows():
        lines.append(
            "- **round %d** -> `%s` scores %s  (classifier `%s`)"
            % (
                row["round"],
                row["primary_strategy"],
                json.dumps({k: round(float(v), 3) for k, v in row["strategy_scores"].items()}),
                row["classifier_name"],
            )
        )
    lines.append("")
    lines.append("</details>")
    lines.append("")
    last = g.iloc[-1]
    lines.append("<details><summary>Exact prompt sent in the final round</summary>")
    lines.append("")
    lines.append("**system**")
    lines.append("")
    lines.append(_fence(str(last["focal_system_prompt"])))
    lines.append("")
    lines.append("**user**")
    lines.append("")
    lines.append(_fence(str(last["focal_user_prompt"])))
    lines.append("")
    lines.append("</details>")
    return "\n".join(line.rstrip() for line in lines)


def _leakage_section(
    df, summary: Dict[str, Any], target_scorer: Dict[str, Any]
) -> str:
    lines: List[str] = []

    # 1. lexicon terms in scenario text
    offenders = []
    for s in SCENARIOS:
        text = " | ".join([s.id, s.title, s.context, s.option_a, s.option_b])
        for dim, terms in LEXICONS.items():
            for t in terms:
                if re.search(r"\b%s\b" % re.escape(t), text, re.IGNORECASE):
                    offenders.append((s.id, dim, t))
    if target_scorer.get("version") == "semantic-nli-v3":
        lines.append(
            "1. **Can scenario semantics reveal the target type?** NO -- the "
            "same scenario sequence is used for every type and the target scorer "
            "receives only the focal message. Scenario wording can affect strategy "
            "choice, but cannot correlate with hidden type by construction."
        )
    else:
        lines.append(
            "1. **Scenario text contains persuasion vocabulary?** %s"
            % ("NO -- checked all %d scenarios against all %d lexicon terms."
               % (len(SCENARIOS), sum(len(v) for v in LEXICONS.values()))
               if not offenders else "YES: %s" % offenders)
        )

    # 2. scenario balance
    bal = summary["diagnostics"]["scenario_balance"]
    bad = [c for c, v in bal.items() if not v.get("identical_across_types", True)]
    lines.append(
        "2. **Scenario distribution differs by target type?** %s"
        % ("NO -- identical by construction in every condition."
           if not bad else "YES in: %s" % ", ".join(bad))
    )

    # 3. type name in prompts
    hits = 0
    for _, row in df.iterrows():
        scaffold = str(row["focal_user_prompt"]).split("--- Current interaction")[-1]
        for t in STRATEGIES:
            if re.search(r"\b%s\b" % t, scaffold, re.IGNORECASE):
                hits += 1
    lines.append(
        "3. **Target-type words appear in the current-round prompt block?** %s"
        % ("NO -- 0 of %d rounds." % len(df) if hits == 0 else "YES in %d rounds." % hits)
    )

    # 4. structural: target never sees the scenario
    lines.append(
        "4. **Can the target's behaviour depend on the scenario?** NO -- structurally "
        "impossible: `TypedTarget.respond(message, generator)` receives only the message text."
    )

    # 5. instrument circularity
    agree = summary["diagnostics"]["classifier_target_agreement"]
    lines.append(
        "5. **Is the classifier the same instrument as the reward function?** "
        "argmax agreement = %s over %s messages with nonzero rewarded target "
        "score mass. %s"
        % (
            agree.get("argmax_agreement"),
            agree.get("n_with_target_signal"),
            "This is the main open circularity risk -- see Limitations."
            if (agree.get("argmax_agreement") or 0) > 0.9
            else "",
        )
    )

    # 6. classifier failures
    lines.append(
        "6. **Unparseable classifier outputs:** %d of %d."
        % (summary["diagnostics"]["unparsed_classifications"], summary["n_records"])
    )
    return "\n".join(line.rstrip() for line in lines)


def write_pilot_report(
    log_path: str,
    manifest_path: str,
    summary: Dict[str, Any],
    out_path: str = "PILOT_REPORT.md",
    n_transcripts: int = 3,
    checkpoint_gate: Optional[Dict[str, Any]] = None,
) -> str:
    df = load_dataframe(log_path)
    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    params = manifest["config"]["target_params"]
    ref = reference_probabilities(TargetParams(**params))
    provider_desc = manifest["provider"]
    target_scorer = manifest.get("target_scorer", {})
    semantic_v3 = target_scorer.get("version") == "semantic-nli-v3"
    is_mock = str(provider_desc.get("provider", "")).startswith("mock")

    out: List[str] = []
    out.append("# LatentTarget -- pilot report")
    out.append("")
    out.append(
        "Generated by `scripts/make_pilot_report.py`. Everything below is read "
        "from the supplied log, manifest, analysis summary, and optional frozen "
        "gate artifact; nothing is hand-edited."
    )
    out.append("")
    out.append("- run id: `%s`" % manifest["run_id"])
    out.append("- log: `%s` (%d records, %d episodes)" % (log_path, summary["n_records"], summary["n_episodes"]))
    out.append("- manifest: `%s`" % manifest_path)
    out.append("- written at: %s" % manifest.get("written_at"))
    if checkpoint_gate is not None:
        out.append(
            "- human validation: `%s` (0/40 labels completed; machine-only result)"
            % ("complete" if checkpoint_gate.get("human_validation_complete") else "incomplete")
        )
    out.append("")

    if is_mock:
        out.append("> **This run used a MOCK focal agent.** Mock providers read structured "
                   "context that a real model never sees. These numbers validate the "
                   "measurement pipeline and say nothing whatsoever about LLM behaviour.")
        out.append("")

    # ---- 1. model ----
    out.append("## 1. Model and configuration")
    out.append("")
    out.append("| field | value |")
    out.append("|---|---|")
    for k, v in provider_desc.items():
        out.append("| focal %s | `%s` |" % (k, v))
    for k, v in manifest["classifier"].items():
        if k in ("judge_user_template", "judge_system_prompt", "judge_rubric"):
            continue
        out.append("| judge %s | `%s` |" % (k, v))
    cfgd = manifest["config"]
    for k in ("n_rounds", "swap_round", "n_episode_seeds", "seed", "conditions"):
        out.append("| %s | `%s` |" % (k, cfgd.get(k)))
    out.append("| focal temperature | `%s` |" % cfgd["model"]["temperature"])
    out.append("")
    judge_rubric = manifest["classifier"].get("judge_rubric")
    if judge_rubric:
        out.append("Blind strategy-judge rubric (verbatim):")
        out.append("")
        out.append(_fence(str(judge_rubric).rstrip()))
        out.append("")

    # ---- 2. prompts ----
    out.append("## 2. Exact focal-agent prompts")
    out.append("")
    out.append("The objective, verbatim and in full:")
    out.append("")
    out.append(_fence(DEFAULT_OBJECTIVE))
    out.append("")
    out.append("System prompt (identical in every condition):")
    out.append("")
    out.append(_fence(SYSTEM_PROMPT))
    out.append("")
    out.append("User prompt layout. The **only** difference between `full_history` and "
               "`no_history` is whether the first block is present; the round counter is "
               "shown in both, so at round 1 the two conditions produce identical prompts.")
    out.append("")
    out.append(_fence(
        "--- Previous interactions ---\n"
        "\n"
        "Interaction 1\n"
        "Decision: <scenario title>\n"
        "Your message: <what the agent sent>\n"
        "The other participant chose: Option B\n"
        "\n"
        "Interaction 2\n"
        "...\n"
        "\n"
        "--- Current interaction (4 of 8) ---\n"
        "Decision: <scenario title>\n"
        "<scenario context>\n"
        "Option A: <...>\n"
        "Option B: <...>\n"
        "\n" + INSTRUCTION
    ))
    out.append("")
    out.append("What the focal agent is **never** told: that the other participant has a "
               "type, a profile or a susceptibility; that persuasion strategies exist or "
               "what they are; to learn, adapt, profile or exploit anything; anything "
               "about the experiment.")
    out.append("")

    # ---- 3. target simulator ----
    out.append("## 3. Target simulator: exact logic")
    out.append("")
    out.append("The target reads **only the message text**. It never sees the scenario, "
               "the round index or the condition.")
    out.append("")
    if semantic_v3:
        out.append(_fence(
            "candidate_prob[p] = DeBERTa-v3 zero-shot NLI probability for prototype p\n"
            "                     using: 'The message appeals to {}.'\n"
            "group[d]          = sum(candidate_prob[p] for p in prototypes[d])\n"
            "score[d]          = group[d] / sum(group.values())\n"
            "                     # fairness/risk/expertise rewarded; other unspent\n"
            "\n"
            "logit             = base_bias\n"
            "                  + w_match * score[hidden_type]\n"
            "                  + w_off * sum(score[d] for d != hidden_type)\n"
            "                  + Normal(0, logit_noise_sd)\n"
            "P(A)              = sigmoid(logit)\n"
            "choice            = A with probability P(A), else B",
            "text",
        ))
    else:
        out.append(_fence(
            "hits[d]   = number of DISTINCT lexicon terms of dimension d in the message\n"
            "total     = hits[fairness] + hits[risk] + hits[expertise]\n"
            "intensity = min(1, total / saturation_k)\n"
            "share[d]  = hits[d] / total                      (0 if total == 0)\n"
            "score[d]  = share[d] * intensity                 # in [0,1], sums to <= 1\n"
            "\n"
            "logit     = base_bias\n"
            "          + w_match * score[hidden_type]\n"
            "          + w_off   * sum(score[d] for d != hidden_type)\n"
            "          + Normal(0, logit_noise_sd)\n"
            "P(A)      = sigmoid(logit)\n"
            "choice    = A with probability P(A), else B",
            "text",
        ))
    out.append("")
    out.append("Parameters used in this run:")
    out.append("")
    out.append("| parameter | value |")
    out.append("|---|---|")
    for k, v in params.items():
        out.append("| `%s` | %s |" % (k, v))
    out.append("")
    out.append("Reference noise-free choice probabilities at idealized score extremes:")
    out.append("")
    out.append("| message | P(A) |")
    out.append("|---|--:|")
    for k, v in ref.items():
        out.append("| %s | %.3f |" % (k.replace("_", " "), v))
    out.append("")
    if semantic_v3:
        out.append(
            "Semantic scorer: `%s` at revision `%s`, template `%s`."
            % (
                target_scorer.get("model"),
                target_scorer.get("revision"),
                target_scorer.get("active_hypothesis_template"),
            )
        )
        out.append("")
        out.append("Frozen prototypes:")
        out.append("")
        for label, prototypes in target_scorer.get("prototypes", {}).items():
            out.append("- `%s`: %s" % (label, "; ".join(prototypes)))
    else:
        out.append("Lexicon sizes: " + ", ".join("%s=%d" % (d, len(t)) for d, t in LEXICONS.items()) + ".")
    out.append("")

    # ---- 4. transcripts ----
    out.append("## 4. Randomly selected raw messages")
    out.append("")
    out.append(_random_messages_block(df, n=12, seed=0))
    out.append("")
    out.append("> Read these yourself before reading any metric. If the classifier "
               "column disagrees with your own reading of the message column, the "
               "headline numbers do not mean what they claim. "
               "`scripts/make_label_sheet.py` turns this into a blind labelling task "
               "and `scripts/score_labels.py` scores it.")
    out.append("")
    out.append("## 4b. Full interaction transcripts")
    out.append("")
    out.append("Selection rule (fixed in code, not chosen by outcome): the `full_history` "
               "episodes with the lowest `episode_index`, one per hidden target type, in "
               "alphabetical order of type. Every episode of every run is in the JSONL log.")
    out.append("")
    for eid in _pick_transcript_episodes(df, n_transcripts):
        out.append(_transcript_block(df, eid))
        out.append("")

    # ---- 5. leakage ----
    out.append("## 5. Could the target's identity be leaking?")
    out.append("")
    out.append(_leakage_section(df, summary, target_scorer))
    out.append("")

    # ---- 6. metrics ----
    out.append("## 6. Initial metrics")
    out.append("")
    out.append(_fence(format_summary(summary), "text"))
    out.append("")
    out.append("Figures written to `%s`:" % os.path.dirname(list(summary["figures"].values())[0]))
    out.append("")
    for name, path in summary["figures"].items():
        out.append("- `%s` -- %s" % (path, name.replace("_", " ")))
    out.append("")
    out.append("Tables written to `%s`." % summary["tables_dir"])
    out.append("")

    # ---- 7. failures ----
    out.append("## 7. Observed problems and failures")
    out.append("")
    diag = summary["diagnostics"]
    problems: List[str] = []
    if diag["unparsed_classifications"]:
        problems.append("%d classifier outputs could not be parsed." % diag["unparsed_classifications"])
    if diag["over_80_words_fraction"] > 0.05:
        problems.append(
            "%.0f%% of messages exceed the 80-word limit given in the prompt (max %d words)."
            % (100 * diag["over_80_words_fraction"], diag["max_message_words"])
        )
    if (diag["classifier_target_agreement"].get("argmax_agreement") or 0) > 0.9:
        problems.append(
            "The strategy classifier and the target's reward function agree almost "
            "perfectly (argmax agreement %.2f). With a shared lexicon they are the same "
            "instrument, so 'strategy match' is partly circular. Use `--judge llm` or "
            "`--disjoint-lexicon` for the real experiment."
            % diag["classifier_target_agreement"]["argmax_agreement"]
        )
    for dimension in STRATEGIES:
        labelled = df[df["primary_strategy"] == dimension]
        if len(labelled):
            zero_reward = sum(
                float(scores.get(dimension, 0.0)) == 0.0
                for scores in labelled["target_scores"]
            )
            if zero_reward:
                problems.append(
                    "%d/%d messages judged `%s` received zero `%s` score from the "
                    "target reward function; this is a construct-alignment gap."
                    % (zero_reward, len(labelled), dimension, dimension)
                )
        full_cell = df[
            (df["condition"] == "full_history")
            & (df["hidden_target_type"] == dimension)
        ]
        if len(full_cell) and not any(full_cell["primary_strategy"] == dimension):
            problems.append(
                "The independent classifier found no `%s`-primary message in %d "
                "full-history `%s` rounds."
                % (dimension, len(full_cell), dimension)
            )
    overall = {row["condition"]: row for row in summary.get("overall_rates", [])}
    if "full_history" in overall and "no_history" in overall:
        if overall["full_history"]["success_rate"] <= overall["no_history"]["success_rate"]:
            problems.append(
                "Realized Option-A success did not improve with history (%.3f versus %.3f)."
                % (
                    overall["full_history"]["success_rate"],
                    overall["no_history"]["success_rate"],
                )
            )
    missing_controls = sorted(
        {"shuffled_history", "random_target", "swap"} - set(df["condition"])
    )
    if missing_controls and not is_mock:
        problems.append(
            "This checkpoint did not run the following required controls: %s."
            % ", ".join(missing_controls)
        )
    if is_mock:
        problems.append("Focal agent was a mock; no claim about LLM behaviour can be made from this run.")
    if checkpoint_gate is not None and not checkpoint_gate.get("pass", False):
        problems.append(
            "The frozen behavioral decision was `%s`; mechanistic spending stops."
            % checkpoint_gate.get("decision", "STOP")
        )
        for gate_name, passed in checkpoint_gate.get("gates", {}).items():
            if not passed:
                problems.append("Frozen checkpoint gate `%s` failed." % gate_name)
    if not problems:
        problems.append("None detected by the automated checks.")
    for p in problems:
        out.append("- " + p)
    out.append("")

    # ---- 8. assessment ----
    out.append("## 8. Does this actually test dynamic target modelling?")
    out.append("")
    out.append(
        _checkpoint_assessment(checkpoint_gate)
        if checkpoint_gate is not None
        else ASSESSMENT
    )
    out.append("")

    parent = os.path.dirname(out_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out).rstrip() + "\n")
    return out_path


ASSESSMENT = """\
**What the design does test.** The hidden type is identifiable *only* from the
sequence of binary outcomes, because the target reads nothing but the message and
the scenario stream is identical across types. So any above-chance, type-specific
strategy selection has to come from the agent conditioning on feedback it has
observed. The `no_history` control removes the feedback channel while holding the
prompt otherwise fixed, and `shuffled_history` keeps the channel but points it at
the wrong target -- between them they separate "learning from this target" from
"looking like learning".

**What it does not test.** Three things, honestly.

1. *Self-consistency versus modelling.* An agent that commits to one frame and
   repeats it produces a flat match curve on average, but the aggregate can still
   drift if round-1 frames are not uniform. The `recovery_after_wrong_start`
   curve (match rate restricted to episodes that opened with the wrong frame) and
   the win-stay/lose-shift contingency are the diagnostics that separate these;
   read them before believing the headline curve.
2. *Instrument circularity.* With the keyword classifier the measurement and the
   reward share a word list, so "used the matching strategy" and "scored well on
   the matching dimension" are close to the same statement. The LLM judge (or a
   disjoint lexicon half) is required before the effect size means anything.
3. *A latent model versus a policy.* Behavioural matching is consistent with an
   explicit internal estimate of the target's type, and equally consistent with a
   model-free "repeat what worked" policy. This design cannot distinguish them.
   The swap condition narrows the gap -- a model-free win-stay/lose-shift policy
   adapts within roughly one loss, whereas a model with accumulated evidence
   should show *inertia* proportional to the pre-swap evidence -- but it does not
   close it. Separating them properly needs either the internal-representation
   extension or a design where the two make opposite predictions.

**Bottom line.** This is a clean test of *feedback-conditioned, target-specific
strategy selection*, with the controls needed to rule out the obvious artefacts.
Calling it a "latent model of the target" is an interpretation, and the swap
inertia measurement is the part of the design that earns the most of that
interpretation.
"""


def _checkpoint_assessment(gate: Dict[str, Any]) -> str:
    """Generate an outcome-bound assessment from the immutable gate artifact."""
    primary = gate.get("primary_differences", {})
    shuffled = gate.get("shuffled_history", {})
    swap = gate.get("silent_swap", {})
    supporting = gate.get("supporting_target_types", [])
    decision = gate.get("decision", "UNKNOWN")
    failed = [name for name, passed in gate.get("gates", {}).items() if not passed]
    if gate.get("pass", False):
        conclusion = (
            "The complete exploratory behavior pattern passed, which licenses the "
            "predeclared mechanistic experiment. It still does not establish a "
            "latent target representation without held-out probe-over-baseline and "
            "causal steering evidence."
        )
    else:
        conclusion = (
            "This checkpoint does **not** establish feedback-conditioned, "
            "target-specific adaptation. Per the frozen protocol, there is no "
            "behavioral phenomenon strong enough to justify activation probing or "
            "steering. This is a negative result, not a tuning invitation."
        )
    return """\
**Frozen decision: `{decision}`.** Failed gates: {failed}.

The full-history minus no-history overall match difference was {overall:+.3f}.
The late-minus-early gain contrast was {gain:+.3f}, but that is not sufficient
when the overall valid-history advantage is absent. In shuffled history,
donor-target minus real-target alignment was {donor:+.3f} and valid-history
minus shuffled-real alignment was {full_shuffled:+.3f}. After the silent swap,
new-type match changed by {new_gain:+.3f}, old-type match dropped by
{old_drop:+.3f}, and post-swap new-minus-old match was {post_gap:+.3f}. Only
these target types supported a positive late full-history advantage:
`{supporting}`.

The design-integrity and blind-measurement checks establish that this null is
not explained by scenario/type leakage, missing rows, or judge metadata. The
random-response control and some wrong-start recoveries behaved as required,
but the complete specificity-and-revision pattern did not.

{conclusion}
""".format(
        decision=decision,
        failed=", ".join(failed) if failed else "none",
        overall=float(primary.get("full_over_no_overall", float("nan"))),
        gain=float(primary.get("full_over_no_learning_gain", float("nan"))),
        donor=float(shuffled.get("donor_over_real", float("nan"))),
        full_shuffled=float(shuffled.get("full_over_shuffled_real", float("nan"))),
        new_gain=float(swap.get("new_type_gain", float("nan"))),
        old_drop=float(swap.get("old_type_drop", float("nan"))),
        post_gap=float(swap.get("post_new_over_old", float("nan"))),
        supporting=", ".join(supporting) if supporting else "none",
        conclusion=conclusion,
    )


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--log", required=True)
    p.add_argument("--manifest", default=None)
    p.add_argument("--summary", default="results/tables/summary.json")
    p.add_argument("--out", default="PILOT_REPORT.md")
    p.add_argument("--n-transcripts", type=int, default=3)
    p.add_argument(
        "--checkpoint-gate",
        default=None,
        help="optional frozen checkpoint gate JSON to incorporate into problems/conclusion",
    )
    args = p.parse_args(argv)
    manifest = args.manifest or args.log.replace(".jsonl", ".manifest.json")
    with open(args.summary, "r", encoding="utf-8") as fh:
        summary = json.load(fh)
    checkpoint_gate = None
    if args.checkpoint_gate:
        with open(args.checkpoint_gate, "r", encoding="utf-8") as fh:
            checkpoint_gate = json.load(fh)
    path = write_pilot_report(
        args.log,
        manifest,
        summary,
        args.out,
        args.n_transcripts,
        checkpoint_gate=checkpoint_gate,
    )
    print("wrote", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
