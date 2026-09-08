import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.grounded_review import review_batch,FIELDS,validate


def example():return [{"item_id":"opaque","scenario":"A has equal access.","option_a":"A","option_b":"B","message":"Choose A for equal access."}]


def result():return {"results":[dict({k:.9 for k in FIELDS},item_id="opaque",primary_frame="fairness",reason="Grounded.")]}


def test_machine_contract_and_replay_no_new_invocation(tmp_path):
    calls=[]
    def run(cmd,**kw):
        calls.append(cmd);assert "--ignore-user-config" in cmd and "--ignore-rules" in cmd
        Path(cmd[cmd.index("--output-last-message")+1]).write_text(json.dumps(result()))
        return SimpleNamespace(returncode=0,stdout="",stderr="model: gpt-5.6-sol\n")
    a=review_batch(example(),"gpt-5.6-sol",tmp_path,0,runner=run)
    assert a==review_batch(example(),"gpt-5.6-sol",tmp_path,0,runner=run)
    assert len(calls)==1
    assert json.loads((tmp_path/"batch_00.meta.json").read_text())["human_validation"] is False


def test_failed_or_uncertain_measurement_not_repeated(tmp_path):
    calls=[]
    def fail(*args,**kwargs):calls.append(1);raise TimeoutError()
    with pytest.raises(TimeoutError):review_batch(example(),"gpt-5.6-sol",tmp_path,0,runner=fail)
    with pytest.raises(RuntimeError):review_batch(example(),"gpt-5.6-sol",tmp_path,0,runner=fail)
    assert len(calls)==1


def test_judge_cannot_receive_analyst_fields(tmp_path):
    items=example();items[0]["target_type"]="fairness"
    with pytest.raises(ValueError):review_batch(items,"gpt-5.6-sol",tmp_path,0)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("value",[float("nan"),True,-.1,1.1])
def test_bad_scores_rejected(value):
    payload=result();payload["results"][0]["factual_support"]=value
    with pytest.raises(ValueError):validate(payload,["opaque"])
