from typing import Any, Dict


def _temp_to_celsius(val: float, unit: str) -> float:
    """Convert a temperature value from the given unit to degrees Celsius.

    Supports Kelvin (K) and Fahrenheit (F) and assumes Celsius if unknown.
    """
    if unit is None:
        return float(val)
    key = unit.strip().lower()
    if key in ("kelvin", "k"):
        return float(val) - 273.15
    if key in ("fahrenheit", "f"):
        return (float(val) - 32.0) * 5.0 / 9.0
    # assume already celsius
    return float(val)


def _length_to_meters_factor(unit: str) -> float:
    u = unit.strip().lower()
    if u in ("m", "meter", "meters"):
        return 1.0
    if u in ("cm", "centimeter", "centimeters"):
        return 0.01
    if u in ("mm", "millimeter", "millimeters"):
        return 0.001
    if u in ("in", "inch", "inches"):
        return 0.0254
    if u in ("ft", "foot", "feet"):
        return 0.3048
    raise ValueError(f"Unsupported length unit: {unit}")


def _mass_to_kg_factor(unit: str) -> float:
    u = unit.strip().lower()
    if u in ("kg", "kilogram", "kilograms"):
        return 1.0
    if u in ("g", "gram", "grams"):
        return 0.001
    if u in ("lb", "lbs", "pound", "pounds"):
        return 0.45359237
    raise ValueError(f"Unsupported mass unit: {unit}")


def _time_to_seconds_factor(unit: str) -> float:
    u = unit.strip().lower()
    if u in ("s", "sec", "second", "seconds"):
        return 1.0
    if u in ("min", "minute", "minutes"):
        return 60.0
    if u in ("h", "hr", "hour", "hours"):
        return 3600.0
    raise ValueError(f"Unsupported time unit: {unit}")


def _pressure_to_pa_factor(unit: str) -> float:
    u = unit.strip().lower()
    if u in ("pa", "pascal", "pascals"):
        return 1.0
    if u in ("kpa", "kilopascal"):
        return 1e3
    if u in ("mpa", "megapascal"):
        return 1e6
    if u in ("bar",):
        return 1e5
    if u in ("psi",):
        return 6894.76
    raise ValueError(f"Unsupported pressure unit: {unit}")


def _convert_temp_expression(expr: str, from_unit: str) -> str:
    # return a wrapped expression that converts expr_in_from_unit -> degrees C
    fu = from_unit.strip().lower()
    if fu in ("kelvin", "k"):
        return f"({expr}) - 273.15"
    if fu in ("fahrenheit", "f"):
        return f"(({expr}) - 32.0) * 5.0/9.0"
    # assume already Celsius
    return expr


def normalize_units(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize expected fields to SI units in place.

    Behavior:
    - Reads optional `raw['units']` table to discover input units.
    - Maps unitless keys (e.g., `mass_flow`, `inlet_temp`) to canonical names the
      rest of the code expects (e.g., `mass_flow_kg_s`, `inlet_temp_c`).
    - Converts temperatures from Kelvin to Celsius when units indicate Kelvin.
    - Converts pressure keys suffixes when necessary (placeholder, currently Pa expected).
    - Handles external temperature profile strings by wrapping with a -273.15
      adjustment when input temperatures are Kelvin.

    This function mutates and returns the dict for downstream validation.
    """
    units = raw.get("units") or {}
    temp_unit = units.get("temperature") if units else None

    # Normalize fluid/internal table keys
    if raw.get("fluid") is None and raw.get("internal") is not None:
        raw["fluid"] = raw["internal"]

    f = raw.get("fluid")
    if f:
        # mass_flow -> mass_flow_kg_s (convert units mass/time -> kg/s)
        if f.get("mass_flow_kg_s") is None and f.get("mass_flow") is not None:
            mass_unit = units.get("mass") if units else None
            time_unit = units.get("time") if units else None
            if mass_unit is None and time_unit is None:
                f["mass_flow_kg_s"] = float(f.get("mass_flow"))
            else:
                mf = float(f.get("mass_flow"))
                mass_factor = _mass_to_kg_factor(mass_unit) if mass_unit is not None else 1.0
                time_factor = _time_to_seconds_factor(time_unit) if time_unit is not None else 1.0
                # input is mass_unit per time_unit -> convert to kg/s
                f["mass_flow_kg_s"] = mf * mass_factor / time_factor
        # inlet_temp -> inlet_temp_c
        if f.get("inlet_temp_c") is None and f.get("inlet_temp") is not None:
            f["inlet_temp_c"] = _temp_to_celsius(float(f.get("inlet_temp")), temp_unit)
        if f.get("outlet_temp_c") is None and f.get("outlet_temp") is not None:
            f["outlet_temp_c"] = _temp_to_celsius(float(f.get("outlet_temp")), temp_unit)

    # Normalize external temperature profile and temperature fields
    ex = raw.get("external")
    if ex:
        # map temperature key
        if ex.get("temperature_c") is None and ex.get("temperature") is not None:
            ex["temperature_c"] = _temp_to_celsius(float(ex.get("temperature")), temp_unit)

        # handle profile strings: allow Tinf_profile alias; if profile is a string
        # and units are not Celsius, wrap expression to convert to Celsius
        profile = ex.get("temperature_profile") or ex.get("Tinf_profile") or ex.get("tinf_profile")
        if profile is not None:
            # If profile is a string equation, and temperature unit is Kelvin or Fahrenheit,
            # convert the expression into Celsius
            if isinstance(profile, str):
                if temp_unit:
                    ex["temperature_profile"] = _convert_temp_expression(profile, temp_unit)
                else:
                    ex["temperature_profile"] = profile
            else:
                # assume structured points; if units are not Celsius, convert point temps
                if isinstance(profile, list) and temp_unit:
                    pts = []
                    for p in profile:
                        p2 = dict(p)
                        if p2.get("temp_c") is None and p2.get("temp") is not None:
                            p2["temp_c"] = _temp_to_celsius(float(p2.get("temp")), temp_unit)
                        pts.append(p2)
                    ex["temperature_profile"] = pts
                else:
                    ex["temperature_profile"] = profile

    # Map design_bounds keys without units to canonical names expected elsewhere
    db = raw.get("design_bounds")
    if db:
        length_unit = units.get("length") if units else None
        factor = _length_to_meters_factor(length_unit) if length_unit is not None else 1.0
        if db.get("min_tube_od_m") is None and db.get("min_tube_od") is not None:
            db["min_tube_od_m"] = float(db.get("min_tube_od")) * factor
        if db.get("max_tube_od_m") is None and db.get("max_tube_od") is not None:
            db["max_tube_od_m"] = float(db.get("max_tube_od")) * factor
        if db.get("min_pitch_m") is None and db.get("min_pitch") is not None:
            db["min_pitch_m"] = float(db.get("min_pitch")) * factor
        if db.get("max_pitch_m") is None and db.get("max_pitch") is not None:
            db["max_pitch_m"] = float(db.get("max_pitch")) * factor
        if db.get("min_coil_diameter_m") is None and db.get("min_coil_diameter") is not None:
            db["min_coil_diameter_m"] = float(db.get("min_coil_diameter")) * factor
        if db.get("max_coil_diameter_m") is None and db.get("max_coil_diameter") is not None:
            db["max_coil_diameter_m"] = float(db.get("max_coil_diameter")) * factor
        if db.get("min_wall_thickness_m") is None and db.get("min_wall_thickness") is not None:
            db["min_wall_thickness_m"] = float(db.get("min_wall_thickness")) * factor

    # Map constraints
    c = raw.get("constraints")
    if c:
        pressure_unit = units.get("pressure") if units else None
        if c.get("max_pressure_drop_pa") is None and c.get("max_pressure_drop") is not None:
            factor = _pressure_to_pa_factor(pressure_unit) if pressure_unit is not None else 1.0
            c["max_pressure_drop_pa"] = float(c.get("max_pressure_drop")) * factor
        if c.get("max_surface_temp_c") is None and c.get("max_surface_temp") is not None:
            c["max_surface_temp_c"] = _temp_to_celsius(float(c.get("max_surface_temp")), temp_unit)
    # Map coil keys aliases (coil_entry_height, coil_exit_height -> entry_height_m)
    coil = raw.get("coil")
    if coil:
        length_unit = units.get("length") if units else None
        factor = _length_to_meters_factor(length_unit) if length_unit is not None else 1.0
        if coil.get("entry_height_m") is None and coil.get("coil_entry_height") is not None:
            coil["entry_height_m"] = float(coil.get("coil_entry_height")) * factor
        if coil.get("exit_height_m") is None and coil.get("coil_exit_height") is not None:
            coil["exit_height_m"] = float(coil.get("coil_exit_height")) * factor
        # derive direction if not provided
        if coil.get("direction") is None and coil.get("entry_height_m") is not None and coil.get("exit_height_m") is not None:
            coil["direction"] = "up" if coil["exit_height_m"] > coil["entry_height_m"] else "down"

    # material/interface key normalization: accept wall_thickness and convert to meters
    mat = raw.get("material") if raw.get("material") is not None else raw.get("interface")
    if isinstance(mat, dict):
        length_unit = units.get("length") if units else None
        factor = _length_to_meters_factor(length_unit) if length_unit is not None else 1.0
        if mat.get("wall_thickness_m") is None and mat.get("wall_thickness") is not None:
            mat["wall_thickness_m"] = float(mat.get("wall_thickness")) * factor
        # ensure the selected canonical key exists back in raw.material (preserve aliasing)
        if raw.get("material") is None and raw.get("interface") is not None:
            raw["material"] = raw.get("interface")
    return raw
