#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Dump the output of commands run on the site"""

import subprocess
from collections.abc import Iterator, Sequence
from pathlib import PurePosixPath

from ._context import CollectContext
from ._exceptions import CollectError, CollectInfo
from ._plugins import DumpItem, GeneratedContent


def collect_command_output(
    context: CollectContext, command_id: str, suffix: str, command: Sequence[str]
) -> Iterator[DumpItem]:
    """Run one command in the site root and dump its output as ``command_<id><suffix>``

    Raises:
        CollectInfo: if the command is not available or produced no output.
        CollectError: if the command returned an error.
    """
    try:
        output = subprocess.check_output(
            list(command),
            text=True,
            stderr=subprocess.STDOUT,
            cwd=context.omd_root,
        )
    except subprocess.CalledProcessError as e:
        raise CollectError("Command %s returned an unexpected error." % " ".join(command)) from e
    except FileNotFoundError as e:
        raise CollectInfo("Command %s not available on this system." % " ".join(command)) from e

    if not output:
        raise CollectInfo("No data")
    yield DumpItem(
        PurePosixPath(f"command_{command_id}{suffix}"), GeneratedContent(output.encode())
    )
