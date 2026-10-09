"""Inverse performance calculation for an existing nozzle geometry."""

from dataclasses import dataclass
import math

from .constants import COEF_J_DEFAULT


SEA_LEVEL_PRESSURE_MPA = 0.0981


@dataclass(frozen=True)
class InverseResult:
    T_k: float
    mass_flow: float
    total_mass_flow: float
    chamber_count: int
    fa: float
    eps: float
    p_a: float
    J_pr_ud_st: float
    J_r_ud: float
    J_SL: float
    J_vac: float
    P_SL_per_chamber: float
    P_vac_per_chamber: float
    P_SL: float
    P_vac: float
    iterations: int


def solve_exit_pressure_ratio(fa, k, tolerance=1e-12, max_iterations=100):
    """Solve the area-ratio equation on its supersonic branch by Newton's method."""
    if not math.isfinite(fa) or fa <= 1:
        raise ValueError("nozzle expansion ratio must be greater than one")
    if not math.isfinite(k) or k <= 1:
        raise ValueError("specific heat ratio must be greater than one")

    right_part = (
        (2 / (k + 1)) ** ((k + 1) / (k - 1))
        * ((k - 1) / 2)
        / fa ** 2
    )
    eps_critical = (2 / (k + 1)) ** (k / (k - 1))
    eps = min(0.02, eps_critical / 2)

    for iteration in range(1, max_iterations + 1):
        value = eps ** (2 / k) - eps ** ((k + 1) / k) - right_part
        derivative = (
            (2 / k) * eps ** (2 / k - 1)
            - ((k + 1) / k) * eps ** ((k + 1) / k - 1)
        )
        eps_new = eps - value / derivative
        if not math.isfinite(eps_new) or not 0 < eps_new < eps_critical:
            boundary = 1e-12 if not math.isfinite(eps_new) or eps_new <= 0 else eps_critical
            eps_new = (eps + boundary) / 2
        if abs(eps_new - eps) < tolerance:
            return eps_new, iteration
        eps = eps_new

    raise RuntimeError("Newton method did not converge")


def calculate_inverse_nozzle(
    D_kr, D_a, p_k, T_st, R, k, J_st_ud,
    coefJ=COEF_J_DEFAULT, chamber_count=1, p_0=SEA_LEVEL_PRESSURE_MPA,
):
    """Calculate performance from propellant data and fixed nozzle diameters."""
    values = (D_kr, D_a, p_k, T_st, R, k, J_st_ud, coefJ, chamber_count)
    if not all(math.isfinite(float(value)) for value in values):
        raise ValueError("all input values must be finite")
    if D_kr <= 0 or D_a <= D_kr:
        raise ValueError("exit diameter must be greater than throat diameter")
    if p_k <= p_0:
        raise ValueError("chamber pressure must be greater than sea-level pressure")
    if T_st <= 0 or R <= 0 or J_st_ud <= 0 or k <= 1:
        raise ValueError("thermodynamic inputs must be positive")
    if not 0 < coefJ <= 1:
        raise ValueError("specific impulse coefficient must be between zero and one")
    if chamber_count <= 0 or not float(chamber_count).is_integer():
        raise ValueError("number of chambers must be a positive integer")
    chamber_count = int(chamber_count)

    T_k = T_st * (86.9 - 0.578 * p_k + 6.27 * math.sqrt(p_k)) / 100.0
    if T_k <= 0:
        raise ValueError("calculated chamber temperature must be positive")
    K_0 = (2 / (k + 1)) ** ((k + 1) / (2 * (k - 1))) * math.sqrt(k)
    mass_flow = (
        0.98 * math.pi * K_0 * p_k * D_kr ** 2
        / (4 * math.sqrt(T_k * R))
    )

    fa = (D_a / D_kr) ** 2
    eps, iterations = solve_exit_pressure_ratio(fa, k)
    p_a = eps * p_k
    k1 = (k - 1) / k

    J_pr_ud_st = coefJ * J_st_ud
    impulse_factor = (
        (1 - eps ** k1) * p_k ** k1
        / (p_k ** k1 - p_0 ** k1)
    )
    if impulse_factor <= 0:
        raise ValueError("specific impulse cannot be calculated for these pressures")
    J_r_ud = (
        J_pr_ud_st
        * (0.67 - 0.016 * p_k + 0.163 * math.sqrt(p_k))
        * math.sqrt(impulse_factor)
    )
    delta_J = R * T_k * eps ** k1 / J_r_ud
    J_vac = J_r_ud + delta_J
    J_SL = J_vac - delta_J * p_0 / p_a
    P_SL_per_chamber = mass_flow * J_SL
    P_vac_per_chamber = mass_flow * J_vac

    return InverseResult(
        T_k=T_k,
        mass_flow=mass_flow,
        total_mass_flow=mass_flow * chamber_count,
        chamber_count=chamber_count,
        fa=fa,
        eps=eps,
        p_a=p_a,
        J_pr_ud_st=J_pr_ud_st,
        J_r_ud=J_r_ud,
        J_SL=J_SL,
        J_vac=J_vac,
        P_SL_per_chamber=P_SL_per_chamber,
        P_vac_per_chamber=P_vac_per_chamber,
        P_SL=P_SL_per_chamber * chamber_count,
        P_vac=P_vac_per_chamber * chamber_count,
        iterations=iterations,
    )
