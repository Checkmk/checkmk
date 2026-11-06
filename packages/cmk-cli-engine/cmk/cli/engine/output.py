#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import shlex
import signal
import subprocess
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from typing import Final


def write_stdout(txt: str) -> None:
    with suppress(IOError):
        sys.stdout.write(txt)
        sys.stdout.flush()


_DEFAULT_PAGER: Final = "less"

_PAGER_PROMPT: Final = (
    "?ltline %lt?L/%L.:byte %bB?s/%s..?e (END):?pB %pB\\%.. (press h for help or q to quit)"
)

_LESS_OPTIONS: Final = f"--no-init --quit-if-one-screen --prompt={_PAGER_PROMPT}$"


def _pager_environment(environ: Mapping[str, str]) -> Mapping[str, str]:
    return {**environ, "LESS": f"{_LESS_OPTIONS} {environ.get('LESS', '')}".rstrip()}


@contextmanager
def _sigint_ignored() -> Iterator[None]:
    previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        yield
    finally:
        signal.signal(signal.SIGINT, previous)


def write_paged(txt: str) -> None:
    if not sys.stdout.isatty():
        write_stdout(txt)
        return

    try:
        with suppress(BrokenPipeError), _sigint_ignored():
            subprocess.run(
                shlex.split(os.environ.get("PAGER") or _DEFAULT_PAGER),
                input=txt,
                text=True,
                check=False,
                env=_pager_environment(os.environ),
            )
    except OSError, ValueError:
        write_stdout(txt)
