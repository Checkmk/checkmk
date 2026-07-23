#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Accessibility skeletons for the graph surfaces (CMK-35973).

Skeletons for the a11y aspects in tests/system/gui/docs/graph_accessibility.md that need the
engine's selector/hook contract. Aspect 2 is covered by LT-01; aspects 1, 3-8 live here.
Complete via GraphAccessor and the graph page-objects in pom/graphing/timeseries_graph.py.
"""

import pytest

from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.testlib.graphing import SKIP_PENDING_GRAPH_ENGINE


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_canvas_has_accessible_name(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """a11y aspect 1 (text alternative): the canvas exposes an accessible name.

    Do: open a service detail graph.
    Assert: the canvas/wrapper has an accessible name (aria-label / role="img" / text
    summary), not an unlabelled canvas.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_controls_are_keyboard_operable(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """a11y aspect 3 (keyboard operability): controls work by keyboard, not mouse-only.

    Do: tab to the legend, consolidation-function, time-range and zoom/pin controls; operate
    each via keyboard.
    Assert: each is focusable and activatable with the keyboard alone.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_focus_managed_in_embedded_containers(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """a11y aspect 4 (focus management): focus enters and returns for embedded graphs.

    Do: open a graph in a popup / slide-in / designer preview; move focus in, then dismiss.
    Assert: focus enters on open and returns to the trigger on close; not lost to the body.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_series_distinguishable_without_color(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """a11y aspect 5 (contrast & non-color cues): series are distinguishable without color.

    Do: open a multi-series graph; inspect curve and legend styling.
    Assert: colors meet the contrast expectation; series carry a non-color cue (label, line
    style, legend proximity), not color only.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_animations_respect_reduced_motion(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """a11y aspect 6 (reduced motion): animation honours prefers-reduced-motion.

    Do: with prefers-reduced-motion: reduce emulated, open a service detail graph.
    Assert: graph animations are suppressed/reduced; no non-essential motion.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_states_are_announced_to_assistive_tech(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """a11y aspect 7 (state announcement): loading/empty/error states are announced.

    Do: drive the graph into the loading and error states (page.route on the time-series
    endpoint).
    Assert: each state has an assistive-tech announcement (role="alert" / aria-live), not a
    silent visual-only change.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")


@pytest.mark.skip(reason=SKIP_PENDING_GRAPH_ENGINE)
def test_embedded_graph_has_disambiguating_name(
    dashboard_page: MainDashboard, graph_hosts_with_varying_data: list[str]
) -> None:
    """a11y aspect 8 (embedded labelling): a dashboard graph's name disambiguates siblings.

    Do: open a dashboard with more than one graph widget.
    Assert: each graph's accessible name identifies its widget so siblings are distinguishable.
    """
    pytest.fail("CMK-35973 skeleton: body not implemented")
