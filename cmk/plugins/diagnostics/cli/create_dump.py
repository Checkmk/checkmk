#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --create-diagnostics-dump" command.

The dump itself is built by cmk.base.diagnostics; this only turns the command
line into a selection of diagnostics plug-ins.
"""

import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import cmk.utils.paths
from cmk.base.config import exit_on_config_file_load_error, load_raw_config
from cmk.base.diagnostics import (
    ConsoleLogger,
    create_diagnostics_dump_v2,
    load_plugin_catalogue,
)
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Command as CLICommand
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Flag as CLIFlag
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Reader as CLIReader
from cmk.cli.internal import Value as CLIValue
from cmk.diagnostics.engine import DumpSelection, resolve_selection
from cmk.diagnostics.internal import DiagnosticsPlugin, Sensitivity, Topic

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
class _CliSelection:
    list_plugins: bool
    all_topics: Sensitivity | None
    plugins: Sequence[str]
    checkmk_server_host: str | None


def _cli_selection(options: CLIReader) -> _CliSelection:
    return _CliSelection(
        list_plugins=options.flag(_LIST_FLAG),
        all_topics=options.value(_ALL_TOPICS_VALUE),
        plugins=options.value(_PLUGINS_VALUE) or (),
        checkmk_server_host=options.value(_CHECKMK_SERVER_HOST_VALUE),
    )


def _resolve_cli_selection(
    catalogue: Mapping[str, DiagnosticsPlugin], options: _CliSelection
) -> DumpSelection:
    thresholds: dict[Topic, Sensitivity | None] = dict.fromkeys(
        (plugin.topic for plugin in catalogue.values()), options.all_topics
    )

    selected = set(resolve_selection(catalogue.values(), thresholds))
    for name in options.plugins:
        if name not in catalogue:
            raise MKGeneralException("Unknown plugin %r (see --list for available plugins)" % name)
        selected.add(name)

    return DumpSelection(
        plugins=sorted(selected),
        checkmk_server_host=options.checkmk_server_host or "",
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
    _omd_root: Path, global_options: CLIGlobalOptions, options: _CliSelection, _args: CLIArgs
) -> CLIExitCode:
    with exit_on_config_file_load_error(debug=global_options.debug):
        raw_config = load_raw_config()

    # NOTE: All the stuff is logged on this level only, which is below the default WARNING level.
    catalogue = load_plugin_catalogue(logger=ConsoleLogger())

    if options.list_plugins:
        _print_available_plugins(catalogue)
        return CLIExitCode.SUCCESS

    dump = create_diagnostics_dump_v2(
        omd_root=cmk.utils.paths.omd_root,
        diagnostics_dir=cmk.utils.paths.diagnostics_dir,
        selection=_resolve_cli_selection(catalogue, options),
        raw_config=raw_config,
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
    return CLIExitCode.SUCCESS


def _run_create_diagnostics_dump(
    context: CLIContext, options: _CliSelection, args: CLIArgs
) -> CLIExitCode:
    try:
        return _mode_create_diagnostics_dump(
            context.omd_root, context.global_options, options, args
        )
    except MKGeneralException as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


cli_command_create_diagnostics_dump = CLICommand(
    name="create_diagnostics_dump",
    long="create-diagnostics-dump",
    request=_cli_selection,
    handler=_run_create_diagnostics_dump,
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
