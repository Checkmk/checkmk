#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import time
from typing import Iterator

import pytest

from tests.testlib import WatchLog
from tests.testlib.site import Site


@pytest.fixture(name="fake_sendmail")
def fake_sendmail_fixture(site: Site) -> Iterator[None]:
    site.write_text_file(
        "local/bin/sendmail", "#!/bin/bash\n" "set -e\n" 'echo "sendmail called with: $@"\n'
    )
    os.chmod(site.path("local/bin/sendmail"), 0o775)
    yield
    site.delete_file("local/bin/sendmail")


@pytest.fixture(name="test_log")
def test_log_fixture(site: Site, fake_sendmail) -> Iterator[WatchLog]:
    users = {
        "hh": {
            "fullname": "Harry Hirsch",
            "password": "1234",
            "email": f"{site.id}@localhost",
            "contactgroups": ["all"],
        },
    }

    initial_users = site.openapi.get_all_users()
    assert len(initial_users) == 2  # expect cmkadmin and automation user

    for name, user_dict in users.items():
        site.openapi.create_user(username=name, **user_dict)  # type: ignore
    all_users = site.openapi.get_all_users()
    assert len(all_users) == len(initial_users) + len(users)

    site.live.command("[%d] STOP_EXECUTING_HOST_CHECKS" % time.time())
    site.live.command("[%d] STOP_EXECUTING_SVC_CHECKS" % time.time())

    site.openapi.create_host(
        "notify-test",
        attributes={
            "ipaddress": "127.0.0.1",
        },
    )
    site.activate_changes_and_wait_for_core_reload()

    with WatchLog(site, default_timeout=20) as l:
        yield l

    site.live.command("[%d] START_EXECUTING_HOST_CHECKS" % time.time())
    site.live.command("[%d] START_EXECUTING_SVC_CHECKS" % time.time())

    site.openapi.delete_host("notify-test")
    for username in users:
        site.openapi.delete_user(username)
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
    site.send_service_check_result("notify-test", "Check_MK", 2, "FAKE CRIT")

    # NOTE: "] " is necessary to get the actual log line and not the external command execution
    test_log.check_logged(
        "] SERVICE NOTIFICATION: check-mk-notify;notify-test;Check_MK;CRITICAL;check-mk-notify;FAKE CRIT"
    )
    test_log.check_logged("] SERVICE NOTIFICATION: hh;notify-test;Check_MK;CRITICAL;mail;FAKE CRIT")
    test_log.check_logged(
        "] SERVICE NOTIFICATION RESULT: hh;notify-test;Check_MK;OK;mail;Spooled mail to local mail transmission agent;"
    )
