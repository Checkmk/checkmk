#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Sequence

import pytest

from cmk.gui.dashboard import title_macros
from cmk.gui.type_defs import SingleInfos, VisualContext
from cmk.utils.macros import MacroMapping


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
    monkeypatch: pytest.MonkeyPatch,
    context: VisualContext,
    single_infos: SingleInfos,
    title: str,
    result: MacroMapping,
    additional_macros: dict[str, str],
) -> None:
    monkeypatch.setattr(
        title_macros,
        "get_alias_of_host",
        lambda _site, _host_name: "alias",
    )
    assert (
        title_macros.macro_mapping_from_context(
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
def test_get_title_macros_from_single_infos(
    single_infos: SingleInfos, result: Sequence[str]
) -> None:
    assert list(title_macros._get_title_macros_from_single_infos(single_infos)) == result


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
def test_title_help_text_for_macros(
    single_infos: SingleInfos, additional_macros: Iterable[str], result: str
) -> None:
    assert title_macros.title_help_text_for_macros(single_infos, additional_macros) == result
