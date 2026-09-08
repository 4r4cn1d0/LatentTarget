from copy import deepcopy
import json

import pytest
import numpy as np

from scripts.run_partner_offline import sha
from scripts.verify_partner_repair import verify_manifest,archived_flags
from src.stratified_intervals import repaired_decision


def test_manifest_tamper_and_file_set(tmp_path):
    p = tmp_path/"result.json"; p.write_text("{}")
    manifest = {"status":"COMPLETE","model_calls":0,"paid_calls":0,"inputs":{},"outputs":{"result.json":sha(p)}}
    (tmp_path/"manifest.json").write_text(json.dumps(manifest))
    assert verify_manifest(tmp_path)["files_verified"] == 1
    p.write_text("changed")
    with pytest.raises(ValueError):
        verify_manifest(tmp_path)
    p.write_text("{}"); (tmp_path/"extra.txt").write_text("x")
    with pytest.raises(ValueError):
        verify_manifest(tmp_path)


def test_archived_gate_flags_recomputed():
    x = np.zeros((1,36,6)); x[:,:,:2] = .5
    validity = np.ones((1,5))
    d = {k:v[0].tolist() for k,v in repaired_decision(x,x,np.repeat(range(6),6),validity).items()}
    assert archived_flags(d,validity[0])["joint"]
    bad = deepcopy(d); bad["joint_pass"] = False
    with pytest.raises(ValueError):
        archived_flags(bad,validity[0])
