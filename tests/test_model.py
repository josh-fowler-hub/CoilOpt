import math

from coiloptimization_ import model


def test_geometry_turn_length():
    L = model.turn_length(0.1, 0.02)
    assert L > 0


def test_total_length_and_area():
    L = model.total_length(10, 0.1, 0.02)
    A = model.external_area(0.01, L)
    assert L > 0 and A > 0


def test_reynolds_prandtl_and_nusselt_internal():
    # water-like properties
    m_dot = 0.1
    rho = 1000.0
    D_i = 0.01
    mu = 1e-3
    cp = 4182.0
    k = 0.6
    u, Re = model.reynolds_from_mass_flow(m_dot, rho, D_i, mu)
    Pr = model.prandtl(cp, mu, k)
    Nu = model.nusselt_internal(Re, Pr)
    assert Re > 0
    assert Pr > 0
    assert Nu > 0


def test_nusselt_external_and_h():
    Re_D = 1000
    Pr = 7
    Nu = model.nusselt_external(Re_D, Pr)
    h = model.h_from_nusselt(Nu, 0.6, 0.01)
    assert Nu > 0 and h > 0


def test_U_overall_and_pressure_drop():
    h_i = 100
    h_o = 50
    D_i = 0.008
    D_o = 0.01
    k_w = 15.0
    U = model.U_overall(h_i, h_o, D_i, D_o, k_w)
    assert U > 0

    m_dot = 0.1
    rho = 1000
    D = D_i
    L = 10
    _, Re = model.reynolds_from_mass_flow(m_dot, rho, D, 1e-3)
    f = model.friction_factor(Re)
    dp = model.pressure_drop(m_dot, rho, D, L, f)
    assert dp >= 0


def test_pump_power():
    m_dot = 0.1
    rho = 1000
    dp = 10000
    P = model.pump_power(m_dot, dp, rho)
    assert P > 0
