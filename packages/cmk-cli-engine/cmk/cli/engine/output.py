#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shlex
import signal
import subprocess
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from typing import Final, TextIO


def _write(stream: TextIO, txt: str) -> None:
    with suppress(IOError):
        stream.write(txt)
        stream.flush()


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


type _RunPager = Callable[[Sequence[str], str, Mapping[str, str]], object]


def run_pager(command: Sequence[str], txt: str, environ: Mapping[str, str]) -> None:
    subprocess.run(command, input=txt, text=True, check=False, env=environ)


@dataclass(frozen=True, kw_only=True)
class Console:
    stdout: TextIO
    stderr: TextIO
    environ: Mapping[str, str]
    run_pager: _RunPager

    def write_error(self, txt: str) -> None:
        _write(self.stderr, txt)

    def page(self, txt: str) -> None:
        if not self.stdout.isatty():
            _write(self.stdout, txt)
            return

        try:
            with suppress(BrokenPipeError), _sigint_ignored():
                self.run_pager(
                    shlex.split(self.environ.get("PAGER") or _DEFAULT_PAGER),
                    txt,
                    _pager_environment(self.environ),
                )
        except OSError, ValueError:
            _write(self.stdout, txt)
