#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects


import fcntl
import os
import threading
from collections.abc import Iterator

import pytest

from cmk.ccc.user import UserId
from cmk.utils.paths import configuration_lockfile
from tests.testlib.unit.gui.openapi_test_helper import (
    clear_app_instance_caches,
    create_api_client,
    create_sample_host_context,
    create_test_groups,
)
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK
from tests.testlib.unit.rest_api_client import RestApiClient


@pytest.fixture()
def api_client(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base_without_version: str
) -> RestApiClient:
    return create_api_client(aut_user_auth_wsgi_app, base_without_version)


@pytest.fixture()
def with_groups(
    monkeypatch: pytest.MonkeyPatch,
    request_context: None,
    with_admin_login: UserId,
    suppress_remote_automation_calls: object,
) -> Iterator[None]:
    yield from create_test_groups(monkeypatch)


@pytest.fixture(name="sample_host")
def fixture_sample_host(request_context: None) -> Iterator[str]:
    yield from create_sample_host_context()


@pytest.fixture(name="fresh_app_instance", scope="function")
def clear_caches_flask_app() -> None:
    clear_app_instance_caches()


@pytest.fixture(name="setup_lock_held_elsewhere")
def fixture_setup_lock_held_elsewhere() -> Iterator[threading.Event]:
    """Hold the configuration lock of Setup like another process until the end of the test

    A watchdog releases the lock early and sets the event, so that a call that waits for the lock
    fails instead of hanging. Its timeout is far beyond the duration of a call that does not wait,
    and such a call costs no time."""
    released_by_watchdog = threading.Event()
    configuration_lockfile.parent.mkdir(parents=True, exist_ok=True)
    # flock() locks per open file, so this lock blocks the same process as well.
    fd = os.open(configuration_lockfile, os.O_RDONLY | os.O_CREAT, 0o660)
    fcntl.flock(fd, fcntl.LOCK_EX)

    def release_by_watchdog() -> None:
        released_by_watchdog.set()
        fcntl.flock(fd, fcntl.LOCK_UN)

    watchdog = threading.Timer(10.0, release_by_watchdog)
    watchdog.start()
    try:
        yield released_by_watchdog
    finally:
        watchdog.cancel()
        watchdog.join()
        os.close(fd)
