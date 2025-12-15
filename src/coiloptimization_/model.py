"""Mathematical model primitives for CoilOptimization.

Provides geometry helpers, Reynolds/Nusselt correlations, overall U, and pressure-drop.
"""
from __future__ import annotations

import math
from typing import Tuple, Callable




def water_properties(T: float) -> tuple:
    """Water properties (rho, cp, mu, k) at temperature T (degC)."""
    # Approximate values for water at room temperature (25 degC):

    def get_density(T):
        return 999.84 - 0.0672 * T - 0.00796 * T**2 + 2.53e-5 * T**3

    def get_cp(T):
        return 4181.3 - 0.33 * T + 1.2e-3 * T**2
    
    def get_viscosity(T):
        return 0.001792 * math.exp(-0.0268 * T + 0.000102 * T**2)
    
    def get_thermal_conductivity(T):
        return 0.5718 + 0.00175 * T - 6.14e-6 * T**2
    
    def get_thermal_expansion_coefficient(T):
        return 2.14e-4 + 1.45e-6 * T + 6.79e-8 * T**2  # 1/K
    
    def get_prandtl(cp, mu, k):
        return cp * mu / k

    rho = get_density(T)  # kg/m3
    cp = get_cp(T)  # J/kgK
    mu = get_viscosity(T)  # Pa*s
    k = get_thermal_conductivity(T)  # W/mK
    Pr = get_prandtl(cp, mu, k)
    return rho, cp, mu, k, Pr

def flue_gas_properties(T: float) -> tuple:
    """Flue gas properties (rho, cp, mu, k) at temperature T (degC)."""
    TK = T + 273.15  # Convert to Kelvin

    # Ideal-gas scaling for density at constant pressure (approx): rho ~ rho_ref * T_ref / TK
    rho_ref = 1.225  # kg/m3 at T_ref
    T_ref = 298.15  # K (~25 C)
    rho = rho_ref * (T_ref / TK)

    # Specific heat (approximate, J/kgK)
    cp = 908.300132 + 0.5195109999999999 * T - 0.000174 * T ** 2

    # Viscosity via Sutherland's law (air-like constants)
    mu0 = 1.6411e-05
    T0 = 273.1
    S = 219.7
    mu = mu0 * (TK / T0) ** 1.5 * (T0 + S) / (TK + S)

    # Thermal conductivity (approx)
    k = 0.07000000000000001

    Pr = cp * mu / k
    return rho, cp, mu, k, Pr

def air_properties(T: float) -> tuple:
    """Air properties (rho, cp, mu, k) at temperature T (degC)."""
    # Approximate values for air at room temperature (25 degC):
    rho = 1.225  # kg/m3
    cp = 1005.0  # J/kgK
    mu = 1.8e-5  # Pa*s
    k = 0.026  # W/mK
    return rho, cp, mu, k

def steam_properties(T: float) -> tuple:
    """Steam properties (rho, cp, mu, k) at temperature T (degC)."""
    # Approximate values for steam at 100 degC:
    rho = 0.598  # kg/m3
    cp = 2010.0  # J/kgK
    mu = 2.0e-5  # Pa*s
    k = 0.026  # W/mK
    return rho, cp, mu, k


def get_material_properties(name: str, T: float) -> dict:
    """Return material properties for solids (e.g., tube materials) by name.

    Returns a dictionary with keys like `k_w`, `rho`, `cp` as available.
    """
    if not name:
        return {"k_w": 15.0}
    key = name.strip().lower()
    if key in ("steel", "stainless_steel", "st" , "carbon_steel"):
        rho, cp, mu, k = steel_properties(T)
        return {"k_w": k, "rho": rho, "cp": cp}
    # Default fallback
    return {"k_w": 15.0}

def oil_properties(T: float) -> tuple:
    """Oil properties (rho, cp, mu, k) at temperature T (degC)."""
    # Approximate values for oil at room temperature (25 degC):
    rho = 850.0  # kg/m3
    cp = 2100.0  # J/kgK
    mu = 0.001  # Pa*s
    k = 0.16  # W/mK
    return rho, cp, mu, k

def steel_properties(T: float) -> tuple:
    """Steel properties (rho, cp, mu, k) at temperature T (degC).

    Return typical constant values for common steels. These are rough
    engineering defaults (room-temperature references)."""
    # Typical values (order-of-magnitude / room temperature)
    rho = 7850.0  # kg/m3
    cp = 490.0  # J/kgK
    # Solid 'viscosity' is not meaningful; provide a small placeholder so
    # interfaces that expect a numeric value won't crash. This is NOT a
    # physical dynamic viscosity for a solid.
    mu = 1.8e-5
    k = 43.0  # W/mK (approximate thermal conductivity for steel)
    return rho, cp, mu, k


def get_fluid_properties(name: str, T: float):
    """Return (rho, cp, mu, k, Pr) for known fluids by name (case-insensitive).

    Falls back to reasonable defaults when unknown.
    """
    if not name:
        return water_properties(T)
    key = name.strip().lower()
    if key in ("water", "h2o"):
        return water_properties(T)
    if key in ("flue_gas", "flue-gas", "gas"):
        return flue_gas_properties(T)
    if key in ("air",):
        rho, cp, mu, k = air_properties(T)
        Pr = cp * mu / k
        return rho, cp, mu, k, Pr
    if key in ("steam",):
        rho, cp, mu, k = steam_properties(T)
        Pr = cp * mu / k
        return rho, cp, mu, k, Pr
    if key in ("oil",):
        rho, cp, mu, k = oil_properties(T)
        Pr = cp * mu / k
        return rho, cp, mu, k, Pr
    # fallback to water
    return water_properties(T)


def turn_length(D_c: float, pitch: float) -> float:
    """Return length of one turn of a helix (m).

    ell_turn = sqrt((pi*D_c)^2 + p^2)
    """
    return math.hypot(math.pi * D_c, pitch)


def total_length(N: int, D_c: float, pitch: float) -> float:
    """Total tube length for N turns."""
    return N * turn_length(D_c, pitch)

def external_area(D_o: float, L: float) -> float:
    """External outer surface area (m^2)."""
    return math.pi * D_o * L


def reynolds_from_mass_flow(m_dot: float, rho: float, D_i: float, mu: float) -> Tuple[float, float]:
    """Compute average velocity and Reynolds number inside tube.

    Returns (u, Re)
    """
    A = math.pi * (D_i ** 2) / 4.0
    u = m_dot / (rho * A)
    Re = rho * u * D_i / mu
    return u, Re


def prandtl(cp: float, mu: float, k: float) -> float:
    """Prandtl number."""
    return cp * mu / k


def nusselt_internal(Re: float, Pr: float, heating: bool = True) -> float:
    """Internal Nusselt number.

    - For turbulent (Re >= 3000): Dittus–Boelter
    - For laminar (Re < 2300): assume fully-developed constant heat flux/temperature -> Nu = 3.66
    """
    if Re >= 3000:
        n = 0.4 if heating else 0.3
        return 0.023 * (Re ** 0.8) * (Pr ** n)
    # laminar approximation (fully-developed)
    return 3.66


def nusselt_external(Re_D: float, Pr: float) -> float:
    """External Nusselt using Churchill–Bernstein correlation for flow over a cylinder."""
    # Churchill–Bernstein
    term1 = 0.3
    term2 = (0.62 * (Re_D ** 0.5) * (Pr ** (1.0 / 3.0))) / ((1 + (0.4 / Pr) ** (2.0 / 3.0)) ** 0.25)
    term3 = (1 + (Re_D / 282000.0) ** (5.0 / 8.0)) ** (4.0 / 5.0)
    return term1 + term2 * term3


def h_from_nusselt(Nu: float, k: float, D: float) -> float:
    """Convective heat transfer coefficient (W/m2K)."""
    return Nu * k / D


def conduction_resistance_per_length(D_o: float, D_i: float, k_w: float) -> float:
    """Conduction resistance per unit length (m*K/W)."""
    return math.log(D_o / D_i) / (2.0 * math.pi * k_w)


def U_overall(h_i: float, h_o: float, D_i: float, D_o: float, k_w: float, r_foul: float = 0.0) -> float:
    """Compute overall heat transfer coefficient U (W/m2K) using cylindrical resistances."""
    # per-unit-length form (1 / (U * pi * D_o)) = 1/(h_i*pi*D_i) + ln(D_o/D_i)/(2*pi*k_w) + 1/(h_o*pi*D_o) + r_foul
    term_i = 1.0 / (h_i * math.pi * D_i)
    term_cond = math.log(D_o / D_i) / (2.0 * math.pi * k_w)
    term_o = 1.0 / (h_o * math.pi * D_o)
    R_total_per_length = term_i + term_cond + term_o + r_foul
    U = 1.0 / (R_total_per_length * math.pi * D_o)
    return U


def wall_temperatures(Th: float, Tinf: float, h_i: float, h_o: float, D_i: float, D_o: float, k_w: float) -> tuple:
    """Compute inner and outer wall temperatures given local bulk temperatures and convective coefficients.

    Returns (T_wall_inner, T_wall_outer)
    """
    # heat flux per unit area (outer basis): q'' = U_local * (Th - Tinf), but we don't have U here.
    # Instead, compute local heat flux per unit area based on series resistances:
    # q'' = (Th - Tinf) / (1/h_i + R_cond_area + 1/h_o)
    # where R_cond_area = conduction resistance per unit area (use outer-area basis):
    R_cond_per_length = conduction_resistance_per_length(D_o, D_i, k_w)
    R_cond_area = R_cond_per_length / (math.pi * D_o)
    R_total = 1.0 / h_i + R_cond_area + 1.0 / h_o
    qpp = (Th - Tinf) / R_total
    T_wall_outer = Tinf + qpp / h_o
    T_wall_inner = Th - qpp / h_i
    return T_wall_inner, T_wall_outer


def friction_factor(Re: float) -> float:
    """Approximate friction factor for smooth pipes: laminar and Blasius turbulent law."""
    if Re <= 0:
        raise ValueError("Re must be positive")
    if Re < 2300:
        return 64.0 / Re
    # Blasius (valid up to ~1e5)
    return 0.3164 * (Re ** -0.25)


def pressure_drop(m_dot: float, rho: float, D: float, L: float, f: float) -> float:
    """Darcy–Weisbach pressure drop (Pa) for given mass flow and friction factor.

    m_dot: mass flow (kg/s)
    rho: density (kg/m3)
    D: hydraulic diameter (m)
    L: length (m)
    f: friction factor
    """
    A = math.pi * D ** 2 / 4.0
    u = m_dot / (rho * A)
    return f * (L / D) * (rho * u ** 2 / 2.0)


def pump_power(m_dot: float, delta_p: float, rho: float) -> float:
    """Approximate pump power (W): volumetric flow * delta_p.

    m_dot: mass flow (kg/s)
    rho: density (kg/m3)
    """
    vol_flow = m_dot / rho
    return vol_flow * delta_p


def solve_energy_balance(
    m_dot: float,
    cp: float,
    Tin: float,
    L: float,
    D_o: float,
    U_func,
    Tinf_func,
    nsteps: int = 1000,
) -> tuple:
    """Solve 1D energy balance along tube length for hot fluid temperature Th(x).

    dTh/dx = - (U(x) * P) / (m_dot * cp) * (Th - Tinf(x))

    Parameters
    - m_dot: mass flow rate (kg/s)
    - cp: specific heat (J/kgK)
    - Tin: inlet temperature (degC)
    - L: total tube length (m)
    - D_o: outer diameter (m) (used to get perimeter P = pi*D_o)
    - U_func: callable U(x) or constant U value
    - Tinf_func: callable Tinf(x) or constant Tinf value
    - nsteps: number of integration steps for RK4

    Returns (x_array, Th_array)
    """
    if m_dot <= 0 or cp <= 0:
        raise ValueError("m_dot and cp must be positive")
    P = math.pi * D_o

    def get_U(x):
        return U_func(x) if callable(U_func) else U_func

    def get_Tinf(x):
        return Tinf_func(x) if callable(Tinf_func) else Tinf_func

    xs = [0.0]
    Ths = [Tin]
    dx = float(L) / nsteps
    Th = Tin
    for i in range(nsteps):
        x = i * dx

        def rhs(xi, Thi):
            return - (get_U(xi) * P) / (m_dot * cp) * (Thi - get_Tinf(xi))

        # RK4 step
        k1 = rhs(x, Th)
        k2 = rhs(x + dx / 2.0, Th + dx * k1 / 2.0)
        k3 = rhs(x + dx / 2.0, Th + dx * k2 / 2.0)
        k4 = rhs(x + dx, Th + dx * k3)
        Th = Th + (dx / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        xs.append(x + dx)
        Ths.append(Th)

    return xs, Ths


def solve_energy_balance_with_local(
    m_dot: float,
    cp: float,
    Tin: float,
    L: float,
    D_o: float,
    local_calc: Callable[[float, float], dict],
    nsteps: int = 1000,
) -> tuple:
    """Solve energy balance where local_calc(x, Th) supplies U, h_i, h_o, wall temps, and qpp.

    Returns (xs, Ths)
    """
    if m_dot <= 0 or cp <= 0:
        raise ValueError("m_dot and cp must be positive")
    P = math.pi * D_o

    xs = [0.0]
    Ths = [Tin]
    dx = float(L) / nsteps
    Th = Tin
    for i in range(nsteps):
        x = i * dx

        def rhs(xi, Thi):
            local = local_calc(xi, Thi)
            qpp = local["qpp"]
            qprime = qpp * P
            return - qprime / (m_dot * cp)

        # RK4 step
        k1 = rhs(x, Th)
        k2 = rhs(x + dx / 2.0, Th + dx * k1 / 2.0)
        k3 = rhs(x + dx / 2.0, Th + dx * k2 / 2.0)
        k4 = rhs(x + dx, Th + dx * k3)
        Th = Th + (dx / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        xs.append(x + dx)
        Ths.append(Th)

    return xs, Ths


def analytical_outlet_temp_constant(Tin: float, Tinf: float, U: float, D_o: float, L: float, m_dot: float, cp: float) -> float:
    """Analytical outlet temperature for constant U and constant Tinf.

    Tout = Tinf + (Tin - Tinf) * exp(- (U * P * L)/(m_dot * cp))
    """
    P = math.pi * D_o
    exponent = - (U * P * L) / (m_dot * cp)
    return Tinf + (Tin - Tinf) * math.exp(exponent)