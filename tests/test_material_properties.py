from coiloptimization_ import model


def test_steel_material_properties():
    props = model.get_material_properties("steel", 25.0)
    assert isinstance(props, dict)
    assert "k_w" in props
    assert props["k_w"] > 0
    # Steel typical thermal conductivity ~ 43 W/mK
    assert abs(props["k_w"] - 43.0) < 1.0
