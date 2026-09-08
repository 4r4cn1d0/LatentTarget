"""Secondary diagnostics. None can override a failed primary decision."""
from collections import Counter, defaultdict

import numpy as np

from src.partner_statistics import METRICS, percentile_interval


def choice_summaries(rows):
    """Missing observations stay in probability and regret bound denominators."""
    groups = defaultdict(list)
    for row in rows:
        if row["branch"] == "FORECAST":
            continue
        for name, value in (("branch", row["branch"]),
                            ("branch_cell", f"{row['branch']}/{row['cell']}"),
                            ("target", f"{row['branch']}/{row['target_type']}"),
                            ("alias", f"{row['branch']}/{row['recipient']}"),
                            ("scenario", f"{row['branch']}/{row['scenario']}"),
                            ("order", f"{row['branch']}/{row['candidate_order']}")):
            groups[(name, value)].append(row)
    result = {}
    for (name, value), items in sorted(groups.items()):
        valid = [r for r in items if r["response_status"] == "valid"]
        result.setdefault(name, {})[value] = {
            "planned": len(items), "valid": len(valid), "validity": len(valid)/len(items),
            "status_counts": dict(Counter(r["response_status"] for r in items)),
            "chosen_slot_counts": dict(Counter(str(r["candidate_slot"]+1) for r in valid)),
            "expected_success_valid_only": float(np.mean([r["expected_success"] for r in valid])) if valid else None,
            "expected_success_bounds": [float(np.mean([r[k] for r in items])) for k in ("expected_success_lower", "expected_success_upper")],
            "regret_bounds": [float(np.mean([r[k] for r in items])) for k in ("regret_lower", "regret_upper")],
        }
    return result


def forecast_summaries(rows):
    forecasts = [r for r in rows if r["branch"] == "FORECAST"]
    valid = [r for r in forecasts if r["valid"]]
    matched = [r for r in valid if r["choice_slot"] is not None]
    correct_order, unequal_pairs = 0., 0
    calibration = [[] for _ in range(5)]
    for row in valid:
        forecast, truth = row["forecast"], row["probabilities"]
        for p, q in zip(forecast, truth):
            calibration[min(int(p*5), 4)].append((p, q))
        for i in range(3):
            for j in range(i+1, 3):
                if abs(truth[i]-truth[j]) < 1e-12:
                    continue
                unequal_pairs += 1
                difference = forecast[i]-forecast[j]
                correct_order += .5 if abs(difference) < 1e-12 else float(difference*(truth[i]-truth[j]) > 0)
    def agreement(row):
        return row["forecast"][row["choice_slot"]] >= max(row["forecast"]) - 1e-12
    return {
        "planned": len(forecasts), "valid": len(valid),
        "validity": len(valid)/len(forecasts) if forecasts else None,
        "by_cell": {str(cell): {"planned": sum(r["cell"] == cell for r in forecasts),
                               "valid": sum(r["cell"] == cell for r in valid)} for cell in range(4)},
        "mse": float(np.mean([r["forecast_mse"] for r in valid])) if valid else None,
        "prior_only_mse_same_valid_subset": float(np.mean([r["prior_mse"] for r in valid])) if valid else None,
        "pairwise_rank_agreement": correct_order/unequal_pairs if unequal_pairs else None,
        "choice_forecast_matched_valid_pairs": len(matched),
        "choice_in_forecast_argmax_fraction": float(np.mean([agreement(r) for r in matched])) if matched else None,
        "calibration_against_known_simulator_probability": [
            {"bin": [i/5,(i+1)/5], "count": len(items),
             "mean_forecast": float(np.mean([x[0] for x in items])) if items else None,
             "mean_true_probability": float(np.mean([x[1] for x in items])) if items else None}
            for i, items in enumerate(calibration)],
        "interpretation": "Secondary conditional probability diagnostic, not access to internal beliefs. Valid only summaries can be selected by missingness.",
    }


def complete_case_sensitivity(lower, upper, strata):
    """Metric complete bundles only; descriptive sensitivity, never a rescue gate."""
    result = {}
    for j, metric in enumerate(METRICS):
        mask = np.isclose(lower[0,:,j], upper[0,:,j], atol=1e-12, rtol=0)
        values = lower[0,mask,j]
        represented = len(np.unique(strata[mask]))
        eligible = len(values) >= 2 and represented == len(np.unique(strata))
        result[metric] = {"complete_bundles": int(mask.sum()), "planned_bundles": len(mask),
                          "mean": float(values.mean()) if len(values) else None,
                          "interval": percentile_interval(values, strata[mask], .025 if j < 2 else .05)[0].tolist() if eligible else None,
                          "strata_represented": represented, "used_for_gate": False}
    return result
