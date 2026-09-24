#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --create-diagnostics-dump" command.

The dump itself is built by cmk.base.diagnostics; this only turns the command
line into a selection of diagnostics plug-ins.
"""

import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import cmk.utils.paths
from cmk.base.automations.automations import load_config
from cmk.base.diagnostics import (
    ConsoleLogger,
    create_diagnostics_dump_v2,
    load_plugin_catalogue,
)
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _
from cmk.cli.engine.commands import option_string
from cmk.cli.internal import Args, CLICommand, CLIOption, GlobalOptions, Options
from cmk.diagnostics.engine import DumpSelection, resolve_selection
from cmk.diagnostics.internal import DiagnosticsPlugin, Sensitivity, Topic

_CLI_THRESHOLDS: Final[Mapping[str, Sensitivity | None]] = {
    "off": None,
    "low": Sensitivity.LOW,
    "medium": Sensitivity.MEDIUM,
    "high": Sensitivity.HIGH,
}


@dataclass(frozen=True)
class _CliSelection:
    list_plugins: bool
    all_topics: str | None
    plugins: str | None
    checkmk_server_host: str


def _cli_selection(parsed: Mapping[str, object]) -> _CliSelection:
    return _CliSelection(
        list_plugins="list" in parsed,
        all_topics=option_string(parsed, "all-topics"),
        plugins=option_string(parsed, "plugins"),
        checkmk_server_host=option_string(parsed, "checkmk-server-host") or "",
    )


def _parse_cli_threshold(raw: str) -> Sensitivity | None:
    try:
        return _CLI_THRESHOLDS[raw]
    except KeyError:
        raise MKGeneralException(
            "Invalid sensitivity threshold {!r} (allowed: {})".format(
                raw, ", ".join(_CLI_THRESHOLDS)
            )
        ) from None


def _resolve_cli_selection(
    catalogue: Mapping[str, DiagnosticsPlugin], options: _CliSelection
) -> DumpSelection:
    default_threshold = (
        _parse_cli_threshold(options.all_topics) if options.all_topics is not None else None
    )
    thresholds: dict[Topic, Sensitivity | None] = dict.fromkeys(
        (plugin.topic for plugin in catalogue.values()), default_threshold
    )

    selected = set(resolve_selection(catalogue.values(), thresholds))
    for name in options.plugins.split(",") if options.plugins is not None else []:
        if name not in catalogue:
            raise MKGeneralException("Unknown plugin %r (see --list for available plugins)" % name)
        selected.add(name)

    return DumpSelection(
        plugins=sorted(selected),
        checkmk_server_host=options.checkmk_server_host,
    )


def _print_available_plugins(catalogue: Mapping[str, DiagnosticsPlugin]) -> None:
    by_topic: dict[Topic, list[DiagnosticsPlugin]] = {}
    for plugin in catalogue.values():
        by_topic.setdefault(plugin.topic, []).append(plugin)
    for topic in sorted(by_topic, key=lambda t: t.localize(str)):
        plugins = by_topic[topic]
        sys.stdout.write(f"{topic.localize(_)}\n")
        for plugin in sorted(plugins, key=lambda p: p.name):
            flags = [plugin.sensitivity.name.lower()]
            if plugin.always:
                flags.append("always")
            sys.stdout.write(
                f"  {plugin.name} ({', '.join(flags)}): {plugin.description.localize(_)}\n"
            )


def _mode_create_diagnostics_dump(
    _omd_root: Path, _global_options: GlobalOptions, parsed: Options, _args: Args
) -> int:
    options = _cli_selection(parsed)
    # NOTE: All the stuff is logged on this level only, which is below the default WARNING level.
    loading_result = load_config()
    catalogue = load_plugin_catalogue(logger=ConsoleLogger())

    if options.list_plugins:
        _print_available_plugins(catalogue)
        return 0

    dump = create_diagnostics_dump_v2(
        omd_root=cmk.utils.paths.omd_root,
        diagnostics_dir=cmk.utils.paths.diagnostics_dir,
        selection=_resolve_cli_selection(catalogue, options),
        loading_result=loading_result,
    )
    logger = ConsoleLogger()
    logger.section_step("Creating diagnostics dump", verbose=False)
    if dump.tarfile_created:
        logger.filepath(
            dump.tarfile_path.relative_to(cmk.utils.paths.omd_root),
            verbose=False,
        )
    else:
        logger.message("No dump")
    return 0


cli_command_create_diagnostics_dump = CLICommand(
    long_option="create-diagnostics-dump",
    handler_function=_mode_create_diagnostics_dump,
    sub_options=[
        CLIOption(
            long_option="list",
            short_help="List the available topics and plugins and exit",
        ),
        CLIOption(
            long_option="all-topics",
            short_help=(
                "Select all plugins of all topics up to the given sensitivity threshold "
                "(off, low, medium or high)"
            ),
            argument=True,
            argument_descr="THRESHOLD",
        ),
        CLIOption(
            long_option="plugins",
            short_help="Additionally select the given plugins, regardless of topic thresholds",
            argument=True,
            argument_descr="NAME,NAME...",
        ),
        CLIOption(
            long_option="checkmk-server-host",
            short_help=(
                "The name of the host monitoring the Checkmk server; needed by some plugins"
            ),
            argument=True,
            argument_descr="HOST",
        ),
    ],
    short_help="Create diagnostics dump",
    long_help=[
        (
            "Create a dump containing information for diagnostic analysis "
            "in the folder var/check_mk/diagnostics. The dump content is "
            "provided by discoverable plugins grouped into topics; use --list "
            "to see what is available on this site. Without any option only "
            "the always collected plugins are packed."
        )
    ],
)
