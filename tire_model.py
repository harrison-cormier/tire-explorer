"""
Tire performance screening model for the fleet tire fitment explorer.

Pure functions and lookup tables, with no Streamlit dependency, so the model can be
tested and reused on its own. Calibration anchors are checked in tests/test_model.py.
The published tests and references behind each table and formula are listed in SOURCES.md.

Copyright 2026 Harrison Cormier, Ashley Pacek and Varvara Blinova.
Licensed under the Apache License 2.0 (see LICENSE and NOTICE).
"""

import math

import numpy as np

G = 9.81
ATM_PSI = 14.7
PSI_TO_KPA = 6.895
NEW_TREAD_MM = 8.0
RAMP_RADIUS_M = 60
CG_HEIGHT_RATIO = 0.22

# ----------------------------------------------------------------------------
# Reference data
# ----------------------------------------------------------------------------

VEHICLES = {
    "Compact SUV (225/65R17)": dict(oem=(225, 65, 17), mass=1700, placard=35, driven=1.00, drive="AWD", fuel=8.5),
    "Mid-size sedan (215/55R17)": dict(oem=(215, 55, 17), mass=1550, placard=35, driven=0.60, drive="FWD", fuel=7.5),
    "Compact car (205/55R16)": dict(oem=(205, 55, 16), mass=1350, placard=33, driven=0.61, drive="FWD", fuel=6.8),
    "Half-ton pickup (275/65R18)": dict(oem=(275, 65, 18), mass=2500, placard=35, driven=0.43, drive="RWD, 2WD mode", fuel=12.5),
}

COMPOUNDS = ["Summer", "All-season", "All-weather (3PMSF)", "Winter"]

SEASONS = {
    "Summer": dict(surfaces=["Dry", "Wet", "Standing water"], temp=(8, 35, 22)),
    "Winter": dict(surfaces=["Cold dry", "Cold wet", "Slush", "Packed snow", "Ice"], temp=(-30, 7, -8)),
}
SURFACE_TEMP_RANGE = {"Cold wet": (-15, 7), "Slush": (-10, 3), "Packed snow": (-30, 2), "Ice": (-30, 0)}
SURFACE_KEY = {
    "Dry": "dry", "Cold dry": "dry", "Wet": "wet", "Cold wet": "wet",
    "Standing water": "flood", "Slush": "slush", "Packed snow": "snow", "Ice": "ice",
}
WATER_DEPTH_MM = {"wet": 1.0, "flood": 6.0, "slush": 8.0}

# Effective braking friction by compound and temperature, reference size, new tread.
T_ROAD = [-30, -20, -10, 0, 7, 15, 25, 35]
T_SNOW = [-30, -20, -10, -5, 0, 2]
T_ICE = [-30, -20, -10, -5, -1, 0]
MU = {
    "dry": (T_ROAD, {
        "Summer": [0.62, 0.72, 0.84, 0.95, 1.00, 1.05, 1.08, 1.06],
        "All-season": [0.78, 0.84, 0.89, 0.93, 0.95, 0.97, 0.98, 0.96],
        "All-weather (3PMSF)": [0.82, 0.86, 0.89, 0.91, 0.92, 0.93, 0.93, 0.90],
        "Winter": [0.86, 0.87, 0.87, 0.86, 0.85, 0.83, 0.79, 0.74],
    }),
    "wet": (T_ROAD, {
        "Summer": [0.35, 0.42, 0.50, 0.60, 0.70, 0.80, 0.85, 0.85],
        "All-season": [0.50, 0.56, 0.62, 0.68, 0.72, 0.76, 0.78, 0.77],
        "All-weather (3PMSF)": [0.54, 0.59, 0.64, 0.69, 0.72, 0.74, 0.74, 0.72],
        "Winter": [0.60, 0.63, 0.66, 0.68, 0.68, 0.67, 0.64, 0.60],
    }),
    "snow": (T_SNOW, {
        "Summer": [0.12, 0.14, 0.16, 0.17, 0.16, 0.15],
        "All-season": [0.24, 0.26, 0.28, 0.27, 0.24, 0.22],
        "All-weather (3PMSF)": [0.32, 0.34, 0.35, 0.34, 0.29, 0.26],
        "Winter": [0.40, 0.42, 0.42, 0.40, 0.34, 0.30],
    }),
    "ice": (T_ICE, {
        "Summer": [0.120, 0.100, 0.085, 0.070, 0.055, 0.050],
        "All-season": [0.170, 0.150, 0.120, 0.100, 0.070, 0.060],
        "All-weather (3PMSF)": [0.220, 0.190, 0.150, 0.120, 0.085, 0.070],
        "Winter": [0.300, 0.260, 0.200, 0.160, 0.110, 0.090],
    }),
}
MU_SLUSH = {"Summer": 0.25, "All-season": 0.34, "All-weather (3PMSF)": 0.40, "Winter": 0.45}

# Size sensitivities: friction scales with (value / reference) ** exponent.
WIDTH_EXP = {"dry": 0.10, "wet": 0.05, "flood": 0.05, "slush": -0.15, "snow": -0.03, "ice": 0.0}
SIDEWALL_EXP = {"dry": -0.04, "wet": -0.02, "flood": -0.02, "slush": 0.0, "snow": 0.0, "ice": 0.0}
DIAMETER_EXP = {"dry": 0.0, "wet": 0.0, "flood": 0.0, "slush": 0.10, "snow": 0.10, "ice": 0.0}

# Burckhardt friction-slip curve shape parameters (c1, c2, c3).
BURCKHARDT = {
    "dry": (1.2801, 23.99, 0.52), "wet": (0.857, 33.822, 0.347), "flood": (0.857, 33.822, 0.347),
    "slush": (0.1946, 94.129, 0.0646), "snow": (0.1946, 94.129, 0.0646), "ice": (0.05, 306.39, 0.01),
}

LAND_RATIO = {"Summer": 0.72, "All-season": 0.68, "All-weather (3PMSF)": 0.65, "Winter": 0.62}
ROLLING = {"Summer": 1.00, "All-season": 0.97, "All-weather (3PMSF)": 1.03, "Winter": 1.07}
WEAR = {"Summer": 1.00, "All-season": 0.80, "All-weather (3PMSF)": 0.95, "Winter": 1.10}
RESPONSE = {"Summer": 1.05, "All-season": 1.00, "All-weather (3PMSF)": 0.97, "Winter": 0.90}

# ----------------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------------


def geometry(width, aspect, rim):
    sidewall = width * aspect / 100
    diameter = rim * 25.4 + 2 * sidewall
    return dict(width=width, aspect=aspect, rim=rim, sidewall=sidewall, diameter=diameter)


def exact_aspect(width, rim, target_diameter):
    return 100 * (target_diameter - rim * 25.4) / (2 * width)


def matched_aspect(width, rim, target_diameter):
    options = range(30, 90, 5)
    return min(options, key=lambda a: abs(geometry(width, a, rim)["diameter"] - target_diameter))


def pressure_at_temperature(set_psi, temp_c, set_temp_c=20):
    absolute = (set_psi + ATM_PSI) * (temp_c + 273.15) / (set_temp_c + 273.15)
    return absolute - ATM_PSI


def base_mu(compound, surface, temp_c):
    if surface == "slush":
        return MU_SLUSH[compound]
    temps, table = MU["wet" if surface == "flood" else surface]
    return float(np.interp(temp_c, temps, table[compound]))


def tread_factor(surface, tread_mm):
    worn = min(max(NEW_TREAD_MM - tread_mm, 0), 4)
    below_4 = max(4 - tread_mm, 0)
    if surface == "dry":
        return 1 + 0.005 * (worn + below_4)
    if surface in ("wet", "flood"):
        return 1 - 0.005 * worn - 0.02 * below_4
    if surface in ("snow", "slush"):
        return 1 - 0.02 * worn - 0.06 * below_4
    return 1 - 0.01 * (worn + below_4)


def hydroplaning_speed(surface, geo, tread_mm, pressure_psi):
    """Speed (km/h) at which the tire rides up on the water film, or None on surfaces with no film."""
    if surface not in WATER_DEPTH_MM:
        return None
    horne = 6.35 * math.sqrt(pressure_psi * PSI_TO_KPA)
    drainage = 0.60 + 0.215 * math.log(1 + 2 * tread_mm / WATER_DEPTH_MM[surface])
    shape = (geo["width"] / 215) ** -0.35 * (geo["diameter"] / 680) ** 0.15
    return horne * drainage * shape


def film_factor(speed_kmh, v_hp):
    if v_hp is None:
        return 1.0
    return 1 - 0.85 * min(speed_kmh / v_hp, 1.0) ** 4


def braking_profile(speed_kmh, mu, v_hp, steps=160):
    speeds = np.linspace(speed_kmh, 0, steps + 1)
    mid = (speeds[:-1] + speeds[1:]) / 2
    decel = np.array([G * mu * film_factor(v, v_hp) for v in mid])
    dv = (speeds[:-1] - speeds[1:]) / 3.6
    dt = dv / decel
    dd = (mid / 3.6) * dt
    return dict(
        t=np.concatenate([[0], np.cumsum(dt)]),
        d=np.concatenate([[0], np.cumsum(dd)]),
        v=speeds,
    )


def slip_curve(surface, mu_peak):
    c1, c2, c3 = BURCKHARDT[surface]
    slip = np.concatenate([np.linspace(0, 0.3, 121), np.linspace(0.305, 1, 80)])
    shape = c1 * (1 - np.exp(-c2 * slip)) - c3 * slip
    mu = shape / shape.max() * mu_peak
    return slip * 100, mu, float(slip[shape.argmax()] * 100)


def cornering_speed(mu, v_hp, radius=RAMP_RADIUS_M):
    """Highest speed (km/h) the lateral grip can hold on a curve, solved by bisection."""
    low, high = 0.0, 300.0
    for _ in range(50):
        mid = (low + high) / 2
        limit = 3.6 * math.sqrt(0.95 * mu * film_factor(mid, v_hp) * G * radius)
        low, high = (mid, high) if mid <= limit else (low, mid)
    return low


def evaluate(cfg, env):
    """All outputs for one tire setup (cfg) in one driving condition (env)."""
    veh = VEHICLES[env["vehicle"]]
    ref = geometry(*veh["oem"])
    geo = geometry(cfg["width"], cfg["aspect"], cfg["rim"])
    surface = env["surface"]
    p_ratio = cfg["pressure"] / veh["placard"]

    size_factor = (
        (geo["width"] / ref["width"]) ** WIDTH_EXP[surface]
        * (geo["sidewall"] / ref["sidewall"]) ** SIDEWALL_EXP[surface]
        * (geo["diameter"] / ref["diameter"]) ** DIAMETER_EXP[surface]
    )
    pressure_factor = 1 - 0.5 * (p_ratio - 1) ** 2
    mu = (base_mu(cfg["compound"], surface, env["temp"]) * size_factor
          * tread_factor(surface, cfg["tread"]) * pressure_factor)

    v_hp = hydroplaning_speed(surface, geo, cfg["tread"], cfg["pressure"])
    profile = braking_profile(env["speed"], mu, v_hp)
    slip, slip_mu, peak_slip = slip_curve(surface, mu)

    load_n = veh["mass"] * G / 4
    patch_area = load_n / (cfg["pressure"] * PSI_TO_KPA * 1000 * LAND_RATIO[cfg["compound"]])
    patch_width = 0.78 * geo["width"]
    patch_length = patch_area * 1e6 / patch_width

    rolling = (ROLLING[cfg["compound"]] * p_ratio ** -0.5
               * (ref["diameter"] / geo["diameter"]) ** 0.3 * (geo["width"] / ref["width"]) ** 0.1)
    heat = max(env["temp"] - 7, 0)
    wear = WEAR[cfg["compound"]] * (1 + {"Winter": 0.03, "All-weather (3PMSF)": 0.01}.get(cfg["compound"], 0) * heat)

    tire_kg = 48.8 * (geo["width"] / 1000) * (geo["diameter"] / 1000) + 30.7 * (geo["sidewall"] / 1000) * (geo["diameter"] / 1000)
    wheel_kg = 8.5 + 1.4 * (geo["rim"] - 16) + 0.04 * (geo["width"] - 205)

    transfer = CG_HEIGHT_RATIO * mu
    if veh["drive"] == "AWD":
        grade = mu
    elif veh["drive"] == "FWD":
        grade = mu * veh["driven"] / (1 + transfer)
    else:
        grade = mu * veh["driven"] / (1 - transfer)

    return dict(
        geo=geo, mu=mu, v_hp=v_hp, profile=profile,
        distance=float(profile["d"][-1]), time=float(profile["t"][-1]),
        slip=slip, slip_mu=slip_mu, peak_slip=peak_slip, locked_mu=float(slip_mu[-1]),
        corner=cornering_speed(mu, v_hp), grade=100 * grade,
        patch_width=patch_width, patch_length=patch_length,
        fuel_delta=25 * (rolling - 1), wear=wear,
        response=RESPONSE[cfg["compound"]] * (ref["sidewall"] / geo["sidewall"]) ** 0.5
        * (geo["width"] / ref["width"]) ** 0.3 * p_ratio ** 0.3,
        harshness=100 * (ref["sidewall"] / geo["sidewall"]) ** 0.7 * p_ratio ** 0.5,
        impact_risk=100 * (ref["sidewall"] / geo["sidewall"]) ** 1.5,
        assembly_kg=tire_kg + wheel_kg,
        price=100 * (1 + 0.08 * (geo["rim"] - ref["rim"])) * (geo["width"] / ref["width"]) ** 0.5,
        speedo=100 * (geo["diameter"] / ref["diameter"] - 1),
    )


def speed_at_distance(profile, distance):
    if distance >= profile["d"][-1]:
        return 0.0
    return float(np.interp(distance, profile["d"], profile["v"]))
