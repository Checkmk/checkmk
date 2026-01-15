#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
import time
from collections.abc import Iterator
from typing import Final

import pytest

from cmk.ccc.hostaddress import HostName
from tests.testlib.site import Site

from .watch_log import WatchLog


@pytest.fixture(name="fake_sendmail")
def fake_sendmail_fixture(site: Site) -> Iterator[None]:
    site.write_file("local/bin/sendmail", '#!/bin/bash\nset -e\necho "sendmail called with: $@"\n')
    try:
        site.run(["chmod", "0775", site.path("local/bin/sendmail").as_posix()])
        yield
    finally:
        site.delete_file("local/bin/sendmail")


@pytest.fixture(name="fake_notification_rule")
def fake_notification_rule(site: Site) -> Iterator[None]:
    site.write_file(
        "etc/check_mk/conf.d/wato/notifications.mk",
        """# Written by Checkmk store\n\nnotification_rules += [{'rule_id': 'f03dd14d-63cd-4dac-8339-9b002753aa9e', 'allow_disable': True, 'contact_all': False, 'contact_all_with_email': False, 'contact_object': True, 'description': 'Notify all contacts of a host/service via HTML email', 'disabled': False, 'notify_plugin': ('mail', '1c131382-2cc5-4979-9026-71a935444d1f')}]""",
    )
    try:
        yield
    finally:
        site.write_file(
            "etc/check_mk/conf.d/wato/notifications.mk",
            """# Written by Checkmk store\n\nnotification_rules += [{'description': 'Notify all contacts of a host/service via HTML email', 'comment': '', 'docu_url': '', 'disabled': False, 'allow_disable': True, 'contact_object': True, 'contact_all': False, 'contact_all_with_email': False, 'rule_id': '50cf4824-12ad-41e2-a6f5-efdd21c55ae7', 'notify_plugin': ('mail', {})}]""",
        )


@pytest.fixture(name="fake_notification_parameter")
def fake_notification_parameter(site: Site) -> Iterator[None]:
    site.write_file(
        "etc/check_mk/conf.d/wato/notification_parameter.mk",
        """# Written by Checkmk store\n\nnotification_parameter.update({'mail': {'1c131382-2cc5-4979-9026-71a935444d1f': {'general': {'description': 'Migrated from notification rule #0', 'comment': 'Auto migrated on update', 'docu_url': ''}, 'parameter_properties': {}}}})""",
    )
    try:
        yield
    finally:
        # TODO remove this if default rule is removed
        # Back to sample config
        site.delete_file("etc/check_mk/conf.d/wato/notification_parameter.mk")


@pytest.fixture(name="test_user")
def fixture_test_user(site: Site) -> Iterator[None]:
    initial_users = site.openapi.users.get_all()

    username = "hh"
    site.openapi.users.create(
        username=username,
        fullname="Harry Hirsch",
        password="1234abcdabcd",
        email=f"{site.id}@localhost",
        contactgroups=["all"],
    )
    site.activate_changes_and_wait_for_core_reload()

    all_users = site.openapi.users.get_all()
    assert len(all_users) == len(initial_users) + 1

    try:
        yield
    finally:
        site.openapi.users.delete(username)
        site.activate_changes_and_wait_for_core_reload()


@pytest.fixture(name="host")
def fixture_host(site: Site) -> Iterator[HostName]:
    hostname = HostName("notify-test")
    site.openapi.hosts.create(hostname, attributes={"ipaddress": "127.0.0.1"})
    site.activate_changes_and_wait_for_core_reload()

    try:
        yield hostname
    finally:
        site.openapi.hosts.delete(hostname)
        site.activate_changes_and_wait_for_core_reload()


@pytest.mark.usefixtures("fake_sendmail")
@pytest.mark.usefixtures("test_user")
@pytest.mark.usefixtures("fake_notification_rule")
@pytest.mark.usefixtures("fake_notification_parameter")
@pytest.mark.usefixtures("disable_checks")
@pytest.mark.usefixtures("disable_flap_detection")
def test_simple_rbn_host_notification(host: HostName, site: Site) -> None:
    with WatchLog(site, default_timeout=20) as log:
        # This checks the following log files: `var/log/nagios.log` or `var/check_mk/core/history`.
        site.send_host_check_result(host, 1, "FAKE DOWN", expected_state=1)

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

    # And check that the notifications are recorded in the log.
    with WatchLog(site, default_timeout=30) as log:
        # Now generate the service notification.
        site.send_service_check_result(host, service, 2, "FAKE CRIT")

        # This checks the following log files: `var/log/nagios.log` or `var/check_mk/core/history`.
        log.check_logged(
            f"] SERVICE NOTIFICATION: check-mk-notify;{host};{service};CRITICAL;check-mk-notify;FAKE CRIT"
        )
        log.check_logged(f"] SERVICE NOTIFICATION: hh;{host};{service};CRITICAL;mail;FAKE CRIT")
        log.check_logged(
            f"] SERVICE NOTIFICATION RESULT: hh;{host};{service};OK;mail;Spooled mail to local mail transmission agent;"
        )
