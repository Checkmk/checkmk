#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --man" and "cmk --browse-man" commands."""

from typing import Final, Literal

from cmk.cli.internal import Arguments as CLIArguments
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import no_options as cli_no_options
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue

type Renderer = Literal["console", "nowiki"]


def _parse_renderer(argument: str) -> Renderer:
    match argument:
        case "console":
            return "console"
        case "nowiki":
            return "nowiki"
        case other:
            raise ValueError(other)


_RENDERER_VALUE: Final = CLIValue(
    long="renderer",
    short="r",
    placeholder="RENDERER",
    help="Use the given renderer: 'console' or 'nowiki'. Defaults to 'console'.",
    parse=_parse_renderer,
)


def _renderer_request(options: CLIReader) -> Renderer | None:
    return options.value(_RENDERER_VALUE)


cli_command_man = CLICommand(
    name="man",
    handler="cmk.plugins.checkmk.cli.handlers.man_pages:cli_handler_man",
    long="man",
    short="M",
    arguments=CLIArguments("CHECKTYPE", optional=True),
    request=_renderer_request,
    help="Show manpage for check CHECKTYPE",
    description=[
        (
            "Shows documentation about a check type. If /usr/bin/less is "
            "available it is used as pager. Exit by pressing Q. "
            "Use -M without an argument to show a list of all manual pages."
        )
    ],
)


cli_command_browse_man = CLICommand(
    name="browse_man",
    handler="cmk.plugins.checkmk.cli.handlers.man_pages:cli_handler_browse_man",
    long="browse-man",
    short="m",
    request=cli_no_options,
    help="Open interactive manpage browser",
)
