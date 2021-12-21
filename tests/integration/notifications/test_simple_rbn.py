#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import time

import pytest

from tests.testlib import WatchLog
from tests.testlib.site import Site

from cmk.utils import version as cmk_version


@pytest.fixture(name="fake_sendmail")
def fake_sendmail_fixture(site: Site):
    site.write_text_file(
        "local/bin/sendmail", "#!/bin/bash\n" "set -e\n" 'echo "sendmail called with: $@"\n'
    )
    os.chmod(site.path("local/bin/sendmail"), 0o775)
    yield
    site.delete_file("local/bin/sendmail")


@pytest.fixture(
    name="test_log",
    params=[
        ("nagios", "var/log/nagios.log"),
        pytest.param(
            ("cmc", "var/check_mk/core/history"),
            marks=pytest.mark.skipif(
                cmk_version.is_raw_edition(), reason="CMC not supported on CRE"
            ),
        ),
    ],
)
def test_log_fixture(request, site: Site, fake_sendmail):
    core, log = request.param
    site.set_config("CORE", core, with_restart=True)

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

    with WatchLog(site, log, default_timeout=20) as l:
        yield l

    site.live.command("[%d] START_EXECUTING_HOST_CHECKS" % time.time())
    site.live.command("[%d] START_EXECUTING_SVC_CHECKS" % time.time())

    site.openapi.delete_host("notify-test")
    for username in users:
        site.openapi.delete_user(username)
    site.activate_changes_and_wait_for_core_reload()


def test_simple_rbn_host_notification(test_log, site: Site):
    site.send_host_check_result("notify-test", 1, "FAKE DOWN", expected_state=1)

    # NOTE: "] " is necessary to get the actual log line and not the external command execution
    test_log.check_logged(
        "] HOST NOTIFICATION: check-mk-notify;notify-test;DOWN;check-mk-notify;FAKE DOWN"
    )
    test_log.check_logged("] HOST NOTIFICATION: hh;notify-test;DOWN;mail;FAKE DOWN")
    test_log.check_logged(
        "] HOST NOTIFICATION RESULT: hh;notify-test;OK;mail;Spooled mail to local mail transmission agent;"
    )


def test_simple_rbn_service_notification(test_log, site: Site):
    site.send_service_check_result("notify-test", "PING", 2, "FAKE CRIT")

    # NOTE: "] " is necessary to get the actual log line and not the external command execution
    test_log.check_logged(
        "] SERVICE NOTIFICATION: check-mk-notify;notify-test;PING;CRITICAL;check-mk-notify;FAKE CRIT"
    )
    test_log.check_logged("] SERVICE NOTIFICATION: hh;notify-test;PING;CRITICAL;mail;FAKE CRIT")
    test_log.check_logged(
        "] SERVICE NOTIFICATION RESULT: hh;notify-test;PING;OK;mail;Spooled mail to local mail transmission agent;"
    )
