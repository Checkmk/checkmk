#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helpers to enrich test failures with diagnostics gathered from the test host."""

from tests.testlib.common.utils2 import run


def render_command_output(cmd: str, sudo: bool, substitute_user: str | None = None) -> str:
    """Render stdout and stderr from command as string or exception if raised.

    Command execution can have non-zero exit-code.
    """
    try:
        completed_process = run(
            cmd.split(" "),
            sudo=sudo,
            check=False,
            substitute_user=substitute_user,
        )
    except BaseException as excp:
        return f"EXCEPTION '{cmd}':\n{excp}"
    return (
        f"STDOUT '{cmd}':\n{completed_process.stdout}\nSTDERR '{cmd}':\n{completed_process.stderr}"
    )


def add_process_snapshot(excp: BaseException, sudo: bool) -> None:
    """Attach a `top` snapshot to the exception, to see what kept the host busy on a timeout."""
    excp.add_note("-" * 80)
    excp.add_note(render_command_output("top -b -n 1", sudo=sudo))
