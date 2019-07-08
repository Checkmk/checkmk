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


@pytest.mark.parametrize("core", ["nagios", "cmc"])
def test_simple_rbn_notification(test_config, site, core):
    site.set_config("CORE", core, with_restart=True)

    # Open the log file and scan to end
    l = WatchLog(site, "var/log/notify.log")

    # Set object down to trigger a notification
    site.send_host_check_result("notify-test", 1, "FAKE DOWN", expected_state=1)

    # Now check for appearing log lines - one after the other
    l.check_logged("Got raw notification (notify-test)", timeout=20)
    l.check_logged("notifying hh via mail", timeout=20)
    l.check_logged("Creating spoolfile:", timeout=20)
    l.check_logged("(notify-test) for local delivery", timeout=20)
    l.check_logged("Output: Spooled mail to local mail transmission agent", timeout=20)
