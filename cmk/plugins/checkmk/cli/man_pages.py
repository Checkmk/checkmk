#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --man" and "cmk --browse-man" commands."""

import sys
from pathlib import Path

import cmk.ccc.debug
from cmk.ccc.exceptions import MKBailOut, MKGeneralException
from cmk.cli.internal import (
    Args,
    CLICommand,
    CLIOption,
    CommandContext,
    ExitCode,
    GlobalOptions,
    Options,
)
from cmk.discover_plugins import discover_families, PluginGroup
from cmk.licensing.basics.finder import blocked_feature_files
from cmk.utils.paths import omd_root


def _mode_man(
    _omd_root: Path, _global_options: GlobalOptions, options: Options, args: Args
) -> ExitCode:
    from cmk.utils import man_pages

    man_page_path_map = man_pages.make_man_page_path_map(
        discover_families(raise_errors=cmk.ccc.debug.enabled()),
        PluginGroup.CHECKMAN.value,
        blocked_paths=blocked_feature_files(omd_root),
    )
    if not args:
        man_pages.print_man_page_table(man_page_path_map)
        return ExitCode.SUCCESS

    if (man_page_path := man_page_path_map.get(args[0])) is None:
        raise MKBailOut(f"No manpage for {args[0]}. Sorry.")

    man_page = man_pages.parse_man_page(args[0], man_page_path)
    renderer: type[man_pages.ConsoleManPageRenderer] | type[man_pages.NowikiManPageRenderer]
    match options.get("renderer", "console"):
        case "console":
            renderer = man_pages.ConsoleManPageRenderer
        case "nowiki":
            renderer = man_pages.NowikiManPageRenderer
        case other:
            raise ValueError(other)

    try:
        rendered = renderer(man_page).render_page()
    except Exception as exc:
        sys.stdout.write(f"ERROR: Invalid check manpage {args[0]}: {exc}\n")
        return ExitCode.SUCCESS

    man_pages.write_output(rendered)
    return ExitCode.SUCCESS


def _run_man(context: CommandContext, options: Options, args: Args) -> ExitCode:
    if context.global_options.debug:
        # discover_families() is told by cmk.ccc.debug whether to raise
        cmk.ccc.debug.enable()
    try:
        return _mode_man(context.omd_root, context.global_options, options, args)
    except (MKBailOut, MKGeneralException) as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return ExitCode.UNKNOWN


cli_command_man = CLICommand(
    long_option="man",
    short_option="M",
    handler_function=_run_man,
    argument=True,
    argument_descr="CHECKTYPE",
    argument_optional=True,
    sub_options=[
        CLIOption(
            long_option="renderer",
            short_option="r",
            argument=True,
            argument_descr="RENDERER",
            short_help="Use the given renderer: 'console' or 'nowiki'. Defaults to 'console'.",
        ),
    ],
    short_help="Show manpage for check CHECKTYPE",
    long_help=[
        (
            "Shows documentation about a check type. If /usr/bin/less is "
            "available it is used as pager. Exit by pressing Q. "
            "Use -M without an argument to show a list of all manual pages."
        )
    ],
)


def _mode_browse_man(
    _omd_root: Path, _global_options: GlobalOptions, _options: Options, _args: Args
) -> ExitCode:
    from cmk.utils import man_pages

    man_pages.print_man_page_browser(
        man_pages.load_man_page_catalog(
            discover_families(raise_errors=cmk.ccc.debug.enabled()),
            PluginGroup.CHECKMAN.value,
            blocked_paths=blocked_feature_files(omd_root),
        )
    )
    return ExitCode.SUCCESS


def _run_browse_man(context: CommandContext, options: Options, args: Args) -> ExitCode:
    if context.global_options.debug:
        # discover_families() is told by cmk.ccc.debug whether to raise
        cmk.ccc.debug.enable()
    try:
        return _mode_browse_man(context.omd_root, context.global_options, options, args)
    except MKGeneralException as e:
        context.logger.error("%(error)s", {"error": e})  # noqa: TRY400
        if context.global_options.debug:
            raise
        return ExitCode.UNKNOWN


cli_command_browse_man = CLICommand(
    long_option="browse-man",
    short_option="m",
    handler_function=_run_browse_man,
    short_help="Open interactive manpage browser",
)
