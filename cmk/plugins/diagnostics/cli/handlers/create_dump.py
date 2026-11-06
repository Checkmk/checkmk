#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Mapping
from pathlib import Path

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
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Handler as CLIHandler
from cmk.diagnostics.engine import DumpSelection, resolve_selection
from cmk.diagnostics.internal import DiagnosticsPlugin, Sensitivity, Topic
from cmk.plugins.diagnostics.cli.create_dump import (
    cli_command_create_diagnostics_dump,
    CliSelection,
)


def _resolve_cli_selection(
    catalogue: Mapping[str, DiagnosticsPlugin], options: CliSelection
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
    _omd_root: Path, global_options: CLIGlobalOptions, options: CliSelection, _args: CLIArgs
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
    context: CLIContext, options: CliSelection, args: CLIArgs
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


cli_handler_create_diagnostics_dump = CLIHandler(
    command=cli_command_create_diagnostics_dump, run=_run_create_diagnostics_dump
)
