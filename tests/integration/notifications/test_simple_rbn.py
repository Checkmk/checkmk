#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Iterator

import pytest

from tests.testlib import WatchLog
from tests.testlib.site import Site


@pytest.fixture(name="fake_sendmail")
def fake_sendmail_fixture(site: Site) -> Iterator[None]:
    site.write_text_file(
        "local/bin/sendmail", '#!/bin/bash\nset -e\necho "sendmail called with: $@"\n'
    )
    os.chmod(site.path("local/bin/sendmail"), 0o775)
    yield
    site.delete_file("local/bin/sendmail")


@pytest.fixture(name="test_user")
def fixture_test_user(site: Site) -> Iterator[None]:
    initial_users = site.openapi.get_all_users()
    assert len(initial_users) == 2  # expect cmkadmin and automation user

    username = "hh"
    site.openapi.create_user(
        username=username,
        fullname="Harry Hirsch",
        password="1234",
        email=f"{site.id}@localhost",
        contactgroups=["all"],
    )

    all_users = site.openapi.get_all_users()
    assert len(all_users) == len(initial_users) + 1

    try:
        yield
    finally:
        site.openapi.delete_user(username)


@pytest.fixture(name="test_log")
def fixture_test_log(
    site: Site,
    fake_sendmail: None,
    test_user: None,
    disable_checks: None,
    disable_flap_detection: None,
) -> Iterator[WatchLog]:
    site.openapi.create_host(
        "notify-test",
        attributes={
            "ipaddress": "127.0.0.1",
        },
    )
    site.activate_changes_and_wait_for_core_reload()

    try:
        with WatchLog(site, default_timeout=20) as l:
            yield l
    finally:
        site.openapi.delete_host("notify-test")
        site.activate_changes_and_wait_for_core_reload()


def test_simple_rbn_host_notification(test_log: WatchLog, site: Site) -> None:
    site.send_host_check_result("notify-test", 1, "FAKE DOWN", expected_state=1)

    # NOTE: "] " is necessary to get the actual log line and not the external command execution
    test_log.check_logged(
        "] HOST NOTIFICATION: check-mk-notify;notify-test;DOWN;check-mk-notify;FAKE DOWN"
    )
    test_log.check_logged("] HOST NOTIFICATION: hh;notify-test;DOWN;mail;FAKE DOWN")
    test_log.check_logged(
        "] HOST NOTIFICATION RESULT: hh;notify-test;OK;mail;Spooled mail to local mail transmission agent;"
    )


def test_simple_rbn_service_notification(test_log: WatchLog, site: Site) -> None:
    site.send_service_check_result("notify-test", "PING", 2, "FAKE CRIT")

    # NOTE: "] " is necessary to get the actual log line and not the external command execution
    test_log.check_logged(
        "] SERVICE NOTIFICATION: check-mk-notify;notify-test;PING;CRITICAL;check-mk-notify;FAKE CRIT"
    )
    test_log.check_logged("] SERVICE NOTIFICATION: hh;notify-test;PING;CRITICAL;mail;FAKE CRIT")
    test_log.check_logged(
        "] SERVICE NOTIFICATION RESULT: hh;notify-test;PING;OK;mail;Spooled mail to local mail transmission agent;"
    )
