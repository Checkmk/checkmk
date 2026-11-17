#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import cmk.ccc.version as cmk_version
from cmk.ccc.version import Edition, edition
from cmk.cli.internal import Context as CLIContext
from cmk.cli.internal import ExitCode as CLIExitCode
from cmk.cli.internal import Handler as CLIHandler
from cmk.plugins.checkmk.cli.output import write_stdout
from cmk.plugins.checkmk.cli.version import (
    cli_command_version,
)

type _EditionOf = Callable[[Path], Edition]


@dataclass(frozen=True, kw_only=True)
class _VersionCommand:
    edition_of: _EditionOf

    def run(self, context: CLIContext, _request: None) -> CLIExitCode:
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
                self.edition_of(context.omd_root).title,
                cmk_version.__version__,
            )
        )
        return CLIExitCode.SUCCESS


cli_handler_version = CLIHandler(
    command=cli_command_version, run=_VersionCommand(edition_of=edition).run
)
