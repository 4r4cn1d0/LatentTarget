import math
from pathlib import Path

import numpy as np
import pytest

from src.stratified_intervals import t_critical, variance_components, stratified_interval, repaired_decision
from src.partner_statistics import bootstrap_distribution
from scripts.repair_partner_calibration import load_config, calibration_cell, coverage_cell

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("df,critical", [(5,(2.571,3.365,4.032)), (11,(2.201,2.718,3.106)),
                                        (23,(2.069,2.500,2.807)), (47,(2.012,2.408,2.685))])
def test_nist_table(df, critical):
    for alpha, expected in zip((.05,.02,.01), critical):
        assert t_critical(df, alpha) == pytest.approx(expected, abs=.00051)


@pytest.mark.parametrize("df", [5,11,23,47])
def test_primary_critical_independent_simpson(df):
    q = t_critical(df, .025)
    x = np.linspace(0, q, 20001)
    f = math.exp(math.lgamma((df+1)/2)-math.lgamma(df/2))/math.sqrt(df*math.pi)*(1+x*x/df)**(-(df+1)/2)
    integral = q/20000/3 * (f[0]+f[-1]+4*f[1:-1:2].sum()+2*f[2:-1:2].sum())
    assert .5+integral == pytest.approx(.9875, abs=1e-10)


def test_direct_unequal_strata_variance_and_interval():
    x = np.array([0.,1.,2.,3.,4.,5., *([1.,3.]*6)])
    strata = np.array([0]*6+[1]*12)
    v = (6/18)**2*np.var(x[:6],ddof=1)/6+(12/18)**2*np.var(x[6:],ddof=1)/12
    info = variance_components(x, strata)
    assert info["df"] == 5
    assert info["variance"][0] == pytest.approx(v)
    np.testing.assert_allclose(stratified_interval(x,strata)[0], x.mean()+np.array([-1,1])*t_critical(5)*np.sqrt(v))


def test_exact_bootstrap_variance_identity():
    x = np.random.default_rng(17).integers(-4,5,36)/4
    strata = np.repeat(range(6),6)
    support, mass = bootstrap_distribution(x,strata)
    info = variance_components(x,strata)
    exact = np.dot((support-x.mean())**2,mass[0])
    assert exact == pytest.approx(info["empirical_bootstrap_variance"][0], abs=1e-12)
    assert exact == pytest.approx(info["variance"][0]*5/6, abs=1e-12)


def test_point_interval_explicit_and_gate_edges():
    strata = np.repeat(range(6),6)
    x = np.zeros((1,36,6)); x[:,:,:2] = .1
    valid = np.ones((1,5))
    assert repaired_decision(x,x,strata,valid)["joint_pass"][0]
    assert variance_components(x[:,:,0],strata)["zero_variance"][0]
    x[:,:,0] = .099
    assert not repaired_decision(x,x,strata,valid)["joint_pass"][0]
    x[:,:,0] = .1; valid[0,2] = .979
    assert not repaired_decision(x,x,strata,valid)["joint_pass"][0]
    valid[:] = 1; hi = x.copy(); hi[:,:,3] = .101
    assert not repaired_decision(x,hi,strata,valid)["joint_pass"][0]
    assert not repaired_decision(-np.ones_like(x), np.ones_like(x), strata, np.zeros_like(valid))["joint_pass"][0]


@pytest.mark.parametrize("x,s", [([],[]), ([1,float('nan')],[0,0]), ([0]*6,[0]*5),
                                ([0]*6,["s"]*6), ([0]*5,[0]*5)])
def test_invalid_variance_inputs(x,s):
    with pytest.raises(ValueError):
        variance_components(x,s)


@pytest.mark.parametrize("df,alpha", [(4,.05),(5,0),(5,.3),(5.5,.05)])
def test_invalid_critical_inputs(df,alpha):
    with pytest.raises(ValueError):
        t_critical(df,alpha)


def test_deterministic_paired_cells_and_coverage():
    _, cfg = load_config(ROOT/"docs/partner_repair_20260908.json")
    a = calibration_cell(cfg,cfg["scenarios"][0],36,8)
    assert a == calibration_cell(cfg,cfg["scenarios"][0],36,8)
    assert len(a[1]) == 8 and len(a[0]) == 2
    assert sum(a[2][k] for k in ("new_only_pass","old_only_pass","both_pass","neither_pass")) == 8
    c = coverage_cell(cfg,"bernoulli",.1,36,8)
    assert c == coverage_cell(cfg,"bernoulli",.1,36,8)
    assert len(c[1]) == 8 and all(r["nominal_coverage"] == .975 for r in c[0])
