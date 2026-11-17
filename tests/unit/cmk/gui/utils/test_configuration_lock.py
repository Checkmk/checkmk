#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fcntl
import os
from collections.abc import Iterator

import pytest

from cmk.gui.exceptions import RequestTimeout
from cmk.gui.utils.configuration_lock import lock_checkmk_configuration
from cmk.gui.utils.timeout_manager import timeout_manager
from cmk.utils.paths import configuration_lockfile


@pytest.fixture(name="lock_held_elsewhere")
def fixture_lock_held_elsewhere() -> Iterator[None]:
    configuration_lockfile.parent.mkdir(parents=True, exist_ok=True)
    # flock() locks per open file, so this lock blocks the same process as well.
    fd = os.open(configuration_lockfile, os.O_RDONLY | os.O_CREAT, 0o660)
    fcntl.flock(fd, fcntl.LOCK_EX)
    try:
        yield
    finally:
        os.close(fd)


@pytest.mark.usefixtures("request_context", "lock_held_elsewhere")
def test_a_request_timing_out_while_waiting_for_the_lock_blames_the_lock() -> None:
    timeout_manager.enable_timeout(1)
    try:
        with (
            pytest.raises(RequestTimeout, match="Couldn't lock the Checkmk configuration"),
            lock_checkmk_configuration(),
        ):
            pass
    finally:
        timeout_manager.disable_timeout()
