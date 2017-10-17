#!/usr/bin/env python
# encoding: utf-8

import pytest
import time
import os
import sys
from testlib import web

STATE_UP          = 0
STATE_DOWN        = 1
STATE_UNREACHABLE = 2

class Scenario(object):
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



@pytest.fixture(scope="module", params=[
    Scenario(core="nagios", unreachable_enabled=True),
    Scenario(core="cmc", unreachable_enabled=True),
    Scenario(core="nagios", unreachable_enabled=False),
    Scenario(core="cmc", unreachable_enabled=False),
], ids=Scenario.get_test_id)
def scenario(request, web, site):
    core = request.param.core
    unreachable_enabled = request.param.unreachable_enabled
    site.set_core(core)

    try:
        print "Applying test config"

        web.add_host("notify-test-parent", attributes={
            "ipaddress": "127.0.0.1",
        })

        web.add_host("notify-test-child", attributes={
            "ipaddress": "127.0.0.1",
            "parents": [ "notify-test-parent" ],
        })

        if unreachable_enabled:
            notification_options = 'd,u,r,f,s'
        else:
            notification_options = 'd,r,f,s'

        rule_result = web.get_ruleset("extra_host_conf:notification_options")
        rule_result["ruleset"] = {
            "": [{'conditions': {'host_specs': ['@all'], 'host_tags': []}, 'options': {}, 'value': notification_options}]
        }
        web.set_ruleset("extra_host_conf:notification_options", rule_result)


        web.activate_changes()

        site.live.command("[%d] DISABLE_HOST_CHECK;notify-test-parent" % time.time())
        site.live.command("[%d] DISABLE_HOST_CHECK;notify-test-child" % time.time())
        site.live.command("[%d] DISABLE_FLAP_DETECTION" % time.time())

        #set_initial_state(site, core)

        yield request.param
    finally:
        #
        # Cleanup code
        #
        print "Cleaning up default config"

        site.live.command("[%d] ENABLE_FLAP_DETECTION" % time.time())
        site.live.command("[%d] ENABLE_HOST_CHECK;notify-test-child" % time.time())
        site.live.command("[%d] ENABLE_HOST_CHECK;notify-test-parent" % time.time())

        web.delete_host("notify-test-child")
        web.delete_host("notify-test-parent")


@pytest.fixture(scope="function")
def initial_state(site, scenario):
    # Before each test: Set to initial state: Both UP
    site.send_host_check_result("notify-test-child", 0, "UP")
    site.send_host_check_result("notify-test-parent", 0, "UP")

    # Before each test: Clear logs
    if scenario.core == "cmc":
        site.live.command("[%d] ROTATE_LOGFILE" % time.time())
    else:
        site.delete_file("var/nagios/nagios.log")

    time.sleep(1) # TODO: Add check for rotation


class HistoryLog(object):
    def __init__(self, site, core):
        self._site = site
        self._core = core
        self._log = self._open_log()
        self._buf = []


    def _log_path(self):
        if self._core == "cmc":
            return "var/check_mk/core/history"
        elif self._core == "nagios":
            return "var/nagios/nagios.log"
        else:
            raise NotImplementedError()


    def _open_log(self):
        if not self._site.file_exists(self._log_path()):
            self._site.write_file(self._log_path(), "")

        fobj = open(self._site.path(self._log_path()), "r")
        fobj.seek(0, 2) # go to end of file
        return fobj


    def check_logged(self, match_for, timeout=5):
        if not self._check_for_line(match_for, timeout):
            raise Exception("Did not find %r in %s after %d seconds" %
                                (match_for, self._log_path(), timeout))


    def check_not_logged(self, match_for, timeout=5):
        if self._check_for_line(match_for, timeout):
            raise Exception("Found %r in %s after %d seconds" %
                                (match_for, self._log_path(), timeout))


    def _check_for_line(self, match_for, timeout):
        timeout_at = time.time() + timeout
        while time.time() < timeout_at:
            #print "read till timeout %0.2f sec left" % (timeout_at - time.time())
            line = self._log.readline()
            sys.stdout.write(line)
            if match_for in line:
                return True
            time.sleep(0.1)

        return False


# Test the situation where:
# a) Child goes down
# b) Parent goes down
# c) child becomes unreachable
def test_unreachable_child_down_before_parent_down(scenario, site, initial_state):
    log = HistoryLog(site, scenario.core)

    # - Set child down, expect DOWN notification
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")

    log.check_logged("HOST ALERT: notify-test-child;DOWN;HARD;1;DOWN")

    # - Set parent down, expect DOWN notification for parent and UNREACHABLE notification for child
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")

    log.check_logged("HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN")

    # This is checked later for nagios
    if scenario.core == "cmc":
        log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;")

    # Difference beween nagios/cmc: when sending DOWN via PROCESS_HOST_CHECK_RESULT
    # the nagios core needs another child down check result to report it as unreachable.
    if scenario.core == "nagios":
        site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE)
        log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

    if scenario.unreachable_enabled:
        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")
    else:
        log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")


# Test the situation where:
# a) Parent goes down
# b) Child goes down, becomes unreachable
def test_unreachable_child_after_parent_is_down(scenario, site, initial_state):
    log = HistoryLog(site, scenario.core)

    # - Set parent down, expect DOWN notification
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")

    log.check_logged("HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;")

    # - set child down, expect UNREACHABLE notification
    assert site.get_host_state("notify-test-child") == STATE_UP
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE)

    log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

    if scenario.unreachable_enabled:
        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")
    else:
        log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")


# Test the situation where:
# a) Child goes down
# b) Parent goes down
# c) Child goes up while parent is down
def test_parent_down_child_up_on_up_result(scenario, site, initial_state):
    log = HistoryLog(site, scenario.core)

    # - Set child down, expect DOWN notification
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")
    log.check_logged("HOST ALERT: notify-test-child;DOWN;HARD;1;DOWN")

    # - Set parent down, expect DOWN notification
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")

    log.check_logged("HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;")

    # - Set child up, expect UP notification
    site.send_host_check_result("notify-test-child", STATE_UP, "UP")

    log.check_logged("HOST ALERT: notify-test-child;UP;HARD;1;")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UP")


# Test the situation where:
# a) Parent goes down
# b) Child goes down and becomes unreachable
# c) Child goes up while parent is down
# d) Child goes down and becomes unreachable while parent is down
def test_parent_down_child_state_changes(scenario, site, initial_state):
    log = HistoryLog(site, scenario.core)

    # - Set parent down, expect DOWN notification
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")

    log.check_logged("HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;")

    # - set child down, expect UNREACHABLE notification
    assert site.get_host_state("notify-test-child") == STATE_UP
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE)

    log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")
    if scenario.unreachable_enabled:
        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")
    else:
        log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")

    # - set child up, expect UP notification
    site.send_host_check_result("notify-test-child", STATE_UP, "UP")

    log.check_logged("HOST ALERT: notify-test-child;UP;HARD;1;")

    if scenario.core == "cmc" or scenario.unreachable_enabled:
        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;")

    # - set child down, expect UNREACHABLE notification
    assert site.get_host_state("notify-test-child") == STATE_UP
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE)

    log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")
    if scenario.unreachable_enabled:
        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")
    else:
        log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")


# Test the situation where:
# a) Parent goes down
# b) Child goes down and becomes unreachable
# c) Parent goes up
# d) Child is still down and becomes down
def test_child_down_after_parent_recovers(scenario, site, initial_state):
    log = HistoryLog(site, scenario.core)

    # - Set parent down, expect DOWN notification
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")

    log.check_logged("HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;")

    # - set child down, expect UNREACHABLE notification
    assert site.get_host_state("notify-test-child") == STATE_UP
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE)

    log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")
    if scenario.unreachable_enabled:
        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")
    else:
        log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")

    # - Set parent up, expect UP notification
    site.send_host_check_result("notify-test-parent", STATE_UP, "UP")
    log.check_logged("HOST ALERT: notify-test-parent;UP;HARD;1;")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;UP")

    # - Next child check DOWN, expect no notification (till next parent check confirms UP)
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")
    log.check_logged("HOST ALERT: notify-test-child;DOWN;HARD;1;")

    if scenario.core == "cmc":
        # - Set parent UP (again), expect DOWN notification for child
        site.send_host_check_result("notify-test-parent", STATE_UP, "UP")

        # Seems the child notification is not processed immediately (TODO check this)
        #time.sleep(1)

    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;DOWN;check-mk-notify;")


# Test the situation where:
# a) Parent goes down
# b) Child goes down and becomes unreachable
# c) Parent goes up
# d) Child goes up
def test_child_up_after_parent_recovers(scenario, site, initial_state):
    log = HistoryLog(site, scenario.core)

    # - Set parent down, expect DOWN notification
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")

    log.check_logged("HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;")

    # - set child down, expect UNREACHABLE notification
    assert site.get_host_state("notify-test-child") == STATE_UP
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE)

    log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")
    if scenario.unreachable_enabled:
        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")
    else:
        log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")

    # - Set parent up, expect UP notification
    site.send_host_check_result("notify-test-parent", STATE_UP, "UP")
    log.check_logged("HOST ALERT: notify-test-parent;UP;HARD;1;")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;UP")

    # - Next service check UP, expect no notification (till next parent check confirms UP)
    site.send_host_check_result("notify-test-child", STATE_UP, "UP")
    log.check_logged("HOST ALERT: notify-test-child;UP;HARD;1;")

    # - Set parent UP, expect UP notification for child
    site.send_host_check_result("notify-test-parent", STATE_UP, "UP")

    if scenario.unreachable_enabled:
        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UP;check-mk-notify;")
    else:
        log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UP;check-mk-notify;")


# Test the situation where:
# a) Child goes down
# b) Parent goes down, child becomes unreachable
# d) Parent goes up, child becomes down
def test_down_child_becomes_unreachable_and_down_again(scenario, site, initial_state):
    log = HistoryLog(site, scenario.core)

    # - Set child down, expect DOWN notification
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")
    log.check_logged("HOST ALERT: notify-test-child;DOWN;HARD;1;DOWN")

    if scenario.core == "cmc":
        # CMC: Send a new check result for the parent to make the CMC create the host notification
        # for the child
        site.send_host_check_result("notify-test-parent", STATE_UP, "UP")

    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;DOWN;check-mk-notify;")

    # - Set parent down, expect DOWN notification for parent and UNREACHABLE notification for child
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")
    log.check_logged("HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN")

    # Difference beween nagios/cmc: when sending DOWN via PROCESS_HOST_CHECK_RESULT
    # the nagios core needs another child down check result to report it as unreachable.
    if scenario.core == "cmc":
        log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

        if scenario.unreachable_enabled:
            log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")
        # TODO: Can not test this because it drains too many entries from the log. HistoryLog could deal
        # with this by readding the read lines after succeeded test or similar
        #else:
        #    log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")

        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;")

    elif scenario.core == "nagios":
        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;")

        site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE)
        log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

        if scenario.unreachable_enabled:
            log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")

    # - Set parent up, expect UP notification
    site.send_host_check_result("notify-test-parent", STATE_UP, "UP")
    log.check_logged("HOST ALERT: notify-test-parent;UP;HARD;1;")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;UP")

    # - Next child check DOWN
    #   cmc: expect no notification (till next parent check confirms UP)
    #   nagios: expect notification without 
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")
    log.check_logged("HOST ALERT: notify-test-child;DOWN;HARD;1;")

    if scenario.core == "cmc":
        # - Set parent UP (again), expect DOWN notification for child
        site.send_host_check_result("notify-test-parent", STATE_UP, "UP")

    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;DOWN;check-mk-notify;")


# Test the situation where:
# a) Child goes down
# b) Parent goes down, child becomes unreachable
# c) Child goes up
def test_down_child_becomes_unreachable_then_up(scenario, site, initial_state):
    log = HistoryLog(site, scenario.core)

    # - Set child down, expect DOWN notification
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")
    log.check_logged("HOST ALERT: notify-test-child;DOWN;HARD;1;DOWN")

    if scenario.core == "cmc":
        # CMC: Send a new check result for the parent to make the CMC create the host notification
        # for the child
        site.send_host_check_result("notify-test-parent", STATE_UP, "UP")

    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;DOWN;check-mk-notify;")

    # - Set parent down, expect DOWN notification for parent and UNREACHABLE notification for child
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")
    log.check_logged("HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN")

    # Difference beween nagios/cmc: when sending DOWN via PROCESS_HOST_CHECK_RESULT
    # the nagios core needs another child down check result to report it as unreachable.
    if scenario.core == "cmc":
        log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

        if scenario.unreachable_enabled:
            log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")
        # TODO: Can not test this because it drains too many entries from the log. HistoryLog could deal
        # with this by readding the read lines after succeeded test or similar
        #else:
        #    log.check_not_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")

        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;")

    elif scenario.core == "nagios":
        log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;")

        site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE)
        log.check_logged("HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;")

        if scenario.unreachable_enabled:
            log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;")

    # - Set child up, expect:
    #   cmc: pending UP notification, and sent up notification after next parent check
    #   nagios: UP notification
    site.send_host_check_result("notify-test-child", STATE_UP, "UP")
    log.check_logged("HOST ALERT: notify-test-child;UP;HARD;1;")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-child;UP")

    ## - Set parent up, expect UP notification
    site.send_host_check_result("notify-test-parent", STATE_UP, "UP")
    log.check_logged("HOST ALERT: notify-test-parent;UP;HARD;1;")
    log.check_logged("HOST NOTIFICATION: check-mk-notify;notify-test-parent;UP")
