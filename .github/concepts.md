# Modeling & Concepts — CoilOptimization

## Purpose

- Capture the physics, assumptions, and approximations used by the optimizer; provide the mathematical primitives needed to compute heat transfer and pressure drop for coil geometries.

## Overview of the physical problem

- We consider a helical tube (coil) carrying a hot flue gas internally and interacting with a colder external fluid (typically water). Heat is transferred from the hot gas -> tube wall -> external fluid. The optimization problem we will implement is:

  - Inputs (fixed): hot gas mass flow and inlet temperature (hot side), external fluid properties (water) and boundary condition (bath temperature or external flow conditions).
  - Design variables: tube outer diameter, wall thickness, coil diameter, axial pitch, number of turns, etc.
  - Objective: maximize heat transferred from the hot gas to the external water (maximize Q) subject to constraints.

- Important: this project models the heat exchanger only — we do not model a pump or include pumping power in the objective. Pressure-drop constraints apply to the hot (internal) flow and may be specified by the user.

## Design variables (examples)

- `D_o` : tube outer diameter (m)
- `t` : tube wall thickness (m)
- `D_i = D_o - 2t` : tube inner diameter (m)
- `D_c` : coil (helix) diameter (m)
- `p` : axial pitch between turns (m)
- `N` : number of turns (integer)

Derived geometry

- Tube length per turn: $\ell_{turn} = \sqrt{(\pi D_c)^2 + p^2}$
- Total tube length: $L = N\,\ell_{turn}$
- External heat transfer area (outer): $A_o = \pi D_o L$

## Governing heat transfer relations

- Heat duty from hot gas to cold water (energy balance):

  - By fluid energy: $Q = \dot m c_p (T_{in}-T_{out})$ for the hot gas (or for water depending on which side we track).
  - By overall conductance: $Q = U A_o \Delta T_{lm}$, where $\Delta T_{lm}$ is the log-mean temperature difference for the chosen flow arrangement.

- Overall heat-transfer coefficient $U$ accounts for series resistances:

$$
\frac{1}{U A_o} = \frac{1}{h_i A_i} + \frac{\ln(r_o/r_i)}{2\pi k_w L} + \frac{1}{h_o A_o} + R_{fouling}
$$

Where per-unit-length forms (useful for coding) lead to the common cylindrical form:

$$
\frac{1}{U\,\pi D_o} = \frac{1}{h_i\,\pi D_i} + \frac{\ln(D_o/D_i)}{2\pi k_w} + \frac{1}{h_o\,\pi D_o} + r_{foul}
$$

Definitions and properties:

- $h_i$ : internal convective heat transfer coefficient (W/m^2K)
- $h_o$ : external convective heat transfer coefficient (W/m^2K)
- $k_w$ : thermal conductivity of tube wall material (W/mK)
- $D_i, D_o$ : inner/outer diameters (m)
- $r_{foul}$ : combined fouling resistance term (m^2K/W)

## Correlations for convection

- Internal flow (inside tube): use appropriate correlation by flow regime

  - Reynolds number: $\displaystyle Re_i = \frac{\rho_i u_i D_i}{\mu_i}$ where $u_i = \dot m / (\rho_i A_i)$ and $A_i=\pi D_i^2/4$.
  - Prandtl: $Pr = c_p \mu / k$.

  - Turbulent (typical engineering choice): Dittus–Boelter

  $$
  Nu_i = 0.023\, Re_i^{0.8} Pr^{n},\quad n=0.4\;\text{(heating)},\;0.3\;\text{(cooling)}
  $$

  - Laminar/internal: use Sieder–Tate or fully-developed solutions when $Re < 2300$.

  - Convert $Nu_i$ to $h_i$: $h_i = \dfrac{Nu_i k_i}{D_i}$.

- External (coil surface in water) — cross-flow or forced convection over a cylinder approximation with curvature corrections for a helix

  - Cylinder cross-flow (Churchill–Bernstein):

  $$
  Nu_o = 0.3 + \frac{0.62 Re_D^{1/2} Pr^{1/3}}{[1 + (0.4/Pr)^{2/3}]^{1/4}}\left[1 + \left(\frac{Re_D}{282000}\right)^{5/8}\right]^{4/5}
  $$

  - Here $Re_D = \dfrac{\rho_o u_o D_o}{\mu_o}$ uses a characteristic velocity $u_o$ representative of the external flow.

  - Convert $Nu_o$ to $h_o$: $h_o = \dfrac{Nu_o k_o}{D_o}$.

Notes: for tightly-packed helical coils, use helix-correction factors for $Nu_o$ and pressure drop; treat these as optional multipliers or calibration coefficients in the model.

## Thermal resistance of tube wall

- For a cylindrical tube per unit length, conduction resistance is:

$$
R_{cond, per\ unit\ length} = \frac{\ln(r_o/r_i)}{2\pi k_w}
$$

with $r_o = D_o/2$, $r_i = D_i/2$.

## Temperature driving potential

- For single-pass coil in a large bath, LMTD is commonly used. If internal and external mass flows are known and approximately constant, compute:

$$
\Delta T_{lm} = \frac{\Delta T_1 - \Delta T_2}{\ln(\Delta T_1/\Delta T_2)}
$$

Where $\Delta T_1$ and $\Delta T_2$ are endpoint temperature differences (hot minus cold) at the two ends.

Alternative: for small systems, directly solve energy balance along the coil using an ODE and local $U(T)$ if nonlinear.

## Hydraulic model — pressure drop

- Use Darcy–Weisbach form for pressure drop along the tube:

$$
\Delta P = f \frac{L}{D_h} \frac{\rho u^2}{2}
$$

Where $f$ is the friction factor (use Blasius or Moody correlations):

- For turbulent smooth pipes (Blasius): $f \approx 0.3164 Re^{-0.25}$ (valid for $3000 \lesssim Re \lesssim 10^5$).
- For laminar: $f = 64/Re$.

For helical coils, include curvature correction factor $\phi_c(Re,\delta)$ so $f_{coil} = f_{straight} \cdot \phi_c$; document the coefficient and default to $\phi_c=1$ if unknown.

Convert pressure-drop constraint into a solver constraint: $\Delta P(x) - \Delta P_{max} \le 0$.

## Objective(s)

- Maximize transferred heat $Q(x)$
- Cost-based objectives (pumping power, material cost) are not supported and should not appear in inputs or outputs; the primary objective is to maximize transferred heat $Q(x)$.

## Constraints

- Geometric: bounds on $D_o, t, D_c, p, N$ (from TOML file)
- Hydraulic: $\Delta P \le \Delta P_{max}$
- Thermal: $T_{wall,max} \le T_{allowable}$ (compute maximum wall temperature using thermal resistances)
- Manufacturability: $t \ge t_{min}$, discrete $N$ integer

## Numerical considerations and implementation plan

- Build modular functions:
  - `geometry(x)` — derive $L$, $A_o$, etc.
  - `fluid_props(T, fluid)` — return $\rho, \mu, k, c_p$ (interpolated or constant)
  - `reynolds(...)`, `nusselt_internal(...)`, `nusselt_external(...)`
  - `U_overall(...)` — compute $U$ from $h_i, h_o, k_w, D_i, D_o, r_{foul}`
  - `Q_from_U(...)` and `Q_from_energy_balance(...)`
  - `pressure_drop(...)`

- Use vectorized numpy implementations where useful for multi-start evaluation.
- Provide analytic derivatives where possible (e.g., derivatives of geometry and area). For convective correlations provide numeric gradients by default.
- Implement a small ODE-based solver option to compute local temperature profiles along the coil for higher fidelity (optional, slower).

## Validation and test cases

- Straight-tube benchmark: validate internal $Nu$ and $\Delta P$ against textbook examples.
- Coil benchmark: compare against approximate published helical coil correlations when available.
- Unit tests for each primitive (geometry, Re, Nu, U, Q, ΔP).

## Practical modeling defaults

- Default to Dittus–Boelter for internal turbulent flow when $Re>3000$ and Sieder–Tate for laminar or transitional regimes.
- Use Churchill–Bernstein for external cylinder cross-flow unless user provides a coil-correction factor.
- Default fouling resistance to zero but allow user override in TOML.
