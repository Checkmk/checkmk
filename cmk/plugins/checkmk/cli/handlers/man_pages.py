#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.import_filter import blocked_files
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.discover_plugins import discover_families, PluginGroup
from cmk.plugins.checkmk.cli.man_pages import (
    cli_command_browse_man,
    cli_command_man,
    ManRequest,
)
from cmk.utils import man_pages


class _ManPagePaths(Protocol):
    def __call__(self, *, debug: bool) -> Mapping[str, Path]: ...


type _PrintManPageTable = Callable[[Mapping[str, Path]], None]


class _ParseManPage(Protocol):
    def __call__(self, name: str, path: Path, *, debug: bool) -> man_pages.ManPage: ...


def _man_page_paths(*, debug: bool) -> Mapping[str, Path]:
    return man_pages.make_man_page_path_map(
        discover_families(raise_errors=debug),
        PluginGroup.CHECKMAN.value,
        blocked_paths=blocked_files(),
    )


@dataclass(frozen=True, kw_only=True)
class _ManCommand:
    paths: _ManPagePaths
    print_table: _PrintManPageTable
    parse: _ParseManPage

    def run(self, context: CLIContext, request: ManRequest) -> CLIExitCode:
        try:
            man_page_path_map = self.paths(debug=context.global_options.debug)
            if request.check_type is None:
                self.print_table(man_page_path_map)
                return CLIExitCode.SUCCESS

            if (man_page_path := man_page_path_map.get(request.check_type)) is None:
                context.logger.error(
                    "No manpage for %(check_type)s. Sorry.", {"check_type": request.check_type}
                )
                return CLIExitCode.UNKNOWN

            man_page = self.parse(
                request.check_type, man_page_path, debug=context.global_options.debug
            )
            renderer: type[man_pages.ConsoleManPageRenderer] | type[man_pages.NowikiManPageRenderer]
            match request.renderer:
                case "console" | None:
                    renderer = man_pages.ConsoleManPageRenderer
                case "nowiki":
                    renderer = man_pages.NowikiManPageRenderer

            try:
                rendered = renderer(man_page).render_page()
            except Exception as exc:
                sys.stderr.write(f"ERROR: Invalid check manpage {request.check_type}: {exc}\n")
                return CLIExitCode.FAILURE

            man_pages.write_output(rendered)
            return CLIExitCode.SUCCESS
        except MKGeneralException as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN


class _BrowseManPages(Protocol):
    def __call__(self, *, debug: bool) -> None: ...


def _browse_man_pages(*, debug: bool) -> None:
    man_pages.print_man_page_browser(
        man_pages.load_man_page_catalog(
            discover_families(raise_errors=debug),
            PluginGroup.CHECKMAN.value,
            blocked_paths=blocked_files(),
            debug=debug,
        )
    )


@dataclass(frozen=True, kw_only=True)
class _BrowseManCommand:
    browse: _BrowseManPages

    def run(self, context: CLIContext, _request: None) -> CLIExitCode:
        try:
            self.browse(debug=context.global_options.debug)
        except MKGeneralException as e:
            context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
            if context.global_options.debug:
                raise
            return CLIExitCode.UNKNOWN
        return CLIExitCode.SUCCESS


cli_handler_man = CLIHandler(
    command=cli_command_man,
    run=_ManCommand(
        paths=_man_page_paths,
        print_table=man_pages.print_man_page_table,
        parse=man_pages.parse_man_page,
    ).run,
)

cli_handler_browse_man = CLIHandler(
    command=cli_command_browse_man, run=_BrowseManCommand(browse=_browse_man_pages).run
)
