#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The "cmk --version" command."""

from pathlib import Path

import cmk.ccc.version as cmk_version
from cmk.ccc.version import edition
from cmk.cli.engine.commands import (
    write_stdout,
)
from cmk.cli.internal import Args, CLICommand, GlobalOptions, Options


def _mode_version(
    omd_root: Path, _global_options: GlobalOptions, _options: Options, _args: Args
) -> int:
    write_stdout(
        """This is %s version %s
Copyright (C) 2009 Checkmk GmbH

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; see the file COPYING.  If not, write to
    the Free Software Foundation, Inc., 59 Temple Place - Suite 330,
    Boston, MA 02111-1307, USA.

"""
        % (
            edition(omd_root).title,
            cmk_version.__version__,
        )
    )
    return 0


cli_command_version = CLICommand(
    long_option="version",
    short_option="V",
    handler_function=_mode_version,
    short_help="Print the version of Checkmk",
)
