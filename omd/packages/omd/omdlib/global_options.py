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


def parse_global_opts(main_args: list[str]) -> tuple[GlobalOptions, list[str]]:
    version: str | None = None
    verbose = False
    force = False
    while len(main_args) >= 1 and main_args[0].startswith("-"):
        token = main_args.pop(0)
        flags = [token[2:]] if token.startswith("--") else list(token[1:])
        for flag in flags:
            match flag:
                case "V" | "version":
                    if len(main_args) < 1:
                        sys.exit(f"Option {flag} needs an argument.")
                    version = main_args.pop(0)
                case "f" | "force":
                    force = True
                case "v" | "verbose":
                    verbose = True
                case _:
                    sys.exit(
                        f"Invalid global option {token}.\nCall omd help for available options."
                    )
    return GlobalOptions(version=version, verbose=verbose, force=force), main_args
