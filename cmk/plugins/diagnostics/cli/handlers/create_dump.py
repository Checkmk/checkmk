#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import cmk.utils.paths
from cmk.base.config import ConfigFileLoadError, load_raw_config
from cmk.base.diagnostics import (
    ConsoleLogger,
    create_diagnostics_dump_v2,
    load_plugin_catalogue,
)
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.i18n import _
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
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


type _LoadCatalogue = Callable[[], Mapping[str, DiagnosticsPlugin]]


class _CreateDump(Protocol):
    def __call__(self, omd_root: Path, selection: DumpSelection) -> Path | None: ...


def _load_catalogue() -> Mapping[str, DiagnosticsPlugin]:
    return load_plugin_catalogue(logger=ConsoleLogger())


def _create_dump(omd_root: Path, selection: DumpSelection) -> Path | None:
    raw_config = load_raw_config(omd_root=omd_root)

    dump = create_diagnostics_dump_v2(
        omd_root=omd_root,
        diagnostics_dir=cmk.utils.paths.diagnostics_dir,
        selection=selection,
        raw_config=raw_config,
    )
    return dump.tarfile_path if dump.tarfile_created else None


@dataclass(frozen=True, kw_only=True)
class _CreateDiagnosticsDumpCommand:
    load_catalogue: _LoadCatalogue
    create_dump: _CreateDump

    def run(self, context: CLIContext, options: CliSelection) -> CLIExitCode:
        try:
            catalogue = self.load_catalogue()

            if options.list_plugins:
                _print_available_plugins(catalogue)
                return CLIExitCode.SUCCESS

            tarfile_path = self.create_dump(
                context.omd_root,
                _resolve_cli_selection(catalogue, options),
            )
            logger = ConsoleLogger()
            logger.section_step("Creating diagnostics dump", verbose=False)
            if tarfile_path is None:
                logger.message("No dump")
            else:
                logger.filepath(tarfile_path.relative_to(context.omd_root), verbose=False)
            return CLIExitCode.SUCCESS
        except ConfigFileLoadError as e:
            if context.global_options.debug:
                raise
            if sys.stderr.isatty():
                sys.stderr.write(f"{e}\n")
            return CLIExitCode.FAILURE
        except MKGeneralException as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN


cli_handler_create_diagnostics_dump = CLIHandler(
    command=cli_command_create_diagnostics_dump,
    run=_CreateDiagnosticsDumpCommand(load_catalogue=_load_catalogue, create_dump=_create_dump).run,
)
