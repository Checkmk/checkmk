#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import time
from collections.abc import Iterator
from typing import Final

import pytest

from tests.testlib import WatchLog
from tests.testlib.site import Site

from cmk.utils.hostaddress import HostName


@pytest.fixture(name="fake_sendmail")
def fake_sendmail_fixture(site: Site) -> Iterator[None]:
    site.write_text_file(
        "local/bin/sendmail", '#!/bin/bash\nset -e\necho "sendmail called with: $@"\n'
    )
    try:
        assert site.execute(["chmod", "0775", site.path("local/bin/sendmail")]).wait() == 0
        yield
    finally:
        site.delete_file("local/bin/sendmail")


@pytest.fixture(name="test_user")
def fixture_test_user(site: Site) -> Iterator[None]:
    initial_users = site.openapi.get_all_users()

    username = "hh"
    site.openapi.create_user(
        username=username,
        fullname="Harry Hirsch",
        password="1234abcdabcd",
        email=f"{site.id}@localhost",
        contactgroups=["all"],
        customer="global" if site.version.is_managed_edition() else None,
    )

    all_users = site.openapi.get_all_users()
    assert len(all_users) == len(initial_users) + 1

    try:
        yield
    finally:
        site.openapi.delete_user(username)


@pytest.fixture(name="host")
def fixture_host(site: Site) -> Iterator[HostName]:
    hostname = HostName("notify-test")
    site.openapi.create_host(hostname, attributes={"ipaddress": "127.0.0.1"})
    site.activate_changes_and_wait_for_core_reload()

    try:
        yield hostname
    finally:
        site.openapi.delete_host(hostname)
        site.activate_changes_and_wait_for_core_reload()


@pytest.mark.usefixtures("fake_sendmail")
@pytest.mark.usefixtures("test_user")
@pytest.mark.usefixtures("disable_checks")
@pytest.mark.usefixtures("disable_flap_detection")
def test_simple_rbn_host_notification(host: HostName, site: Site) -> None:
    site.send_host_check_result(host, 1, "FAKE DOWN", expected_state=1)

    with WatchLog(site, default_timeout=20) as log:
        # This checks the following log files: `var/log/nagios.log` or `var/check_mk/core/history`.
        log.check_logged(
            f"] HOST NOTIFICATION: check-mk-notify;{host};DOWN;check-mk-notify;FAKE DOWN"
        )
        log.check_logged(f"] HOST NOTIFICATION: hh;{host};DOWN;mail;FAKE DOWN")
        log.check_logged(
            f"] HOST NOTIFICATION RESULT: hh;{host};OK;mail;Spooled mail to local mail transmission agent;"
        )


@pytest.mark.usefixtures("fake_sendmail")
@pytest.mark.usefixtures("test_user")
@pytest.mark.usefixtures("disable_flap_detection")
@pytest.mark.skip(reason="flaky test")
def test_simple_rbn_service_notification(host: HostName, site: Site) -> None:
    # cmc only has 'Check_MK' and 'Check_MK Discovery'.
    service: Final = "PING" if site.core_name() == "nagios" else "Check_MK"
    assert service in itertools.chain.from_iterable(
        site.live.query("GET services\nColumns: description\n")
    )

    # Trigger a check cycle
    site.send_host_check_result(host, 1, "FAKE DOWN", expected_state=1)
    time.sleep(0.1)
    # But keep the site up or the service notifications will be postponed.
    site.send_host_check_result(host, 0, "FAKE UP", expected_state=0)

    # Now generate the service notification.
    site.send_service_check_result(host, service, 2, "FAKE CRIT")

    # And check that the notifications are recorded in the log.
    with WatchLog(site, default_timeout=30) as log:
        # This checks the following log files: `var/log/nagios.log` or `var/check_mk/core/history`.
        log.check_logged(
            f"] SERVICE NOTIFICATION: check-mk-notify;{host};{service};CRITICAL;check-mk-notify;FAKE CRIT"
        )
        log.check_logged(f"] SERVICE NOTIFICATION: hh;{host};{service};CRITICAL;mail;FAKE CRIT")
        log.check_logged(
            f"] SERVICE NOTIFICATION RESULT: hh;{host};{service};OK;mail;Spooled mail to local mail transmission agent;"
        )
