#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --create-diagnostics-dump" command.

The dump itself is built by cmk.base.diagnostics; this only turns the command
line into a selection of diagnostics plug-ins.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue
from cmk.diagnostics.internal import Sensitivity

_CLI_THRESHOLDS: Final[Mapping[str, Sensitivity | None]] = {
    "off": None,
    "low": Sensitivity.LOW,
    "medium": Sensitivity.MEDIUM,
    "high": Sensitivity.HIGH,
}


def _parse_threshold(argument: str) -> Sensitivity | None:
    try:
        return _CLI_THRESHOLDS[argument]
    except KeyError:
        raise ValueError(argument) from None


def _parse_plugin_names(argument: str) -> Sequence[str]:
    return tuple(argument.split(","))


_LIST_FLAG: Final = CLIFlag(
    long="list",
    help="List the available topics and plugins and exit",
)

_ALL_TOPICS_VALUE: Final = CLIValue(
    long="all-topics",
    help=(
        "Select all plugins of all topics up to the given sensitivity threshold "
        "(off, low, medium or high)"
    ),
    placeholder="THRESHOLD",
    parse=_parse_threshold,
)

_PLUGINS_VALUE: Final = CLIValue(
    long="plugins",
    help="Additionally select the given plugins, regardless of topic thresholds",
    placeholder="NAME,NAME...",
    parse=_parse_plugin_names,
)

_CHECKMK_SERVER_HOST_VALUE: Final = CLIValue(
    long="checkmk-server-host",
    help="The name of the host monitoring the Checkmk server; needed by some plugins",
    placeholder="HOST",
    parse=str,
)


@dataclass(frozen=True, kw_only=True)
class CliSelection:
    list_plugins: bool
    all_topics: Sensitivity | None
    plugins: Sequence[str]
    checkmk_server_host: str | None


def _cli_selection(options: CLIReader) -> CliSelection:
    return CliSelection(
        list_plugins=options.flag(_LIST_FLAG),
        all_topics=options.value(_ALL_TOPICS_VALUE),
        plugins=options.value(_PLUGINS_VALUE) or (),
        checkmk_server_host=options.value(_CHECKMK_SERVER_HOST_VALUE),
    )


cli_command_create_diagnostics_dump = CLICommand(
    name="create_diagnostics_dump",
    handler="cmk.plugins.diagnostics.cli.handlers.create_dump:cli_handler_create_diagnostics_dump",
    long="create-diagnostics-dump",
    request=_cli_selection,
    help="Create diagnostics dump",
    description=[
        (
            "Create a dump containing information for diagnostic analysis "
            "in the folder var/check_mk/diagnostics. The dump content is "
            "provided by discoverable plugins grouped into topics; use --list "
            "to see what is available on this site. Without any option only "
            "the always collected plugins are packed."
        )
    ],
)
