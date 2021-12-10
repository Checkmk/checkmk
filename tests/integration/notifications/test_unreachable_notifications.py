#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import errno
import os
import time
from typing import Optional

import pytest

from tests.testlib import wait_until, WatchLog
from tests.testlib.site import Site

from cmk.utils import version as cmk_version

STATE_UP = 0
STATE_DOWN = 1
STATE_UNREACHABLE = 2


class Scenario:
    @classmethod
    def get_test_id(cls, scenario):
        if scenario.unreachable_enabled:
            unreachable_label = "unreachable_enabled"
        else:
            unreachable_label = "unreachable_disabled"

        return "%s-%s" % (scenario.core, unreachable_label)

    def __init__(self, core, unreachable_enabled):
        self.core = core
        self.unreachable_enabled = unreachable_enabled

        if core == "cmc":
            self.log: Optional[str] = "var/check_mk/core/history"
        elif core == "nagios":
            self.log = "var/nagios/nagios.log"
        else:
            self.log = None

    @property
    def log_timeout(self):
        return 10 if self.core == "cmc" else 30


@pytest.fixture(
    name="scenario",
    scope="module",
    params=[
        pytest.param(
            Scenario(core="cmc", unreachable_enabled=True),
            marks=pytest.mark.skipif(
                cmk_version.is_raw_edition(), reason="CMC not available on CRE"
            ),
        ),
        pytest.param(
            Scenario(core="cmc", unreachable_enabled=False),
            marks=pytest.mark.skipif(
                cmk_version.is_raw_edition(), reason="CMC not available on CRE"
            ),
        ),
        Scenario(core="nagios", unreachable_enabled=True),
        Scenario(core="nagios", unreachable_enabled=False),
    ],
    ids=Scenario.get_test_id,
)
def scenario_fixture(request, web, site: Site):  # noqa: F811 # pylint: disable=redefined-outer-name
    core = request.param.core
    unreachable_enabled = request.param.unreachable_enabled
    site.set_core(core)

    try:
        print("Applying test config")

        site.openapi.create_host(
            "notify-test-parent",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )

        site.openapi.create_host(
            "notify-test-child",
            attributes={
                "ipaddress": "127.0.0.1",
                "parents": ["notify-test-parent"],
            },
        )

        if unreachable_enabled:
            notification_options = "d,u,r,f,s"
        else:
            notification_options = "d,r,f,s"

        # Replace with RestAPI, see CMK-9251
        rule_result = web.get_ruleset("extra_host_conf:notification_options")
        rule_result["ruleset"] = {
            "": [{"condition": {}, "options": {}, "value": notification_options}]
        }
        # Replace with RestAPI, see CMK-9251
        web.set_ruleset("extra_host_conf:notification_options", rule_result)

        site.activate_changes_and_wait_for_core_reload()

        site.live.command("[%d] DISABLE_HOST_CHECK;notify-test-parent" % time.time())
        site.live.command("[%d] DISABLE_SVC_CHECK;notify-test-parent;PING" % time.time())
        site.live.command(
            "[%d] DISABLE_SVC_CHECK;notify-test-parent;Check_MK Discovery" % time.time()
        )

        site.live.command("[%d] DISABLE_HOST_CHECK;notify-test-child" % time.time())
        site.live.command("[%d] DISABLE_SVC_CHECK;notify-test-child;PING" % time.time())
        site.live.command(
            "[%d] DISABLE_SVC_CHECK;notify-test-child;Check_MK Discovery" % time.time()
        )

        site.live.command("[%d] DISABLE_FLAP_DETECTION" % time.time())

        yield request.param
    finally:
        #
        # Cleanup code
        #
        print("Cleaning up default config")

        site.live.command("[%d] ENABLE_FLAP_DETECTION" % time.time())
        site.live.command("[%d] ENABLE_HOST_CHECK;notify-test-child" % time.time())
        site.live.command("[%d] ENABLE_HOST_CHECK;notify-test-parent" % time.time())

        site.openapi.delete_host("notify-test-child")
        site.openapi.delete_host("notify-test-parent")

        site.activate_changes_and_wait_for_core_reload()


@pytest.fixture(name="initial_state", scope="function")
def initial_state_fixture(site: Site, scenario):
    # Before each test: Set to initial state: Both UP
    site.send_host_check_result("notify-test-child", 0, "UP")
    site.send_host_check_result("notify-test-parent", 0, "UP")

    # Before each test: Clear logs
    if scenario.core == "cmc":
        # The command is processed asynchronously -> Wait for completion
        inode_before = os.stat(site.path("var/check_mk/core/history")).st_ino
        site.live.command("[%d] ROTATE_LOGFILE" % time.time())

        def rotated_log():
            try:
                return inode_before != os.stat(site.path("var/check_mk/core/history")).st_ino
            except OSError as e:
                if e.errno == errno.ENOENT:
                    return False
                raise e

        wait_until(rotated_log, timeout=10)
    else:
        site.delete_file("var/nagios/nagios.log")


def _send_child_down(scenario, site: Site, log):
    # - Set child down, expect DOWN notification
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")
    log.check_logged("HOST ALERT: notify-test-child;DOWN;HARD;1;DOWN")

    if scenario.core == "cmc":
        # CMC: Send a new check result for the parent to make the CMC create the host notification
        # for the child
        site.send_host_check_result("notify-test-parent", STATE_UP, "UP")

    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;DOWN;check-mk-notify;")


def _send_parent_down(scenario, site: Site, log):
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")
    log.check_logged("HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN")


def _send_parent_recovery(scenario, site: Site, log):
    site.send_host_check_result("notify-test-parent", STATE_UP, "UP")
    log.check_logged("HOST ALERT: notify-test-parent;UP;HARD;1;")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;UP")


def _send_child_recovery(scenario, site: Site, log):
    site.send_host_check_result("notify-test-child", STATE_UP, "UP")
    log.check_logged("HOST ALERT: notify-test-child;UP;HARD;1;")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UP")


def _send_child_down_expect_unreachable(scenario, site: Site, log):
    assert site.get_host_state("notify-test-child") == STATE_UP
    site.send_host_check_result(
        "notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE
    )

    log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")
    if scenario.unreachable_enabled:
        log.check_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
        )
    else:
        log.check_not_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
        )


# Test the situation where:
# a) Child goes down
# b) Parent goes down
# c) child becomes unreachable
def test_unreachable_child_down_before_parent_down(scenario, site: Site, initial_state):
    with WatchLog(site, scenario.log, default_timeout=scenario.log_timeout) as log:
        # - Set child down, expect DOWN notification
        _send_child_down(scenario, site, log)

        # - Set parent down, expect DOWN notification for parent and UNREACHABLE notification for child
        _send_parent_down(scenario, site, log)

        if scenario.core == "cmc":
            log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

            if scenario.unreachable_enabled:
                log.check_logged(
                    "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
                )
            # TODO: Can not check this at the moment
            # else:
            #    log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")
            log.check_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
            )

        elif scenario.core == "nagios":
            log.check_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
            )

            # Difference beween nagios/cmc: when sending DOWN via PROCESS_HOST_CHECK_RESULT
            # the nagios core needs another child down check result to report it as unreachable.
            site.send_host_check_result(
                "notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE
            )
            log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

            if scenario.unreachable_enabled:
                log.check_logged(
                    "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
                )
            # TODO: Can not check this at the moment
            # else:
            #    log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")


# Test the situation where:
# a) Parent goes down
# b) Child goes down, becomes unreachable
def test_unreachable_child_after_parent_is_down(scenario, site: Site, initial_state):
    with WatchLog(site, scenario.log, default_timeout=scenario.log_timeout) as log:
        # - Set parent down, expect DOWN notification
        _send_parent_down(scenario, site, log)
        log.check_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
        )

        # - set child down, expect UNREACHABLE notification
        _send_child_down_expect_unreachable(scenario, site, log)


# Test the situation where:
# a) Child goes down
# b) Parent goes down
# c) Child goes up while parent is down
def test_parent_down_child_up_on_up_result(scenario, site: Site, initial_state):
    with WatchLog(site, scenario.log, default_timeout=scenario.log_timeout) as log:
        # - Set child down, expect DOWN notification
        _send_child_down(scenario, site, log)

        # - Set parent down, expect DOWN notification
        _send_parent_down(scenario, site, log)
        log.check_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
        )

        # - Set child up, expect UP notification
        _send_child_recovery(scenario, site, log)


# Test the situation where:
# a) Parent goes down
# b) Child goes down and becomes unreachable
# c) Child goes up while parent is down
# d) Child goes down and becomes unreachable while parent is down
def test_parent_down_child_state_changes(scenario, site: Site, initial_state):
    with WatchLog(site, scenario.log, default_timeout=scenario.log_timeout) as log:
        # - Set parent down, expect DOWN notification
        _send_parent_down(scenario, site, log)
        log.check_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
        )

        # - set child down, expect UNREACHABLE notification
        assert site.get_host_state("notify-test-child") == STATE_UP
        site.send_host_check_result(
            "notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE
        )
        log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

        if scenario.unreachable_enabled:
            log.check_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
            )
        else:
            log.check_not_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
            )

        # - set child up, expect UP notification
        site.send_host_check_result("notify-test-child", STATE_UP, "UP")
        log.check_logged("HOST ALERT: notify-test-child;UP;HARD;1;")

        if scenario.unreachable_enabled:
            log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;")
        else:
            log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;")

        # - set child down, expect UNREACHABLE notification
        assert site.get_host_state("notify-test-child") == STATE_UP
        site.send_host_check_result(
            "notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE
        )
        log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

        if scenario.unreachable_enabled:
            log.check_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
            )
        else:
            log.check_not_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
            )


# Test the situation where:
# a) Parent goes down
# b) Child goes down and becomes unreachable
# c) Parent goes up
# d) Child is still down and becomes down
def test_child_down_after_parent_recovers(scenario, site: Site, initial_state):
    with WatchLog(site, scenario.log, default_timeout=scenario.log_timeout) as log:
        # - Set parent down, expect DOWN notification
        _send_parent_down(scenario, site, log)
        log.check_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
        )

        # - set child down, expect UNREACHABLE notification
        _send_child_down_expect_unreachable(scenario, site, log)

        # - Set parent up, expect UP notification
        _send_parent_recovery(scenario, site, log)

        # - Next child check DOWN, expect no notification (till next parent check confirms UP)
        site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")
        log.check_logged("HOST ALERT: notify-test-child;DOWN;HARD;1;")

        if scenario.core == "cmc":
            # - Set parent UP (again), expect DOWN notification for child
            site.send_host_check_result("notify-test-parent", STATE_UP, "UP")

        log.check_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-child;DOWN;check-mk-notify;"
        )


# Test the situation where:
# a) Parent goes down
# b) Child goes down and becomes unreachable
# c) Parent goes up
# d) Child goes up
def test_child_up_after_parent_recovers(scenario, site: Site, initial_state):
    with WatchLog(site, scenario.log, default_timeout=scenario.log_timeout) as log:
        # - Set parent down, expect DOWN notification
        _send_parent_down(scenario, site, log)
        log.check_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
        )

        # - set child down, expect UNREACHABLE notification
        _send_child_down_expect_unreachable(scenario, site, log)

        # - Set parent up, expect UP notification
        _send_parent_recovery(scenario, site, log)

        # - Next service check UP, expect no notification (till next parent check confirms UP)
        site.send_host_check_result("notify-test-child", STATE_UP, "UP")
        log.check_logged("HOST ALERT: notify-test-child;UP;HARD;1;")

        # - Set parent UP, expect UP notification for child
        site.send_host_check_result("notify-test-parent", STATE_UP, "UP")

        if scenario.unreachable_enabled:
            log.check_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-child;UP;check-mk-notify;"
            )
        else:
            log.check_not_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-child;UP;check-mk-notify;"
            )


# Test the situation where:
# a) Parent goes down
# b) Child goes down and becomes unreachable
# c) Child goes up
# d) Parent goes up
def test_child_down_and_up_while_not_reachable(scenario, site: Site, initial_state):
    with WatchLog(site, scenario.log, default_timeout=scenario.log_timeout) as log:
        # - Set parent down, expect DOWN notification
        _send_parent_down(scenario, site, log)
        log.check_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
        )

        # - set child down, expect UNREACHABLE notification
        _send_child_down_expect_unreachable(scenario, site, log)

        # - Set child up, expect no notification
        site.send_host_check_result("notify-test-child", STATE_UP, "UP")
        log.check_logged("HOST ALERT: notify-test-child;UP;HARD;1;")

        if scenario.unreachable_enabled:
            log.check_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-child;UP;check-mk-notify;"
            )
        else:
            log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UP")

        # - Set parent up, expect UP notification
        _send_parent_recovery(scenario, site, log)


# Test the situation where:
# a) Child goes down
# b) Parent goes down, child becomes unreachable
# d) Parent goes up, child becomes down
def test_down_child_becomes_unreachable_and_down_again(scenario, site: Site, initial_state):
    with WatchLog(site, scenario.log, default_timeout=scenario.log_timeout) as log:
        # - Set child down, expect DOWN notification
        _send_child_down(scenario, site, log)

        # - Set parent down, expect DOWN notification for parent and UNREACHABLE notification for child
        _send_parent_down(scenario, site, log)

        # Difference beween nagios/cmc: when sending DOWN via PROCESS_HOST_CHECK_RESULT
        # the nagios core needs another child down check result to report it as unreachable.
        if scenario.core == "cmc":
            log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

            if scenario.unreachable_enabled:
                log.check_logged(
                    "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
                )
            # TODO: Can not test this because it drains too many entries from the log. WatchLog could deal
            # with this by readding the read lines after succeeded test or similar
            # else:
            #    log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")

            log.check_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
            )

        elif scenario.core == "nagios":
            log.check_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
            )

            site.send_host_check_result(
                "notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE
            )
            log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

            if scenario.unreachable_enabled:
                log.check_logged(
                    "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
                )

        # - Set parent up, expect UP notification
        _send_parent_recovery(scenario, site, log)

        # - Next child check DOWN
        #   cmc: expect no notification (till next parent check confirms UP)
        #   nagios: expect notification without
        site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")
        log.check_logged("HOST ALERT: notify-test-child;DOWN;HARD;1;")

        if scenario.core == "cmc":
            # - Set parent UP (again), expect DOWN notification for child
            site.send_host_check_result("notify-test-parent", STATE_UP, "UP")

        log.check_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-child;DOWN;check-mk-notify;"
        )


# Test the situation where:
# a) Child goes down
# b) Parent goes down, child becomes unreachable
# c) Child goes up
# d) Parent goes up
def test_down_child_becomes_unreachable_then_up(scenario, site: Site, initial_state):
    with WatchLog(site, scenario.log, default_timeout=scenario.log_timeout) as log:
        # - Set child down, expect DOWN notification
        site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")
        log.check_logged("HOST ALERT: notify-test-child;DOWN;HARD;1;DOWN")

        if scenario.core == "cmc":
            # CMC: Send a new check result for the parent to make the CMC create the host notification
            # for the child
            site.send_host_check_result("notify-test-parent", STATE_UP, "UP")

        log.check_logged(
            "HOST NOTIFICATION: check-mk-notify;notify-test-child;DOWN;check-mk-notify;"
        )

        # - Set parent down, expect DOWN notification for parent and UNREACHABLE notification for child
        site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")
        log.check_logged("HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN")

        # Difference beween nagios/cmc: when sending DOWN via PROCESS_HOST_CHECK_RESULT
        # the nagios core needs another child down check result to report it as unreachable.
        if scenario.core == "cmc":
            log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

            if scenario.unreachable_enabled:
                log.check_logged(
                    "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
                )
            # TODO: Can not test this because it drains too many entries from the log. WatchLog could deal
            # with this by readding the read lines after succeeded test or similar
            # else:
            #    log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")

            log.check_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
            )

        elif scenario.core == "nagios":
            log.check_logged(
                "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;"
            )

            site.send_host_check_result(
                "notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE
            )
            log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

            if scenario.unreachable_enabled:
                log.check_logged(
                    "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;"
                )

        # - Set child up, expect:
        #   cmc: pending UP notification, and sent up notification after next parent check
        #   nagios: UP notification
        _send_child_recovery(scenario, site, log)

        # - Set parent up, expect UP notification
        _send_parent_recovery(scenario, site, log)
