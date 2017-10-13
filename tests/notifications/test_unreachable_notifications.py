#!/usr/bin/env python
# encoding: utf-8

import pytest
import time
from testlib import web

@pytest.fixture(scope="module")
def test_cfg(web, site):
    try:
        print "Applying test config"

        web.add_host("notify-test-parent", attributes={
            "ipaddress": "127.0.0.1",
        })

        web.add_host("notify-test-child", attributes={
            "ipaddress": "127.0.0.1",
            "parents": [ "notify-test-parent" ],
        })

        web.activate_changes()

        site.live.command("[%d] DISABLE_HOST_CHECK;notify-test-parent" % time.time())
        site.live.command("[%d] DISABLE_HOST_CHECK;notify-test-child" % time.time())

        yield None
    finally:
        #
        # Cleanup code
        #
        print "Cleaning up default config"

        web.delete_host("notify-test-child")
        web.delete_host("notify-test-parent")


def set_initial_state(site):
    # Before each test: Set to initial state: Both UP
    site.send_host_check_result("notify-test-child", 0, "UP")
    site.send_host_check_result("notify-test-parent", 0, "UP")

    # Before each test: Clear logs
    site.live.command("[%d] ROTATE_LOGFILE" % time.time())
    time.sleep(1) # TODO: Add check for rotation


def open_history_log(core):
    if core == "cmc":
        return open("var/check_mk/core/history")
    elif core == "nagios":
        return open("var/nagios/nagios.log")
    else:
        raise NotImplementedError()


STATE_UP          = 0
STATE_DOWN        = 1
STATE_UNREACHABLE = 2

@pytest.mark.parametrize(("core"), [ "nagios", "cmc" ])
def test_unreachable_child_down_before_parent_down(test_cfg, site, core):
    site.set_core(core)
    set_initial_state(site)

    # TODO:
    # - Set child down, expect DOWN notification
    site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN")

    assert "HOST ALERT: notify-test-child;DOWN;HARD;1;DOWN" in open_history_log(core).read()

    # - Set parent down, expect DOWN notification for parent and UNREACHABLE notification for child
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")

    # Difference beween nagios/cmc: when sending DOWN via PROCESS_HOST_CHECK_RESULT
    # the nagios core needs another child down check result to report it as unreachable.
    if core == "nagios":
        site.send_host_check_result("notify-test-child", STATE_DOWN, "DOWN", expected_state=STATE_UNREACHABLE)

    history_log = open_history_log(core).read()

    assert "HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN" in history_log
    assert "HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;" in history_log

    if core == "cmc":
        assert "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;" in history_log
        assert "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;" in history_log
    else:
        # TODO: Nagios does not log the entries checked above for cmc. This may be a problem e.g. for availability.
        pass


@pytest.mark.parametrize(("core"), [ "nagios", "cmc" ])
def test_unreachable_child_after_parent_is_down(test_cfg, site, core):
    site.set_core(core)
    set_initial_state(site)


    # TODO:
    # - Set parent down, expect DOWN notification
    site.send_host_check_result("notify-test-parent", STATE_DOWN, "DOWN")

    assert "HOST ALERT: notify-test-parent;DOWN;HARD;1;DOWN" in open_history_log(core).read()

    # - set child down, expect UNREACHABLE notification
    assert site.get_host_state("notify-test-child") == STATE_UP
    site.send_host_check_result("notify-test-ychild", STATE_DOWN, "DOWN")
    assert site.get_host_state("notify-test-child") == STATE_UNREACHABLE

    history_log = open_history_log(core).read()

    assert "HOST ALERT: notify-test-child;DOWN;HARD;1;DOWN" in history_log

    #if core == "cmc":
    #    assert "HOST ALERT: notify-test-child;UNREACHABLE;HARD;1;child becomes unreachable due to state change of parent host" in history_log

    #    assert "HOST NOTIFICATION: check-mk-notify;notify-test-parent;DOWN;check-mk-notify;" in history_log
    #    assert "HOST NOTIFICATION: check-mk-notify;notify-test-child;UNREACHABLE;check-mk-notify;" in history_log
    #else:
    #    # TODO: Nagios does not log the entries checked above for cmc. This may be a problem e.g. for availability.
    #    pass

    # TODO:
    # - Set parent down, expect DOWN notification
    # - Set child up, expect no notification

    # TODO:
    # - Set parent down, expect DOWN notification
    # - set child down, expect UNREACHABLE notification
    # - set child up, expect UP notification
    # - set child down, expect UNREACHABLE notification

    # TODO:
    # - Set parent down, expect DOWN notification
    # - set child down, expect UNREACHABLE notification
    # - Set parent up, expect UP notification and child DOWN notification
    # - Set parent down, expect DOWN notification and UNREACHABLE child notification


#@pytest.mark.parametrize(("core"), [ "nagios", "cmc" ])
#def test_unreachable_disabled_by_default(test_cfg, site, core):
#    # TODO: Set child down, set parent down
#    # TODO: Check log that no UNREACHABLE notification has been created
#    pass
