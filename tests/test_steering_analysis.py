import json

import pytest

from src.steering_analysis import load_steering_dataframe, paired_steering_summary


def test_paired_steering_analysis_recovers_target_effect(tmp_path):
    path = tmp_path / "steer.jsonl"
    with path.open("w") as fh:
        for episode in ("e1", "e2", "e3"):
            for coefficient in (1.0, 3.0):
                for intervention, score in (
                    ("zero", 0.2), ("target", 0.8),
                    ("random", 0.3), ("opposite", 0.1),
                ):
                    row = {
                        "source_episode_id": episode, "source_round": 2,
                        "steer_target": "fairness", "coefficient": coefficient,
                        "intervention": intervention,
                        "strategy_classification": {
                            "fairness": score,
                            "primary_strategy": "fairness" if score > 0.5 else "other",
                        },
                    }
                    fh.write(json.dumps(row) + "\n")
    df = load_steering_dataframe(str(path))
    summary = paired_steering_summary(df, n_boot=100, seed=0)
    primary = [
        row for row in summary
        if row["coefficient"] == 1.0
        and row["metric"] == "intended_score"
        and row["contrast"] == "target_minus_zero"
    ][0]
    assert primary["mean_difference"] == pytest.approx(0.6)
    assert primary["n_source_episodes"] == 3
