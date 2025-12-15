from coiloptimization_ import model


def test_wall_temperatures_consistency():
    Th = 350.0
    Tinf = 300.0
    h_i = 100.0
    h_o = 50.0
    D_i = 0.008
    D_o = 0.01
    k_w = 15.0

    Tw_i, Tw_o = model.wall_temperatures(Th, Tinf, h_i, h_o, D_i, D_o, k_w)
    assert Tw_o >= Tinf
    assert Tw_i <= Th
    # conduction check: Tw_i - Tw_o should equal q'' * R_cond_area
    R_cond_per_length = model.conduction_resistance_per_length(D_o, D_i, k_w)
    R_cond_area = R_cond_per_length / (3.141592653589793 * D_o)
    qpp = (Th - Tinf) / (1.0 / h_i + R_cond_area + 1.0 / h_o)
    assert abs((Tw_i - Tw_o) - qpp * R_cond_area) < 1e-6
