#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.plugins.dashboard import utils


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param(
            {
                "type": "pnpgraph",
                "show_legend": True,
                "show_service": True,
                "single_infos": [],
                "context": {
                    "host": "abc",
                },
            },
            {
                "graph_render_options": {"show_legend": True},
                "single_infos": ["service", "host"],
                "type": "pnpgraph",
                "context": {
                    "host": "abc",
                    "service": "_HOST_",
                },
            },
            id="->1.5.0i2->2.0.0b6 pnpgraph",
        ),
        pytest.param(
            {
                "type": "pnpgraph",
                "graph_render_options": {
                    "show_legend": False,
                    "show_title": True,
                    "title_format": "plain",
                },
                "single_infos": ["host", "service"],
                "context": {
                    "host": "abc",
                },
            },
            {
                "graph_render_options": {
                    "show_legend": False,
                },
                "single_infos": ["host", "service"],
                "type": "pnpgraph",
                "context": {
                    "host": "abc",
                    "service": "_HOST_",
                },
            },
            id="1.6.0->2.0.0b6 pnpgraph",
        ),
        pytest.param(
            {
                "type": "notifications_bar_chart",
                "time_range": "d0",
                "time_resolution": "h",
            },
            {
                "type": "notifications_bar_chart",
                "render_mode": (
                    "bar_chart",
                    {
                        "time_range": "d0",
                        "time_resolution": "h",
                    },
                ),
            },
            id="2.0.0->2.0.0b6 notification bar chart",
        ),
        pytest.param(
            {
                "type": "alerts_bar_chart",
                "time_range": "d0",
                "time_resolution": "h",
            },
            {
                "type": "alerts_bar_chart",
                "render_mode": (
                    "bar_chart",
                    {
                        "time_range": "d0",
                        "time_resolution": "h",
                    },
                ),
            },
            id="2.0.0->2.0.0b6 alerts bar chart",
        ),
    ],
)
def test_transform_dashlets_mut(entry, result):
    assert utils._transform_dashlets_mut(entry) == result


@pytest.mark.parametrize(
    "entry, result",
    [
        pytest.param(
            {"svc_status_display": {"some": "content"}, "some": "other stuff"},
            {"status_display": {"some": "content"}, "some": "other stuff"},
            id="2.0.0->2.1.0i1",
        ),
    ],
)
def test_transform_dashlet_status_display(entry, result):
    assert utils.ABCFigureDashlet._transform_vs_forth(entry) == result


@pytest.mark.parametrize(
    "config, expected_config",
    [
        pytest.param(
            {
                "timerange": "0",
            },
            {
                "timerange": "4h",
            },
            id="1.4.0->2.1.0i1 Timewindow from Timerange valuespec CMK-5864",
        ),
        pytest.param(
            {
                "timerange": "25h",
            },
            {
                "timerange": "25h",
            },
            id="2.1 Timewindow from Timerange valuespec CMK-5864",
        ),
    ],
)
def test_transform_timerange(config, expected_config):
    assert expected_config == utils.transform_timerange_dashlet(config)


@pytest.mark.parametrize(
    "context, single_infos, title, additional_macros, result",
    [
        pytest.param(
            {},
            [],
            "Some title $HOST_ALIAS$",
            {},
            {"$DEFAULT_TITLE$": "dashlet"},
            id="no single_infos",
        ),
        pytest.param(
            {"host": {"host": "heute"}},
            ["host"],
            "Best graph",
            {},
            {
                "$DEFAULT_TITLE$": "dashlet",
                "$HOST_NAME$": "heute",
            },
            id="host single_infos",
        ),
        pytest.param(
            {"service": {"service": "CPU utilization"}},
            ["service"],
            "Best graph",
            {},
            {
                "$DEFAULT_TITLE$": "dashlet",
                "$SERVICE_DESCRIPTION$": "CPU utilization",
            },
            id="service single_infos",
        ),
        pytest.param(
            {
                "host": {"host": "vm-123"},
                "service": {"service": "CPU utilization"},
            },
            ["host", "service"],
            "Best graph",
            {},
            {
                "$DEFAULT_TITLE$": "dashlet",
                "$HOST_NAME$": "vm-123",
                "$SERVICE_DESCRIPTION$": "CPU utilization",
            },
            id="host and service single_infos",
        ),
        pytest.param(
            {
                "host": {"host": "vm-123"},
                "service": {"service": "CPU utilization"},
            },
            ["host", "service"],
            "Best graph $HOST_ALIAS$",
            {
                "$SITE$": "site",
            },
            {
                "$DEFAULT_TITLE$": "dashlet",
                "$HOST_NAME$": "vm-123",
                "$HOST_ALIAS$": "alias",
                "$SERVICE_DESCRIPTION$": "CPU utilization",
                "$SITE$": "site",
            },
            id="site and host alias",
        ),
        pytest.param(
            {
                "host": {"host": "vm-123"},
                "service": {"service": "CPU utilization"},
            },
            ["host", "service"],
            "Best graph $HOST_ALIAS$",
            {
                "$ADD_MACRO_1$": "1",
                "$ADD_MACRO_2$": "2",
            },
            {
                "$DEFAULT_TITLE$": "dashlet",
                "$HOST_NAME$": "vm-123",
                "$HOST_ALIAS$": "alias",
                "$SERVICE_DESCRIPTION$": "CPU utilization",
                "$ADD_MACRO_1$": "1",
                "$ADD_MACRO_2$": "2",
            },
            id="additional macros",
        ),
    ],
)
def test_macro_mapping_from_context(
    monkeypatch,
    context,
    single_infos,
    title,
    result,
    additional_macros,
):
    monkeypatch.setattr(
        utils,
        "get_alias_of_host",
        lambda _site, _host_name: "alias",
    )
    assert (
        utils.macro_mapping_from_context(
            context,
            single_infos,
            title,
            "dashlet",
            **additional_macros,
        )
        == result
    )


@pytest.mark.parametrize(
    "single_infos, result",
    [
        pytest.param(
            [],
            [],
            id="no single infos",
        ),
        pytest.param(
            ["service", "host"],
            ["$HOST_NAME$", "$HOST_ALIAS$", "$SERVICE_DESCRIPTION$"],
            id="service and host",
        ),
        pytest.param(
            ["site"],
            [],
            id="unknown single info",
        ),
    ],
)
def test_get_title_macros_from_single_infos(single_infos, result):
    assert list(utils._get_title_macros_from_single_infos(single_infos)) == result


@pytest.mark.parametrize(
    "single_infos, additional_macros, result",
    [
        pytest.param(
            [],
            [],
            "You can use the following macros to fill in the corresponding information:"
            "<ul><li><tt>$DEFAULT_TITLE$ (default title of the element)</tt></li></ul>"
            "These macros can be combined with arbitrary text elements, e.g. "
            '"some text <tt>$MACRO1$</tt> -- <tt>$MACRO2$</tt>".',
            id="default title only",
        ),
        pytest.param(
            ["host"],
            [],
            "You can use the following macros to fill in the corresponding information:"
            "<ul><li><tt>$DEFAULT_TITLE$ (default title of the element)</tt></li>"
            "<li><tt>$HOST_NAME$</tt></li>"
            "<li><tt>$HOST_ALIAS$</tt></li></ul>"
            "These macros can be combined with arbitrary text elements, e.g. "
            '"some text <tt>$MACRO1$</tt> -- <tt>$MACRO2$</tt>".',
            id="host single infos",
        ),
        pytest.param(
            [],
            ["$MACRO$"],
            "You can use the following macros to fill in the corresponding information:"
            "<ul><li><tt>$DEFAULT_TITLE$ (default title of the element)</tt></li>"
            "<li><tt>$MACRO$</tt></li></ul>"
            "These macros can be combined with arbitrary text elements, e.g. "
            '"some text <tt>$MACRO1$</tt> -- <tt>$MACRO2$</tt>".',
            id="additional macro",
        ),
        pytest.param(
            ["service", "host"],
            ["$MACRO1$", "$MACRO2$ (some explanation)"],
            "You can use the following macros to fill in the corresponding information:"
            "<ul><li><tt>$DEFAULT_TITLE$ (default title of the element)</tt></li>"
            "<li><tt>$HOST_NAME$</tt></li>"
            "<li><tt>$HOST_ALIAS$</tt></li>"
            "<li><tt>$SERVICE_DESCRIPTION$</tt></li>"
            "<li><tt>$MACRO1$</tt></li>"
            "<li><tt>$MACRO2$ (some explanation)</tt></li></ul>"
            "These macros can be combined with arbitrary text elements, e.g. "
            '"some text <tt>$MACRO1$</tt> -- <tt>$MACRO2$</tt>".',
            id="host, service in single infos and additional macros",
        ),
    ],
)
def test_title_help_text_for_macros(monkeypatch, single_infos, additional_macros, result):
    monkeypatch.setattr(
        utils.ABCFigureDashlet,
        "single_infos",
        lambda: single_infos,
    )
    monkeypatch.setattr(
        utils.ABCFigureDashlet,
        "get_additional_title_macros",
        lambda: additional_macros,
    )
    # mypy: Only concrete class can be given where "Type[Dashlet]" is expected [misc]
    assert utils._title_help_text_for_macros(utils.ABCFigureDashlet) == result  # type: ignore[misc]
