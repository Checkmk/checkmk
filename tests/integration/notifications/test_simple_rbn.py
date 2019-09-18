# pylint: disable=redefined-outer-name

import time
import pytest

from testlib import web, WatchLog  # pylint: disable=unused-import


@pytest.fixture()
def test_config(web, site):
    users = {
        "hh": {
            "alias": "Harry Hirsch",
            "password": "1234",
            "email": u"%s@localhost" % web.site.id,
            'contactgroups': ['all'],
        },
    }

    expected_users = set(["cmkadmin", "automation"] + users.keys())
    web.add_htpasswd_users(users)
    all_users = web.get_all_users()
    assert not expected_users - set(all_users.keys())

    # Notify
    web.add_host("notify-test", attributes={
        "ipaddress": "127.0.0.1",
    })
    web.activate_changes()

    site.live.command("[%d] DISABLE_HOST_CHECK;notify-test" % time.time())

    yield

    web.delete_host("notify-test")
    web.delete_htpasswd_users(users.keys())
    web.activate_changes()


@pytest.mark.parametrize("core,log", [
    ("nagios", "var/log/nagios.log"),
    ("cmc", "var/check_mk/core/history"),
])
def test_simple_rbn_host_notification(test_config, site, core, log):
    site.set_config("CORE", core, with_restart=True)

    # Open the log file and scan to end
    l = WatchLog(site, log)

    # Set object down to trigger a notification
    site.send_host_check_result("notify-test", 1, "FAKE DOWN", expected_state=1)

    # Now check for appearing log lines - one after the other
    # NOTE: "] " is necessary to get the actual log line and not the external command execution
    l.check_logged(
        "] HOST NOTIFICATION: check-mk-notify;notify-test;DOWN;check-mk-notify;FAKE DOWN",
        timeout=20,
    )
    l.check_logged(
        "] HOST NOTIFICATION: hh;notify-test;DOWN;mail;FAKE DOWN",
        timeout=20,
    )
    l.check_logged(
        "] HOST NOTIFICATION RESULT: hh;notify-test;OK;mail;Spooled mail to local mail transmission agent;",
        timeout=20,
    )
