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


@dataclass(frozen=True)
class AltitudeThrustCurve:
    altitude_km: tuple
    ambient_pressure_mpa: tuple
    specific_impulse: tuple
    thrust: tuple
    matched_altitude_km: float | None


@dataclass(frozen=True)
class AltitudePerformance:
    total_mass_flow: float
    chamber_count: int
    p_a: float
    J_r_ud: float
    J_vac: float
    P_SL: float
    P_vac: float


def altitude_performance_from_model(model):
    """Adapt a completed forward-calculation model for the shared altitude chart."""
    values = (
        model.m_, model.z_k, model.p_a, model.J_r_ud,
        model.J_8_ud, model.P_0, model.P_8,
    )
    if any(value is None or not math.isfinite(float(value)) for value in values):
        raise ValueError("engine calculation results are incomplete")
    if model.m_ <= 0 or model.z_k <= 0 or model.p_a <= 0:
        raise ValueError("engine calculation results are outside the method domain")
    return AltitudePerformance(
        total_mass_flow=float(model.m_ * model.z_k),
        chamber_count=int(model.z_k),
        p_a=float(model.p_a),
        J_r_ud=float(model.J_r_ud),
        J_vac=float(model.J_8_ud),
        P_SL=float(model.P_0),
        P_vac=float(model.P_8),
    )


_ATMOSPHERE_BASE_ALTITUDES_KM = (0.0, 11.0, 20.0, 32.0, 47.0, 51.0, 71.0, 84.852)
_ATMOSPHERE_LAPSE_RATES_K_PER_KM = (-6.5, 0.0, 1.0, 2.8, 0.0, -2.8, -2.0)
_ATMOSPHERE_T0_K = 288.15
_ATMOSPHERE_STANDARD_P0_PA = 101325.0
_ATMOSPHERE_G0 = 9.80665
_ATMOSPHERE_R_AIR = 287.05287
_EARTH_RADIUS_KM = 6356.766


def _atmosphere_layer_bases():
    temperatures = [_ATMOSPHERE_T0_K]
    pressure_ratios = [1.0]
    for index, lapse_rate in enumerate(_ATMOSPHERE_LAPSE_RATES_K_PER_KM):
        h0 = _ATMOSPHERE_BASE_ALTITUDES_KM[index]
        h1 = _ATMOSPHERE_BASE_ALTITUDES_KM[index + 1]
        temperature0 = temperatures[-1]
        delta_h_m = (h1 - h0) * 1000.0
        if lapse_rate == 0.0:
            ratio = math.exp(
                -_ATMOSPHERE_G0 * delta_h_m
                / (_ATMOSPHERE_R_AIR * temperature0)
            )
            temperature1 = temperature0
        else:
            lapse_rate_per_m = lapse_rate / 1000.0
            temperature1 = temperature0 + lapse_rate * (h1 - h0)
            ratio = (temperature0 / temperature1) ** (
                _ATMOSPHERE_G0 / (_ATMOSPHERE_R_AIR * lapse_rate_per_m)
            )
        temperatures.append(temperature1)
        pressure_ratios.append(pressure_ratios[-1] * ratio)
    return tuple(temperatures), tuple(pressure_ratios)


_ATMOSPHERE_BASE_TEMPERATURES_K, _ATMOSPHERE_BASE_PRESSURE_RATIOS = (
    _atmosphere_layer_bases()
)


def standard_atmosphere_pressure_mpa(altitude_km):
    """Return ambient pressure, scaled to the application's 0.0981 MPa sea level."""
    altitude_km = float(altitude_km)
    if not math.isfinite(altitude_km) or altitude_km < 0:
        raise ValueError("altitude must be a non-negative finite number")

    geopotential_km = (
        _EARTH_RADIUS_KM * altitude_km / (_EARTH_RADIUS_KM + altitude_km)
    )
    layer = len(_ATMOSPHERE_LAPSE_RATES_K_PER_KM) - 1
    for index in range(len(_ATMOSPHERE_LAPSE_RATES_K_PER_KM)):
        if geopotential_km < _ATMOSPHERE_BASE_ALTITUDES_KM[index + 1]:
            layer = index
            break

    h0 = _ATMOSPHERE_BASE_ALTITUDES_KM[layer]
    temperature0 = _ATMOSPHERE_BASE_TEMPERATURES_K[layer]
    pressure_ratio0 = _ATMOSPHERE_BASE_PRESSURE_RATIOS[layer]
    lapse_rate = _ATMOSPHERE_LAPSE_RATES_K_PER_KM[layer]
    delta_h_m = (geopotential_km - h0) * 1000.0
    if lapse_rate == 0.0:
        pressure_ratio = pressure_ratio0 * math.exp(
            -_ATMOSPHERE_G0 * delta_h_m
            / (_ATMOSPHERE_R_AIR * temperature0)
        )
    else:
        lapse_rate_per_m = lapse_rate / 1000.0
        temperature = temperature0 + lapse_rate * (geopotential_km - h0)
        pressure_ratio = pressure_ratio0 * (temperature0 / temperature) ** (
            _ATMOSPHERE_G0 / (_ATMOSPHERE_R_AIR * lapse_rate_per_m)
        )
    return SEA_LEVEL_PRESSURE_MPA * pressure_ratio


def calculate_altitude_thrust_curve(result, max_altitude_km=100.0, step_km=0.5):
    """Calculate total thrust versus altitude for a completed inverse calculation."""
    max_altitude_km = float(max_altitude_km)
    step_km = float(step_km)
    if not math.isfinite(max_altitude_km) or max_altitude_km <= 0:
        raise ValueError("maximum altitude must be positive")
    if not math.isfinite(step_km) or step_km <= 0:
        raise ValueError("altitude step must be positive")

    point_count = int(math.ceil(max_altitude_km / step_km))
    altitudes = [min(index * step_km, max_altitude_km) for index in range(point_count + 1)]
    if altitudes[-1] != max_altitude_km:
        altitudes.append(max_altitude_km)
    pressures = [standard_atmosphere_pressure_mpa(value) for value in altitudes]
    delta_j = result.J_vac - result.J_r_ud
    impulses = [
        result.J_vac - delta_j * pressure / result.p_a
        for pressure in pressures
    ]
    thrusts = [result.total_mass_flow * impulse for impulse in impulses]

    matched_altitude = None
    if pressures[-1] <= result.p_a <= pressures[0]:
        for index in range(1, len(pressures)):
            if pressures[index] <= result.p_a <= pressures[index - 1]:
                p0, p1 = pressures[index - 1], pressures[index]
                h0, h1 = altitudes[index - 1], altitudes[index]
                fraction = (result.p_a - p0) / (p1 - p0)
                matched_altitude = h0 + fraction * (h1 - h0)
                break

    return AltitudeThrustCurve(
        altitude_km=tuple(altitudes),
        ambient_pressure_mpa=tuple(pressures),
        specific_impulse=tuple(impulses),
        thrust=tuple(thrusts),
        matched_altitude_km=matched_altitude,
    )


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
