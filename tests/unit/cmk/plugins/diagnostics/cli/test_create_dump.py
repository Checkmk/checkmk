#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.cli.internal import Declaration as CLIDeclaration
from cmk.cli.internal import Reader as CLIReader
from cmk.diagnostics.internal import Sensitivity
from cmk.plugins.diagnostics.cli.create_dump import (
    _ALL_TOPICS_VALUE,
    _CHECKMK_SERVER_HOST_VALUE,
    _cli_selection,
    _LIST_FLAG,
    _PLUGINS_VALUE,
    CliSelection,
)


def test_the_selection_is_read_from_the_command_line() -> None:
    given: Mapping[CLIDeclaration, Sequence[str]] = {
        _LIST_FLAG: [""],
        _ALL_TOPICS_VALUE: ["low"],
        _PLUGINS_VALUE: ["b_high,a_low"],
        _CHECKMK_SERVER_HOST_VALUE: ["my_server"],
    }

    assert _cli_selection(
        CLIReader(lambda declaration: given.get(declaration, ()))
    ) == CliSelection(
        list_plugins=True,
        all_topics=Sensitivity.LOW,
        plugins=("b_high", "a_low"),
        checkmk_server_host="my_server",
    )


def test_an_unknown_threshold_is_rejected() -> None:
    with pytest.raises(ValueError, match="extreme"):
        given: Mapping[CLIDeclaration, Sequence[str]] = {_ALL_TOPICS_VALUE: ["extreme"]}

        _cli_selection(CLIReader(lambda declaration: given.get(declaration, ())))
