# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import socket
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from .log import colorize


def run_command(  # type: ignore[explicit-any]
    args: Sequence[str],
    check: bool = True,
    error_message: str | None = None,
    raise_runtime_error: bool = True,
    text: bool = True,
    logger: logging.Logger | None = logging.getLogger(__name__),
    silent: bool = False,
    **kwargs: Any,
) -> subprocess.CompletedProcess[Any]:
    result = subprocess.run(args=args, capture_output=True, text=text, check=False, **kwargs)
    msg = f"Running command {colorize(' '.join(args), 'blue')}:"
    if not silent and result.stdout:
        msg = msg + "\nSTDOUT:\n" + colorize(result.stdout.strip(), "green")
    if not silent and result.stderr:
        msg = msg + "\nSTDERR:\n" + colorize(result.stderr.strip(), "red")
    if logger:
        logger.debug(msg)
    if check and result.returncode != 0:
        if raise_runtime_error:
            error_msg = (error_message + "\n") if error_message else ""
            error_msg += (
                f"ERROR: Command failed: {colorize(' '.join(args), 'red')}\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )
            raise RuntimeError(error_msg)
        if logger and error_message:
            logger.warning(error_message)

    return result


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return False
        except OSError:
            return True


def write_root_owned_file(path: Path, content: str, permissions: str = "0666") -> None:
    """Write content to a root-owned file with specified permissions.

    Creates the parent directory if needed, writes the content via sudo,
    and sets the specified permissions. Content is piped through sudo
    to ensure secure writing regardless of permission settings.

    Args:
        path: Path to the file to create/write
        content: String content to write to the file
        permissions: Octal permission string (default: "0666" for world-writable)
    """
    # Create parent directory if needed
    run_command(["sudo", "mkdir", "-p", str(path.parent)])

    # Write content via sudo using tee (silent output)
    run_command(
        ["sudo", "tee", str(path)],
        input=content,
        silent=True,
    )

    # Set permissions
    run_command(["sudo", "chmod", permissions, str(path)])
