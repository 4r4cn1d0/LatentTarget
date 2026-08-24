from src.black_box_baseline import collect_black_box_guesses, score_black_box_guesses


class FakeProvider:
    def __init__(self):
        self.calls = []

    def ask(self, system, user, max_tokens=64):
        self.calls.append((system, user, max_tokens))
        return "fairness" if "first" in user else "risk"


def rows():
    return [
        {"episode_id": "e1", "round": 1, "condition": "full_history",
         "focal_user_prompt": "first", "hidden_target_type": "fairness"},
        {"episode_id": "e1", "round": 2, "condition": "full_history",
         "focal_user_prompt": "second", "hidden_target_type": "risk"},
    ]


def test_collect_and_score_black_box_guesses():
    provider = FakeProvider()
    checkpoints = []
    guesses = collect_black_box_guesses(
        rows(), provider, checkpoint=lambda value: checkpoints.append(value.copy())
    )
    assert guesses == {"e1": {"1": "fairness", "2": "risk"}}
    assert len(provider.calls) == 2
    assert len(checkpoints) == 2
    assert score_black_box_guesses(rows(), guesses)["accuracy"] == 1.0


def test_resume_skips_existing_measurements():
    provider = FakeProvider()
    guesses = collect_black_box_guesses(
        rows(), provider, existing={"e1": {"1": "expertise"}}
    )
    assert guesses["e1"]["1"] == "expertise"
    assert guesses["e1"]["2"] == "risk"
    assert len(provider.calls) == 1
