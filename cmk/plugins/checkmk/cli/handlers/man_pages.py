#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from pathlib import Path

from cmk.ccc.exceptions import MKBailOut, MKGeneralException
from cmk.cli.internal import Args as CLIArgs
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import GlobalOptions as CLIGlobalOptions
from cmk.cli.internal import Handler as CLIHandler
from cmk.discover_plugins import discover_families, PluginGroup
from cmk.licensing.basics.finder import blocked_feature_files
from cmk.plugins.checkmk.cli.man_pages import (
    cli_command_browse_man,
    cli_command_man,
    Renderer,
)
from cmk.utils.paths import omd_root


def _mode_man(
    _omd_root: Path, global_options: CLIGlobalOptions, requested: Renderer | None, args: CLIArgs
) -> CLIExitCode:
    from cmk.utils import man_pages

    man_page_path_map = man_pages.make_man_page_path_map(
        discover_families(raise_errors=global_options.debug),
        PluginGroup.CHECKMAN.value,
        blocked_paths=blocked_feature_files(omd_root),
    )
    if not args:
        man_pages.print_man_page_table(man_page_path_map)
        return CLIExitCode.SUCCESS

    if (man_page_path := man_page_path_map.get(args[0])) is None:
        raise MKBailOut(f"No manpage for {args[0]}. Sorry.")

    man_page = man_pages.parse_man_page(args[0], man_page_path, debug=global_options.debug)
    renderer: type[man_pages.ConsoleManPageRenderer] | type[man_pages.NowikiManPageRenderer]
    match requested:
        case "console" | None:
            renderer = man_pages.ConsoleManPageRenderer
        case "nowiki":
            renderer = man_pages.NowikiManPageRenderer

    try:
        rendered = renderer(man_page).render_page()
    except Exception as exc:
        sys.stderr.write(f"ERROR: Invalid check manpage {args[0]}: {exc}\n")
        return CLIExitCode.FAILURE

    man_pages.write_output(rendered)
    return CLIExitCode.SUCCESS


def _run_man(context: CLIContext, requested: Renderer | None, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_man(context.omd_root, context.global_options, requested, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


def _mode_browse_man(
    _omd_root: Path, global_options: CLIGlobalOptions, _request: None, _args: CLIArgs
) -> CLIExitCode:
    from cmk.utils import man_pages

    man_pages.print_man_page_browser(
        man_pages.load_man_page_catalog(
            discover_families(raise_errors=global_options.debug),
            PluginGroup.CHECKMAN.value,
            blocked_paths=blocked_feature_files(omd_root),
            debug=global_options.debug,
        )
    )
    return CLIExitCode.SUCCESS


def _run_browse_man(context: CLIContext, request: None, args: CLIArgs) -> CLIExitCode:
    try:
        return _mode_browse_man(context.omd_root, context.global_options, request, args)
    except MKGeneralException as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return CLIExitCode.UNKNOWN


cli_handler_man = CLIHandler(command=cli_command_man, run=_run_man)

cli_handler_browse_man = CLIHandler(command=cli_command_browse_man, run=_run_browse_man)
