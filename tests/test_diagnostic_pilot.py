from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

from scripts.build_diagnostic_packet import build
from src.diagnostic_pilot import (validate_packet, collect, MockChoiceProvider, digest, write_new,
                                  read, verify_package, check_approval)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def packet_dir(tmp_path_factory):
    out = tmp_path_factory.mktemp("packet_parent") / "prepared"
    build(ROOT/"results/grounded_partner_readiness_20260908", ROOT/"docs/diagnostic_pilot_20260908.json", out)
    return out


@pytest.fixture
def packet(packet_dir):
    return read(packet_dir/"package/packet.json")


def test_three_complete_bundles_and_independent_families(packet):
    assert validate_packet(packet)
    assert len(set(packet["provenance"]["selected_families"])) == 3
    assert not any(r["spec"]["branch"] == "FORECAST" for r in packet["requests"])


def test_full_mock_then_resume_performs_no_extra_calls(packet, tmp_path):
    calls = []
    class Provider(MockChoiceProvider):
        def generate(self, prompt):
            assert set(vars(prompt)) == {"system", "user", "context"} and prompt.context == {}
            calls.append(prompt)
            return super().generate(prompt)
    first = collect(packet, tmp_path, provider_factory=Provider)
    assert len(calls) == 60 and first["status"] == "COMPLETE"
    assert first == collect(packet, tmp_path, provider_factory=Provider)
    assert len(calls) == 60
    assert len(list(tmp_path.glob("*.response.json"))) == 60


def test_interruption_and_resume_same_exact_outputs(packet, tmp_path):
    a, b = tmp_path/"interrupted", tmp_path/"continuous"
    assert collect(packet, a, stop_after=7)["responses"] == 7
    collect(packet, a)
    collect(packet, b)
    for i in range(60):
        x, y = (read(p/f"{i:03d}.response.json") for p in (a,b))
        assert x["seed"] == y["seed"] and x["raw_response"] == y["raw_response"]


@pytest.mark.parametrize("raw", ["1\n", "Option 1", "", "4", None])
def test_invalid_generation_saved_and_never_retried(packet, tmp_path, raw):
    calls=[]
    class Bad(MockChoiceProvider):
        def generate(self, prompt):
            calls.append(1)
            return raw
    with pytest.raises(RuntimeError, match="strict digit"):
        collect(packet, tmp_path, provider_factory=Bad)
    assert read(tmp_path/"000.response.json")["status"] == "INVALID_OR_FAILED"
    with pytest.raises(RuntimeError, match="no replacement"):
        collect(packet, tmp_path, provider_factory=Bad)
    assert len(calls) == 1


def test_uncertain_claim_cannot_repeat(packet, tmp_path):
    class Interrupted(MockChoiceProvider):
        def generate(self, prompt):
            raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        collect(packet, tmp_path, provider_factory=Interrupted)
    assert (tmp_path/"000.claim.json").exists() and not (tmp_path/"000.response.json").exists()
    with pytest.raises(RuntimeError, match="uncertain"):
        collect(packet, tmp_path)


@pytest.mark.parametrize("change", ["duplicate", "missing", "prompt", "capture", "model", "metadata", "order"])
def test_corrupted_packet_rejected_before_output(packet, tmp_path, change):
    p = deepcopy(packet)
    if change == "duplicate":p["requests"][1] = p["requests"][0]
    elif change == "missing":p["requests"].pop()
    elif change == "prompt":p["requests"][0]["prompt"]["user"] += "altered"
    elif change == "capture":p["config"]["generation"]["capture"] = True
    elif change == "model":p["config"]["model"] = "older-model"
    elif change == "metadata":p["requests"][0]["prompt"]["hidden_type"] = "risk"
    else:p["requests"].reverse()
    with pytest.raises(ValueError):collect(p, tmp_path/"unused")
    assert not (tmp_path/"unused").exists()


def test_record_tamper_and_unknown_file_rejected(packet, tmp_path):
    collect(packet, tmp_path, stop_after=1)
    r=read(tmp_path/"000.response.json");r["raw_response"]="3" if r["raw_response"]!="3" else "1"
    (tmp_path/"000.response.json").write_text(json.dumps(r))
    with pytest.raises(ValueError, match="hash mismatch"):collect(packet, tmp_path)


def test_no_real_mode_without_approval_or_with_mock_injection(packet, tmp_path):
    with pytest.raises(ValueError):collect(packet, tmp_path, mode="hf")
    with pytest.raises(ValueError):collect(packet, tmp_path, mode="hf", provider_factory=MockChoiceProvider)
    assert not list(tmp_path.iterdir())


def test_approval_price_deadline_and_watchdog_checks(packet):
    sha=validate_packet(packet)
    approval=dict(packet_sha256=sha, approved=True, pod_id="test-pod", maximum_requests=60,
                  maximum_total_usd=5., hourly_quote_usd=1.59,
                  pod_deadline_utc=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),
                  stop_watchdog_verified=True, results_on_persistent_volume=True)
    check_approval(approval, sha)
    for k,v in (("hourly_quote_usd",3),("maximum_total_usd",float("nan")),("approved",False),
                ("stop_watchdog_verified",False),("packet_sha256","different"),("maximum_requests",61),
                ("pod_deadline_utc",datetime.now().isoformat())):
        with pytest.raises(ValueError):check_approval(dict(approval,**{k:v}),sha)


def test_portable_archive_verifies_and_mock_runs_without_repo(packet_dir, tmp_path):
    with tarfile.open(packet_dir/"latenttarget_diagnostic_20260908.tar.gz") as f:
        f.extractall(tmp_path, filter="data")
    package=tmp_path/"package"
    result=subprocess.run([sys.executable,str(package/"scripts/run_diagnostic_pilot.py"),"--mode","mock","--output",str(tmp_path/"output")],
                          cwd=tmp_path,text=True,capture_output=True,check=True)
    assert read(tmp_path/"output/complete.json")["responses"]==60
    assert '"mode": "mock"' in result.stdout
    verify_package(package)
    (package/"secret.env").write_text("fixture only")
    with pytest.raises(ValueError,match="unexpected"):verify_package(package)


def test_package_file_tamper_rejected(packet_dir, tmp_path):
    with tarfile.open(packet_dir/"latenttarget_diagnostic_20260908.tar.gz") as f:f.extractall(tmp_path,filter="data")
    (tmp_path/"package/config.py").write_text("changed")
    with pytest.raises(ValueError,match="hash"):verify_package(tmp_path/"package")
