"""
Smoke test for the Streamlit page: both views and demo mode must render without an exception,
and the copyright line must be on screen in every one of them.

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
