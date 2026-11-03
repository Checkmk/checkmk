# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import signal
from collections.abc import Iterator

import pytest
from qemu_windows import process


@pytest.fixture(name="signal_handlers")
def fixture_signal_handlers() -> Iterator[None]:
    """Undoes the signal handlers setup() installs."""
    handlers = {signum: signal.getsignal(signum) for signum in (signal.SIGTERM, signal.SIGHUP)}
    yield
    for signum, handler in handlers.items():
        signal.signal(signum, handler)


@pytest.mark.usefixtures("signal_handlers")
def test_sigterm_unwinds_with_the_exit_code_of_a_killed_process() -> None:
    process.setup()
    with pytest.raises(SystemExit) as exit_:
        os.kill(os.getpid(), signal.SIGTERM)
    assert exit_.value.code == 128 + signal.SIGTERM
