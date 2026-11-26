"""
Smoke test for the Streamlit page: both views and demo mode must render without an exception,
and the copyright line must be on screen in every one of them. The Technical view runs only its
open tab, so each tab is opened in turn, the closed tabs must stay empty, and the Road choice
inside a tab must survive switching away and back. The View and Season controls must work in
both views and in demo mode.

Copyright 2026 Harrison Cormier, Ashley Pacek and Varvara Blinova.
"""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import tire_model as tm

APP = str(Path(__file__).resolve().parents[1] / "app.py")
COPYRIGHT = "© 2026 Harrison Cormier, Ashley Pacek and Varvara Blinova"


def copyright_places(app):
    """Where the copyright line is shown: under the page, at the foot of the sidebar, and in the demo banner."""
    return dict(
        page=any(COPYRIGHT in c.value for c in app.main.caption),
        sidebar=any(COPYRIGHT in c.value for c in app.sidebar.caption),
        banner=any(COPYRIGHT in str(getattr(h, "body", "")) or COPYRIGHT in str(h.proto) for h in app.main.get("html")),
    )


@pytest.mark.parametrize("view", ["Simple", "Technical"])
@pytest.mark.parametrize("vehicle", list(tm.VEHICLES))
def test_page_renders_for_every_vehicle_in_both_views(view, vehicle):
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["view"] = view
    app.session_state["vehicle"] = vehicle
    app.run()
    assert not app.exception
    shown = copyright_places(app)
    assert shown["page"] and shown["sidebar"]


@pytest.mark.parametrize("view", ["Simple", "Technical"])
def test_demo_mode_renders(view):
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["view"] = view
    app.session_state["demo"] = True
    app.session_state["demo_pending"] = True
    app.run()
    assert not app.exception
    shown = copyright_places(app)
    assert shown["page"] and shown["sidebar"] and shown["banner"]


TECHNICAL_TABS = ["Braking physics", "Width vs diameter vs everything else", "Winter vs summer", "Slip and stability",
                  "Health and safety", "Four pillars", "Model and sources"]


def technical_page(tab=None, **state):
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["view"] = "Technical"
    for key, value in {"tech_tab": tab, **state}.items():
        if value is not None:
            app.session_state[key] = value
    return app.run()


def segmented(app, key):
    return next(w for w in app.get("segmented_control") if w.key == key)


@pytest.mark.parametrize("tab", TECHNICAL_TABS)
def test_each_technical_tab_opens_and_closed_tabs_run_nothing(tab):
    """Only the open Technical tab is drawn; the other six stay empty so a slider move does not rebuild their charts."""
    app = technical_page(tab)
    assert not app.exception
    assert [t.label for t in app.tabs] == TECHNICAL_TABS
    assert app.session_state["tech_tab"] == tab
    for panel in app.tabs:
        assert (len(panel.children) > 0) == (panel.label == tab), panel.label
    assert copyright_places(app)["page"]


def test_road_choice_survives_a_tab_switch():
    """The Road control lives inside a tab that is skipped while closed, so its value must be kept for the session."""
    app = technical_page("Winter vs summer")
    segmented(app, "road").set_value("wet")
    app.run()
    app.session_state["tech_tab"] = "Four pillars"
    app.run()
    assert not app.exception and app.session_state["road"] == "wet"
    app.session_state["tech_tab"] = "Winter vs summer"
    app.run()
    assert not app.exception
    assert segmented(app, "road").value == "wet"
    assert "on a wet road" in app.get("plotly_chart")[0].proto.spec


@pytest.mark.parametrize("demo", [False, True])
@pytest.mark.parametrize("view", ["Simple", "Technical"])
def test_view_and_season_controls_work_in_both_views_and_demo_mode(view, demo):
    app = AppTest.from_file(APP, default_timeout=30)
    app.session_state["view"] = view
    app.session_state["demo"] = demo
    app.session_state["demo_last"] = 1e12
    app.run()
    assert not app.exception
    assert segmented(app, "view").value == view

    segmented(app, "season").set_value("Summer")
    app.run()
    assert not app.exception
    assert app.session_state["season"] == "Summer"
    assert app.session_state["surface"] == tm.SEASONS["Summer"]["surfaces"][0]

    other = "Technical" if view == "Simple" else "Simple"
    segmented(app, "view").set_value(other)
    app.run()
    assert not app.exception
    assert app.session_state["view"] == other
    assert len(app.metric) == (5 if other == "Technical" else 3)
