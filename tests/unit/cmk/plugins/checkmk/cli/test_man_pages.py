#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from cmk.cli.engine.commands import bind as cli_bind
from cmk.cli.engine.readers import ParsedOptions as CLIParsedOptions
from cmk.cli.engine.readers import RecordedOptions as CLIRecordedOptions
from cmk.cli.internal import Command as CLICommand
from cmk.plugins.checkmk.cli.man_pages import (
    _renderer_request,
    cli_command_browse_man,
    cli_command_man,
)


@pytest.mark.parametrize(
    ["command", "expected"],
    [
        pytest.param(cli_command_man, ["renderer"], id="man"),
        pytest.param(cli_command_browse_man, [], id="browse-man"),
    ],
)
def test_a_man_page_command_declares_its_options[R](
    command: CLICommand[R], expected: list[str]
) -> None:
    recorded = CLIRecordedOptions()
    command.request(recorded)

    assert [option.name for option in recorded.options] == expected


def test_the_renderer_is_read_from_the_command_line() -> None:
    options = CLIParsedOptions([("-r", "nowiki")], logging.getLogger(__name__))

    assert _renderer_request(options) == "nowiki"


def test_an_unknown_renderer_is_rejected_before_the_command_runs() -> None:
    with pytest.raises(ValueError, match="--renderer: Invalid argument"):
        cli_bind(
            cli_command_man, CLIParsedOptions([("--renderer", "html")], logging.getLogger(__name__))
        )
