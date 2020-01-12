# pylint: disable=redefined-outer-name

import time
import os
import pytest  # type: ignore

from testlib import web, WatchLog  # pylint: disable=unused-import


@pytest.fixture()
def fake_sendmail(site):
    site.write_file("local/bin/sendmail", "#!/bin/bash\n"
                    "set -e\n"
                    "echo \"sendmail called with: $@\"\n")
    os.chmod(site.path("local/bin/sendmail"), 0o775)
    yield
    site.delete_file("local/bin/sendmail")


@pytest.fixture(params=[
    ("nagios", "var/log/nagios.log"),
    ("cmc", "var/check_mk/core/history"),
])
def test_log(request, web, site, fake_sendmail):
    core, log = request.param
    site.set_config("CORE", core, with_restart=True)

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

    site.live.command("[%d] STOP_EXECUTING_HOST_CHECKS" % time.time())
    site.live.command("[%d] STOP_EXECUTING_SVC_CHECKS" % time.time())

    web.add_host("notify-test", attributes={
        "ipaddress": "127.0.0.1",
    })
    web.activate_changes()

    with WatchLog(site, log, default_timeout=20) as l:
        yield l

    site.live.command("[%d] START_EXECUTING_HOST_CHECKS" % time.time())
    site.live.command("[%d] START_EXECUTING_SVC_CHECKS" % time.time())

    web.delete_host("notify-test")
    web.delete_htpasswd_users(users.keys())
    web.activate_changes()


def test_simple_rbn_host_notification(test_log, site):
    site.send_host_check_result("notify-test", 1, "FAKE DOWN", expected_state=1)

    # NOTE: "] " is necessary to get the actual log line and not the external command execution
    test_log.check_logged(
        "] HOST NOTIFICATION: check-mk-notify;notify-test;DOWN;check-mk-notify;FAKE DOWN")
    test_log.check_logged("] HOST NOTIFICATION: hh;notify-test;DOWN;mail;FAKE DOWN")
    test_log.check_logged(
        "] HOST NOTIFICATION RESULT: hh;notify-test;OK;mail;Spooled mail to local mail transmission agent;"
    )


def test_simple_rbn_service_notification(test_log, site):
    site.send_service_check_result("notify-test", "PING", 2, "FAKE CRIT")

    # NOTE: "] " is necessary to get the actual log line and not the external command execution
    test_log.check_logged(
        "] SERVICE NOTIFICATION: check-mk-notify;notify-test;PING;CRITICAL;check-mk-notify;FAKE CRIT"
    )
    test_log.check_logged("] SERVICE NOTIFICATION: hh;notify-test;PING;CRITICAL;mail;FAKE CRIT")
    test_log.check_logged(
        "] SERVICE NOTIFICATION RESULT: hh;notify-test;PING;OK;mail;Spooled mail to local mail transmission agent;"
    )
