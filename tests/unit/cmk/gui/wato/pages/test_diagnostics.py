#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for the support diagnostics form deriving from the discovered plugins"""

from collections.abc import Iterable

import pytest

from cmk.ccc.version import Edition
from cmk.diagnostics.internal import (
    CollectContext,
    DiagnosticsPlugin,
    DumpItem,
    Help,
    Sensitivity,
    Topic,
)
from cmk.discover_plugins import DiscoveredPlugins, PluginLocation
from cmk.gui.http import request
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.wato.pages import diagnostics as diagnostics_page

_TOPIC_A = Topic("Topic A")
_TOPIC_B = Topic("Topic B")


def _handler(_context: CollectContext) -> Iterable[DumpItem]:
    return ()


def _make_plugin(
    name: str,
    topic: Topic,
    sensitivity: Sensitivity,
    always: bool = False,
) -> DiagnosticsPlugin:
    return DiagnosticsPlugin(
        name=name,
        description=Help("Collects something."),
        sensitivity=sensitivity,
        topic=topic,
        always=always,
        handler=_handler,
    )


_FAKE_PLUGINS = [
    _make_plugin("a_low", _TOPIC_A, Sensitivity.LOW),
    _make_plugin("a_high", _TOPIC_A, Sensitivity.HIGH),
    _make_plugin("b_medium", _TOPIC_B, Sensitivity.MEDIUM),
    _make_plugin("always_one", _TOPIC_A, Sensitivity.LOW, always=True),
]


@pytest.fixture(name="fake_discovery")
def fixture_fake_discovery(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        diagnostics_page,
        "load_diagnostics_plugins",
        lambda *args, **kwargs: DiscoveredPlugins(
            errors=(),
            plugins={
                PluginLocation("cmk.plugins.test.diagnostics.test", p.name): p
                for p in _FAKE_PLUGINS
            },
        ),
    )


@pytest.mark.usefixtures("request_context", "fake_discovery")
def test_vs_diagnostics_builds_from_discovered_plugins() -> None:
    request.set_var("select_site_p_site", "NO_SITE")
    mode = diagnostics_page.ModeDiagnostics(Edition.COMMUNITY)

    valuespec = mode._vs_diagnostics(diagnostics_page._load_plugin_catalogue())
    elements = dict(valuespec._get_elements())

    # one threshold dropdown per discovered topic, sorted by unlocalized title
    topic_keys = [key for key in elements if key.startswith("topic_")]
    assert topic_keys == ["topic_Topic_A", "topic_Topic_B"]
    assert all(isinstance(elements[key], DropdownChoice) for key in topic_keys)
    assert elements["topic_Topic_A"].title() == "Topic A"

    # the always collected plugins are shown read-only
    assert "always" in elements

    # the Checkmk server host field is always offered
    assert "checkmk_server_host" in elements


@pytest.mark.usefixtures("request_context")
def test_vs_diagnostics_omits_always_element_without_always_plugins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        diagnostics_page,
        "load_diagnostics_plugins",
        lambda *args, **kwargs: DiscoveredPlugins(
            errors=(),
            plugins={
                PluginLocation("cmk.plugins.test.diagnostics.test", "a_low"): _make_plugin(
                    "a_low", _TOPIC_A, Sensitivity.LOW
                )
            },
        ),
    )
    request.set_var("select_site_p_site", "NO_SITE")
    mode = diagnostics_page.ModeDiagnostics(Edition.COMMUNITY)

    elements = dict(mode._vs_diagnostics(diagnostics_page._load_plugin_catalogue())._get_elements())

    assert "checkmk_server_host" in elements  # the host field is always offered
    assert "always" not in elements  # no always plugins discovered


@pytest.mark.usefixtures("request_context", "fake_discovery")
def test_form_submission_resolves_topic_thresholds() -> None:
    request.set_var("select_site_p_site", "NO_SITE")
    request.set_var("_collect_dump", "1")
    request.set_var("diagnostics_p_topic_Topic_A", DropdownChoice.option_id("high"))
    request.set_var("diagnostics_p_topic_Topic_B", DropdownChoice.option_id("off"))
    request.set_var("diagnostics_p_checkmk_server_host", "myserver")

    mode = diagnostics_page.ModeDiagnostics(Edition.COMMUNITY)
    params = mode._diagnostics_parameters

    assert params is not None
    assert params.site == "NO_SITE"
    assert params.timeout == diagnostics_page.timeout_default
    # topic_a at high selects both plugins, topic_b is off, always plugins excluded
    assert params.plugins == ["a_high", "a_low"]
    assert params.checkmk_server_host == "myserver"
