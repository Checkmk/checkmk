#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class GlobalOptions:
    version: str | None = None
    verbose: bool = False
    force: bool = False
    interactive: bool = False


def parse_global_opts(main_args: list[str]) -> tuple[GlobalOptions, list[str]]:
    global_opts = GlobalOptions()
    while len(main_args) >= 1 and main_args[0].startswith("-"):
        opt = main_args[0]
        main_args = main_args[1:]
        if opt.startswith("--"):
            global_opts, main_args = _handle_global_option(global_opts, main_args, opt[2:], opt)
        else:
            for c in opt[1:]:
                global_opts, main_args = _handle_global_option(global_opts, main_args, c, opt)
    return global_opts, main_args


def _handle_global_option(
    global_opts: GlobalOptions, main_args: list[str], opt: str, orig: str
) -> tuple[GlobalOptions, list[str]]:
    version = global_opts.version
    verbose = global_opts.verbose
    force = global_opts.force
    interactive = global_opts.interactive

    if opt in ["V", "version"]:
        version, main_args = _opt_arg(main_args, opt)
    elif opt in ["f", "force"]:
        force = True
        interactive = False
    elif opt in ["i", "interactive"]:
        force = False
        interactive = True
    elif opt in ["v", "verbose"]:
        verbose = True
    else:
        sys.exit("Invalid global option %s.\nCall omd help for available options." % orig)

    new_global_opts = GlobalOptions(
        version=version,
        verbose=verbose,
        force=force,
        interactive=interactive,
    )

    return new_global_opts, main_args


def _opt_arg(main_args: list[str], opt: str) -> tuple[str, list[str]]:
    if len(main_args) < 1:
        sys.exit("Option %s needs an argument." % opt)
    arg = main_args[0]
    main_args = main_args[1:]
    return arg, main_args
