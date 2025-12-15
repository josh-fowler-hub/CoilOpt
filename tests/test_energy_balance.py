from coiloptimization_ import model, profiles


def test_energy_balance_constant():
    m_dot = 0.5
    cp = 1000
    Tin = 400.0
    L = 10.0
    D_o = 0.02
    U = 50.0
    Tinf = 300.0

    xs, Ths = model.solve_energy_balance(m_dot, cp, Tin, L, D_o, U, Tinf, nsteps=1000)
    Tout_num = Ths[-1]
    Tout_anal = model.analytical_outlet_temp_constant(Tin, Tinf, U, D_o, L, m_dot, cp)
    assert abs(Tout_num - Tout_anal) < 1e-2


def test_energy_balance_with_profile_equation():
    m_dot = 0.5
    cp = 1000
    Tin = 400.0
    L = 10.0
    D_o = 0.02
    U = 50.0
    # Tinf varies: polynomial/exponential-like expression
    eq = "300 + 50*exp(-x/5)"
    Tinf_func = profiles.make_profile_from_equation(eq)
    xs, Ths = model.solve_energy_balance(m_dot, cp, Tin, L, D_o, U, Tinf_func, nsteps=500)
    # ensure monotonic decrease from Tin towards local Tinf values
    assert Ths[0] == Tin
    assert Ths[-1] < Tin