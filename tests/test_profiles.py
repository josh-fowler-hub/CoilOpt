from coiloptimization_ import profiles


def test_eval_expression():
    f = profiles.make_profile_from_equation("300 - 10*x")
    assert f(0) == 300
    assert f(10) == 200


def test_points_interpolation():
    pts = [{"x_m": 0.0, "temp_c": 100.0}, {"x_m": 2.0, "temp_c": 80.0}, {"x_m": 5.0, "temp_c": 50.0}]
    f = profiles.make_profile_from_points(pts)
    assert f(0.0) == 100.0
    assert f(2.0) == 80.0
    assert abs(f(1.0) - 90.0) < 1e-6
    assert f(10.0) == 50.0
