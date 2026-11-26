"""
Calibration and sanity checks for tire_model. Each test names the published result or modelling
assumption it protects. SOURCES.md says which are supported by a published test and which are judgement values.

Copyright 2026 Harrison Cormier, Ashley Pacek and Varvara Blinova.
"""

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tire_model as tm

SUV = "Compact SUV (225/65R17)"


def run(compound="All-season", surface="dry", temp=20, speed=80, width=225, aspect=65, rim=17, tread=8.0,
        pressure=35, vehicle=SUV):
    cfg = dict(compound=compound, width=width, aspect=aspect, rim=rim, tread=tread, pressure=pressure)
    env = dict(vehicle=vehicle, surface=surface, temp=temp, speed=speed)
    return tm.evaluate(cfg, env)


def test_geometry_of_factory_size():
    geo = tm.geometry(225, 65, 17)
    assert geo["sidewall"] == pytest.approx(146.25)
    assert geo["diameter"] == pytest.approx(724.3)


def test_exact_aspect_holds_diameter():
    target = tm.geometry(225, 65, 17)["diameter"]
    aspect = tm.exact_aspect(245, 18, target)
    assert tm.geometry(245, aspect, 18)["diameter"] == pytest.approx(target)


def test_pressure_falls_about_one_psi_per_five_to_six_degrees():
    assert tm.pressure_at_temperature(35, -8) == pytest.approx(30.3, abs=0.3)
    assert tm.pressure_at_temperature(35, 20) == pytest.approx(35)


def test_dry_braking_from_100_is_in_the_tested_range():
    assert 34 < run(compound="Summer", speed=100)["distance"] < 40
    assert 38 < run(compound="All-season", speed=100)["distance"] < 44


def test_winter_tire_is_10_to_20_percent_longer_than_summer_on_cool_dry_road():
    ratio = run(compound="Winter", temp=5.5, speed=100)["distance"] / run(compound="Summer", temp=5.5, speed=100)["distance"]
    assert 1.10 < ratio < 1.20


def test_wet_crossover_between_all_season_and_summer_sits_between_10_and_15_degrees():
    assert run("All-season", "wet", 6)["distance"] < run("Summer", "wet", 6)["distance"]
    assert run("Summer", "wet", 15)["distance"] < run("All-season", "wet", 15)["distance"]


def test_summer_tire_needs_at_least_twice_the_distance_on_packed_snow():
    assert run("Summer", "snow", -10)["distance"] > 2 * run("Winter", "snow", -10)["distance"]


def test_tire_types_rank_in_order_on_snow_and_ice():
    for surface, temp in (("snow", -10), ("ice", -5)):
        distances = [run(c, surface, temp)["distance"] for c in ("Winter", "All-weather (3PMSF)", "All-season", "Summer")]
        assert distances == sorted(distances)


def test_width_barely_matters_on_packed_snow():
    narrow = run("Winter", "snow", -10, width=225)["distance"]
    wide = run("Winter", "snow", -10, width=255, aspect=tm.exact_aspect(255, 17, 724.3))["distance"]
    assert abs(wide / narrow - 1) < 0.01


def test_narrower_is_better_in_slush_and_wider_is_better_on_dry():
    aspect = lambda w: tm.exact_aspect(w, 17, 724.3)
    assert run("Winter", "slush", 0, width=205, aspect=aspect(205))["distance"] < run("Winter", "slush", 0, width=245, aspect=aspect(245))["distance"]
    assert run("Summer", "dry", 25, width=245, aspect=aspect(245))["distance"] < run("Summer", "dry", 25, width=205, aspect=aspect(205))["distance"]


def test_snow_grip_loses_about_two_percent_per_mm_down_to_4_mm_then_faster():
    new, half, worn = (run("Winter", "snow", -10, tread=t)["distance"] for t in (8.0, 4.0, 2.0))
    assert 1.06 < half / new < 1.11
    assert (worn / half - 1) / 2 > (half / new - 1) / 4


def test_wet_braking_at_2_mm_is_15_to_30_percent_longer():
    ratio = run(surface="wet", temp=10, tread=2.0)["distance"] / run(surface="wet", temp=10)["distance"]
    assert 1.15 < ratio < 1.30


def test_ice_grip_improves_as_it_gets_colder():
    assert run("Winter", "ice", -20)["distance"] < run("Winter", "ice", -1)["distance"]


def test_hydroplaning_speed_responds_to_width_wear_and_pressure():
    base = run(surface="flood")["v_hp"]
    assert run(surface="flood", width=255, aspect=tm.exact_aspect(255, 17, 724.3))["v_hp"] < base
    assert run(surface="flood", tread=2.0)["v_hp"] < base
    assert run(surface="flood", pressure=28)["v_hp"] < base
    assert 75 < base < 95


def test_no_hydroplaning_speed_without_a_water_film():
    assert run(surface="dry")["v_hp"] is None
    assert run("Winter", "snow", -10)["v_hp"] is None


@pytest.mark.parametrize("surface,tread,width", [("flood", 1.6, 255), ("slush", 4.0, 245), ("wet", 8.0, 205), ("dry", 8.0, 225)])
def test_cornering_speed_satisfies_the_grip_equation(surface, tread, width):
    result = run(surface=surface, temp=5, tread=tread, width=width)
    v = result["corner"]
    limit = 3.6 * math.sqrt(0.95 * result["mu"] * tm.film_factor(v, result["v_hp"]) * tm.G * tm.RAMP_RADIUS_M)
    assert v == pytest.approx(limit, abs=0.05)


def test_slip_peak_arrives_earlier_on_low_grip_surfaces():
    peaks = [run("Winter", s, -5)["peak_slip"] for s in ("dry", "snow", "ice")]
    assert peaks == sorted(peaks, reverse=True)
    assert run("Winter", "ice", -5)["locked_mu"] < run("Winter", "ice", -5)["mu"]


def test_speed_at_distance_is_zero_once_stopped():
    result = run()
    assert tm.speed_at_distance(result["profile"], result["distance"] + 1) == 0
    assert tm.speed_at_distance(result["profile"], 0) == pytest.approx(80)


def test_every_vehicle_surface_and_tire_type_evaluates():
    for vehicle, spec in tm.VEHICLES.items():
        width, aspect, rim = spec["oem"]
        for surface in ("dry", "wet", "flood", "slush", "snow", "ice"):
            for compound in tm.COMPOUNDS:
                result = run(compound, surface, -5, width=width, aspect=aspect, rim=rim, vehicle=vehicle, pressure=spec["placard"])
                assert result["distance"] > 0 and math.isfinite(result["distance"])
