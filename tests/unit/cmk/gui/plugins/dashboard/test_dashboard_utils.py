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
                'type': 'pnpgraph',
                'show_legend': True,
                'show_service': True,
                'single_infos': [],
                'context': {
                    "host": "abc",
                },
            },
            {
                'graph_render_options': {
                    'show_legend': True
                },
                'single_infos': ['service', 'host'],
                'type': 'pnpgraph',
                'context': {
                    'host': 'abc',
                    'service': '_HOST_',
                },
            },
            id="->1.5.0i2->2.0.0b6 pnpgraph",
        ),
        pytest.param(
            {
                'type': 'pnpgraph',
                'graph_render_options': {
                    'show_legend': False,
                    'show_title': True,
                    'title_format': 'plain',
                },
                'single_infos': ['host', 'service'],
                'context': {
                    "host": "abc",
                },
            },
            {
                'graph_render_options': {
                    'show_legend': False,
                },
                'single_infos': ['host', 'service'],
                'type': 'pnpgraph',
                'context': {
                    'host': 'abc',
                    'service': '_HOST_',
                },
            },
            id="1.6.0->2.0.0b6 pnpgraph",
        ),
    ],
)
def test_transform_dashlets_mut(entry, result):
    assert utils._transform_dashlets_mut(entry) == result


@pytest.mark.parametrize(
    "context, single_infos, title, result",
    [
        pytest.param(
            {},
            [],
            "Some title $HOST_ALIAS$",
            {},
            id="no single_infos",
        ),
        pytest.param(
            {"host": "heute"},
            ["host"],
            "Best graph",
            {"$HOST_NAME$": "heute"},
            id="host single_infos",
        ),
        pytest.param(
            {"service": "CPU utilization"},
            ["service"],
            "Best graph",
            {"$SERVICE_DESCRIPTION$": "CPU utilization"},
            id="service single_infos",
        ),
        pytest.param(
            {
                "host": "vm-123",
                "service": "CPU utilization"
            },
            ["host", "service"],
            "Best graph",
            {
                "$HOST_NAME$": "vm-123",
                "$SERVICE_DESCRIPTION$": "CPU utilization"
            },
            id="host and service single_infos",
        ),
    ],
)
def test_macro_mapping_from_context(context, single_infos, title, result):
    assert utils.macro_mapping_from_context(context, single_infos, title) == result


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
            "",
            id="no macros",
        ),
        pytest.param(
            ["host"],
            [],
            "You can use the following macros to fill in the corresponding information:"
            "<ul><li><tt>$HOST_NAME$</tt></li>"
            "<li><tt>$HOST_ALIAS$</tt></li></ul>"
            "These macros can be combined with arbitrary text elements, e.g. "
            "\"some text <tt>$MACRO1$</tt> -- <tt>$MACRO2$</tt>\".",
            id="host single infos",
        ),
        pytest.param(
            [],
            ["$MACRO$"],
            "You can use the following macros to fill in the corresponding information:"
            "<ul><li><tt>$MACRO$</tt></li></ul>"
            "These macros can be combined with arbitrary text elements, e.g. "
            "\"some text <tt>$MACRO1$</tt> -- <tt>$MACRO2$</tt>\".",
            id="only additional macro",
        ),
        pytest.param(
            ["service", "host"],
            ["$MACRO1$", "$MACRO2$ (some explanation)"],
            "You can use the following macros to fill in the corresponding information:"
            "<ul><li><tt>$HOST_NAME$</tt></li>"
            "<li><tt>$HOST_ALIAS$</tt></li>"
            "<li><tt>$SERVICE_DESCRIPTION$</tt></li>"
            "<li><tt>$MACRO1$</tt></li>"
            "<li><tt>$MACRO2$ (some explanation)</tt></li></ul>"
            "These macros can be combined with arbitrary text elements, e.g. "
            "\"some text <tt>$MACRO1$</tt> -- <tt>$MACRO2$</tt>\".",
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
