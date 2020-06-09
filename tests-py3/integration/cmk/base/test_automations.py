#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
# flake8: noqa

import re
import os
import ast
import subprocess
import freezegun  # type: ignore[import]
import pytest  # type: ignore[import]

from testlib.fixtures import web  # pylint: disable=unused-import
from testlib.utils import get_standard_linux_agent_output

import cmk.utils.paths

import cmk.base.autochecks as autochecks
import cmk.base.config as config


@pytest.fixture(scope="module")
def test_cfg(web, site):
    print("Applying default config")
    web.add_host("modes-test-host", attributes={
        "ipaddress": "127.0.0.1",
    })
    web.add_host("modes-test-host2",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "tag_criticality": "test",
                 })
    web.add_host("modes-test-host3",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "tag_criticality": "test",
                 })
    web.add_host("modes-test-host4",
                 attributes={
                     "ipaddress": "127.0.0.1",
                     "tag_criticality": "offline",
                 })

    site.write_file(
        "etc/check_mk/conf.d/modes-test-host.mk",
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ALL_HOSTS))\n")

    site.makedirs("var/check_mk/agent_output/")
    site.write_file("var/check_mk/agent_output/modes-test-host", get_standard_linux_agent_output())
    site.write_file("var/check_mk/agent_output/modes-test-host2", get_standard_linux_agent_output())
    site.write_file("var/check_mk/agent_output/modes-test-host3", get_standard_linux_agent_output())

    web.discover_services("modes-test-host")
    web.discover_services("modes-test-host2")
    web.discover_services("modes-test-host3")

    web.activate_changes()
    yield None

    #
    # Cleanup code
    #
    print("Cleaning up test config")

    site.delete_dir("var/check_mk/agent_output")

    site.delete_file("etc/check_mk/conf.d/modes-test-host.mk")

    web.delete_host("modes-test-host")
    web.delete_host("modes-test-host2")
    web.delete_host("modes-test-host3")
    web.delete_host("modes-test-host4")


#.
#   .--Autom.calls---------------------------------------------------------.
#   |            _         _                             _ _               |
#   |           / \  _   _| |_ ___  _ __ ___    ___ __ _| | |___           |
#   |          / _ \| | | | __/ _ \| '_ ` _ \  / __/ _` | | / __|          |
#   |         / ___ \ |_| | || (_) | | | | | || (_| (_| | | \__ \          |
#   |        /_/   \_\__,_|\__\___/|_| |_| |_(_)___\__,_|_|_|___/          |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Test the command line automation calls                               |
#   '----------------------------------------------------------------------'


def _execute_automation(site,
                        cmd,
                        args=None,
                        stdin=None,
                        expect_stdout=None,
                        expect_stderr="",
                        expect_stderr_pattern="",
                        expect_exit_code=0,
                        parse_data=True):
    cmdline = ["cmk", "--automation", cmd] + ([] if args is None else args)
    print(cmdline)
    p = site.execute(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

    stdout, stderr = p.communicate(stdin)

    assert p.wait() == expect_exit_code, "Output: %r, Error: %r" % (stdout, stderr)

    if expect_stderr_pattern:
        assert re.match(expect_stderr_pattern, stderr) is not None
    else:
        assert stderr == expect_stderr

    if expect_stdout is not None:
        assert stdout == expect_stdout

    if parse_data:
        data = ast.literal_eval(stdout)
        return data


def test_automation_discovery_no_host(test_cfg, site):
    # NOTE: We can't use @raiseerrors here, because this would redirect stderr to /dev/null!
    p = site.execute(["cmk", "--automation", "inventory", "@scan", "new"],
                     stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE)

    stdout, stderr = p.communicate()
    assert "Need two arguments:" in stderr
    assert stdout == ""
    assert p.wait() == 1


def test_automation_discovery_single_host(test_cfg, site):
    data = _execute_automation(site, "inventory", args=["@raiseerrors", "new", "modes-test-host"])

    assert isinstance(data, tuple)
    assert len(data) == 2

    assert len(data[0]) == 1
    assert "modes-test-host" in data[0]
    assert len(data[0]["modes-test-host"]) == 6

    assert data[1] == {}


def test_automation_discovery_multiple_hosts(test_cfg, site):
    data = _execute_automation(site,
                               "inventory",
                               args=["@raiseerrors", "new", "modes-test-host", "modes-test-host2"])

    assert isinstance(data, tuple)
    assert len(data) == 2

    assert len(data[0]) == 2
    assert "modes-test-host" in data[0]
    assert "modes-test-host2" in data[0]
    assert len(data[0]["modes-test-host"]) == 6
    assert len(data[0]["modes-test-host2"]) == 6

    assert data[1] == {}


def test_automation_discovery_not_existing_host(test_cfg, site):
    data = _execute_automation(site, "inventory", args=["@raiseerrors", "new", "xxxhost"])

    assert isinstance(data, tuple)
    assert len(data) == 2

    assert data[0]["xxxhost"] == [0, 0, 0, 0, 0, 0]
    assert data[1] == {"xxxhost": ''}


def test_automation_discovery_with_cache_option(test_cfg, site):
    data = _execute_automation(site, "inventory", args=["@cache", "new", "modes-test-host"])

    assert isinstance(data, tuple)
    assert len(data) == 2

    assert len(data[0]) == 1
    assert "modes-test-host" in data[0]
    assert len(data[0]["modes-test-host"]) == 6

    assert data[1] == {}


def test_automation_analyse_service_autocheck(test_cfg, site):
    data = _execute_automation(site, "analyse-service", args=["modes-test-host", "CPU load"])

    assert data["origin"] == "auto"
    assert data["checktype"] == "cpu.loads"
    assert data["item"] is None
    assert data["checkgroup"] == "cpu_load"


def test_automation_analyse_service_no_check(test_cfg, site):
    data = _execute_automation(site, "analyse-service", args=["modes-test-host", "XXX CPU load"])
    assert data == {}


def test_automation_try_discovery_not_existing_host(test_cfg, site):
    _execute_automation(
        site,
        "try-inventory",
        args=["xxx-not-existing-host"],
        expect_stderr_pattern=(r"Failed to lookup IPv4 address of xxx-not-existing-host "
                               r"via DNS: (\[Errno -2\] Name or service not known"
                               r"|\[Errno -3\] Temporary failure in name resolution)\n"),
        expect_stdout="",
        expect_exit_code=2,
        parse_data=False,
    )


def test_automation_try_discovery_host(test_cfg, site):

    with freezegun.freeze_time("2020-06-01"):
        data = _execute_automation(site, "try-inventory", args=["modes-test-host"])
    assert isinstance(data, dict)
    assert isinstance(data["output"], str)
    assert isinstance(data["check_table"], list)

    # The following has been nailed down during major refactoring in cmk/base/discovery.py.
    # remove it afterwards, as this is probably going to be annoying.

    # Drop last row (Uptime) and ignore metrics (both are time sensitive)
    # Also ignore labels for readability.
    check_table = sorted(row[:-2] for row in data["check_table"][:-1])

    assert check_table == [
        ('old', 'apache_status', 'apache_status', '127.0.0.1:5000', '{}', {},
         'Apache 127.0.0.1:5000 Status', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'apache_status', 'apache_status', '127.0.0.1:5004', '{}', {},
         'Apache 127.0.0.1:5004 Status', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'apache_status', 'apache_status', '127.0.0.1:5007', '{}', {},
         'Apache 127.0.0.1:5007 Status', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'apache_status', 'apache_status', '127.0.0.1:5008', '{}', {},
         'Apache 127.0.0.1:5008 Status', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'apache_status', 'apache_status', '127.0.0.1:5009', '{}', {},
         'Apache 127.0.0.1:5009 Status', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'apache_status', 'apache_status', '::1:80', '{}', {}, 'Apache ::1:80 Status', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'check_mk.agent_update', 'agent_update', None, '{}', {}, 'Check_MK Agent', 1,
         "Error: Check_MK Site on deployment server not started(!), Last update check: 2017-01-01 11:01:06 (warn at 2 d)(!), Last agent update: 2017-01-01 11:01:07"
        ),
        ('old', 'cpu.loads', 'cpu_load', None, 'cpuload_default_levels', (5.0, 10.0), 'CPU load', 0,
         "15 min load: 0.48 at 8 Cores (0.06 per Core)"),
        ('old', 'cpu.threads', 'threads', None, '{}', {
            'levels': (2000, 4000)
        }, 'Number of threads', 0, "Count: 969 threads"),
        ('old', 'df', 'filesystem', '/', "{'include_volume_name': False}", {
            'include_volume_name': False,
            'inodes_levels': (10.0, 5.0),
            'levels': (80.0, 90.0),
            'levels_low': (50.0, 60.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24
        }, 'Filesystem /', 2, '98.48% used (210.35 of 213.60 GB), (warn/crit at 80.0%/90.0%)(!!)'),
        ('old', 'df', 'filesystem', '/boot', "{'include_volume_name': False}", {
            'include_volume_name': False,
            'inodes_levels': (10.0, 5.0),
            'levels': (80.0, 90.0),
            'levels_low': (50.0, 60.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24
        }, 'Filesystem /boot', 1,
         '86.35% used (204.05 of 236.29 MB), (warn/crit at 80.0%/90.0%)(!)'),
        ('old', 'df', 'filesystem', '/boot/efi', "{'include_volume_name': False}", {
            'include_volume_name': False,
            'inodes_levels': (10.0, 5.0),
            'levels': (80.0, 90.0),
            'levels_low': (50.0, 60.0),
            'magic_normsize': 20,
            'show_inodes': 'onlow',
            'show_levels': 'onmagic',
            'show_reserved': False,
            'trend_perfdata': True,
            'trend_range': 24
        }, 'Filesystem /boot/efi', 0, '0.7% used (3.58 of 510.98 MB)'),
        ('old', 'kernel.performance', 'kernel_performance', None, '{}', {}, 'Kernel Performance', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'kernel.util', 'cpu_iowait', None, '{}', {}, 'CPU utilization', 0,
         'User: 6.32%, System: 0.93%, Wait: 0.1%, Total CPU: 7.34%'),
        ('old', 'lnx_thermal', 'temperature', 'Zone 0', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 0', 0, '32.4 °C'),
        ('old', 'lnx_thermal', 'temperature', 'Zone 1', '{}', {
            'device_levels_handling': 'devdefault',
            'levels': (70.0, 80.0)
        }, 'Temperature Zone 1', 0, '50.0 °C'),
        ('old', 'mem.linux', 'memory_linux', None, '{}', {
            'levels_commitlimit': ('perc_free', (20.0, 10.0)),
            'levels_committed': ('perc_used', (100.0, 150.0)),
            'levels_hardwarecorrupted': ('abs_used', (1, 1)),
            'levels_pagetables': ('perc_used', (8.0, 16.0)),
            'levels_shm': ('perc_used', (20.0, 30.0)),
            'levels_total': ('perc_used', (120.0, 150.0)),
            'levels_virtual': ('perc_used', (80.0, 90.0)),
            'levels_vmalloc': ('abs_free', (52428800, 31457280))
        }, 'Memory', 0,
         "Total virtual memory: 14.05% - 4.42 GB of 31.43 GB, RAM: 28.4% - 4.42 GB of 15.55 GB, Swap: 0% - 0.00 B of 15.88 GB"
        ),
        ('old', 'mkeventd_status', None, 'heute', '{}', {}, 'OMD heute Event Console', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'mkeventd_status', None, 'test1', '{}', {}, 'OMD test1 Event Console', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'mkeventd_status', None, 'test2', '{}', {}, 'OMD test2 Event Console', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'mkeventd_status', None, 'test3', '{}', {}, 'OMD test3 Event Console', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'mkeventd_status', None, 'test_crawl', '{}', {}, 'OMD test_crawl Event Console', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'mknotifyd', None, 'heute', '{}', {}, 'OMD heute Notification Spooler', 2,
         'Version: 1.4.0i4, Status last updated 3.4 y ago, spooler seems crashed or busy(!!)'),
        ('old', 'mknotifyd', None, 'heute_slave_1', '{}', {},
         'OMD heute_slave_1 Notification Spooler', 2,
         'Version: 2016.12.23, Status last updated 3.4 y ago, spooler seems crashed or busy(!!)'),
        ('old', 'mknotifyd', None, 'test1', '{}', {}, 'OMD test1 Notification Spooler', 2,
         'Version: 1.4.0i3, Status last updated 3.4 y ago, spooler seems crashed or busy(!!)'),
        ('old', 'mknotifyd', None, 'test2', '{}', {}, 'OMD test2 Notification Spooler', 2,
         'Version: 1.4.0i3, Status last updated 3.4 y ago, spooler seems crashed or busy(!!)'),
        ('old', 'mknotifyd', None, 'test3', '{}', {}, 'OMD test3 Notification Spooler', 2,
         'Version: 1.4.0i3, Status last updated 3.4 y ago, spooler seems crashed or busy(!!)'),
        ('old', 'mknotifyd', None, 'test_crawl', '{}', {}, 'OMD test_crawl Notification Spooler', 2,
         'Version: 2016.12.21, Status last updated 3.4 y ago, spooler seems crashed or busy(!!)'),
        ('old', 'mounts', 'fs_mount_options', '/',
         "['data=ordered', 'errors=remount-ro', 'noatime', 'nodiratime', 'rw']",
         ['data=ordered', 'errors=remount-ro', 'noatime', 'nodiratime',
          'rw'], 'Mount options of /', 0, 'Mount options exactly as expected'),
        ('old', 'mounts', 'fs_mount_options', '/boot',
         "['acl', 'barrier', 'block_validity', 'relatime', 'rw', 'stripe=4', 'user_xattr']",
         ['acl', 'barrier', 'block_validity', 'relatime', 'rw', 'stripe=4',
          'user_xattr'], 'Mount options of /boot', 0, 'Mount options exactly as expected'),
        ('old', 'mounts', 'fs_mount_options', '/boot/efi',
         "['codepage=437', 'dmask=0077', 'errors=remount-ro', 'fmask=0077', 'iocharset=iso8859-1', 'relatime', 'rw', 'shortname=mixed']",
         [
             'codepage=437', 'dmask=0077', 'errors=remount-ro', 'fmask=0077', 'iocharset=iso8859-1',
             'relatime', 'rw', 'shortname=mixed'
         ], 'Mount options of /boot/efi', 0, 'Mount options exactly as expected'),
        ('old', 'ntp.time', 'ntp_time', None, '{}', {
            'alert_delay': (300, 3600),
            'ntp_levels': (10, 200.0, 500.0)
        }, 'NTP Time', 0,
         'sys.peer - stratum 2, offset -0.84 ms, jitter 20.87 ms, last reached 62 secs ago (synchronized on 176.9.31.215)'
        ),
        ('old', 'omd_apache', None, 'aq', 'None', None, 'OMD aq apache', 0,
         'No activity since last check'),
        ('old', 'omd_apache', None, 'heute', 'None', None, 'OMD heute apache', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'omd_apache', None, 'heute_slave_1', 'None', None, 'OMD heute_slave_1 apache', 0,
         'No activity since last check'),
        ('old', 'omd_apache', None, 'onelogin', 'None', None, 'OMD onelogin apache', 0,
         'No activity since last check'),
        ('old', 'omd_apache', None, 'stable', 'None', None, 'OMD stable apache', 0,
         'No activity since last check'),
        ('old', 'omd_apache', None, 'stable_slave_1', 'None', None, 'OMD stable_slave_1 apache', 0,
         'No activity since last check'),
        ('old', 'omd_apache', None, 'test1', 'None', None, 'OMD test1 apache', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'omd_apache', None, 'test2', 'None', None, 'OMD test2 apache', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'omd_apache', None, 'test3', 'None', None, 'OMD test3 apache', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'omd_apache', None, 'test_crawl', 'None', None, 'OMD test_crawl apache', 0,
         'WAITING - Counter based check, cannot be done offline'),
        ('old', 'postfix_mailq', 'mail_queue_length', '', '{}', {
            'active': (200, 300),
            'deferred': (10, 20)
        }, 'Postfix Queue', 0, 'Deferred queue length: 0, Active queue length: 0'),
        ('old', 'postfix_mailq_status', None, '', 'None', None, 'Postfix status', 0,
         'Status: the Postfix mail system is running, PID: 2051'),
        ('old', 'tcp_conn_stats', 'tcp_conn_stats', None, 'tcp_conn_stats_default_levels', {},
         'TCP Connections', 0,
         'CLOSE_WAIT: 7, ESTABLISHED: 3, FIN_WAIT2: 1, LISTEN: 38, TIME_WAIT: 14'),
    ]


def test_automation_set_autochecks(test_cfg, site):
    new_items = {
        ("df", "xxx"): ("'bla'", {
            u"xyz": u"123"
        }),
        ("uptime", None): (None, {}),
    }

    try:
        data = _execute_automation(site,
                                   "set-autochecks",
                                   args=["blablahost"],
                                   stdin=repr(new_items))
        assert data is None

        autochecks_file = "%s/%s.mk" % (cmk.utils.paths.autochecks_dir, "blablahost")
        assert os.path.exists(autochecks_file)

        data = autochecks.parse_autochecks_file("blablahost", config.service_description)
        services = [((s.check_plugin_name, s.item), s.parameters_unresolved,
                     s.service_labels.to_dict()) for s in data]
        assert sorted(services) == [
            (('df', u'xxx'), "'bla'", {
                u"xyz": u"123"
            }),
            (('uptime', None), 'None', {}),
        ]

        assert site.file_exists("var/check_mk/autochecks/blablahost.mk")
    finally:
        if site.file_exists("var/check_mk/autochecks/blablahost.mk"):
            site.delete_file("var/check_mk/autochecks/blablahost.mk")


def test_automation_update_dns_cache(test_cfg, site, web):
    cache_path = 'var/check_mk/ipaddresses.cache'

    if site.file_exists(cache_path):
        site.delete_file(cache_path)

    try:
        web.add_host("update-dns-cache-host")
        web.add_host("localhost")

        site.write_file(cache_path, "{('bla', 4): '127.0.0.1'}")

        data = _execute_automation(site, "update-dns-cache")
        assert isinstance(data, tuple)
        assert len(data) == 2

        assert data[0] > 0
        assert data[1] == ["update-dns-cache-host"]

        assert site.file_exists(cache_path)

        cache = eval(site.read_file(cache_path))
        assert isinstance(cache, dict)
        assert cache[("localhost", 4)] == "127.0.0.1"
        assert ("bla", 4) not in cache

    finally:
        web.delete_host("localhost")
        web.delete_host("update-dns-cache-host")


# TODO: Test with the different cores
def test_automation_reload(test_cfg, site):
    data = _execute_automation(site, "reload")
    assert data == []


# TODO: Test with the different cores
def test_automation_restart(test_cfg, site):
    data = _execute_automation(site, "restart")
    assert data == []


def test_automation_get_check_information(test_cfg, site):
    data = _execute_automation(site, "get-check-information")
    assert isinstance(data, dict)
    assert len(data) > 1000

    for _check_type, info in data.items():
        assert isinstance(info["title"], str)
        assert "service_description" in info
        assert "snmp" in info


def test_automation_get_real_time_checks(test_cfg, site):
    data = _execute_automation(site, "get-real-time-checks")
    assert isinstance(data, list)
    assert len(data) > 5

    for check_type, title in data:
        assert isinstance(check_type, str)
        assert isinstance(title, str)


def test_automation_get_check_manpage(test_cfg, site):
    data = _execute_automation(site, "get-check-manpage", args=["uptime"])
    assert isinstance(data, dict)
    assert data["type"] == "check_mk"

    for key in ["snmp_info", "has_perfdata", "service_description", "group", "header"]:
        assert key in data

    assert "description" in data["header"]
    assert "title" in data["header"]
    assert "agents" in data["header"]
    assert "license" in data["header"]
    assert "distribution" in data["header"]


def test_automation_notification_replay(test_cfg, site):
    site.write_file(
        "var/check_mk/notify/backlog.mk",
        "[{'SERVICEACKCOMMENT': '', 'SERVICE_EC_CONTACT': '', 'PREVIOUSSERVICEHARDSTATEID': '0', 'HOST_ADDRESS_6': '', 'NOTIFICATIONAUTHORNAME': '', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LONGSERVICEOUTPUT': '', 'LASTHOSTPROBLEMID': '0', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'SERVICEDOWNTIME': '0', 'LASTSERVICESTATE': 'OK', 'SERVICEDESC': 'Temperature Zone 0', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICENOTES': '', 'HOSTPERFDATA': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'LASTHOSTSTATEID': '0', 'SERVICENOTESURL': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTSERVICESTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTDOWNTIME': '0', 'SERVICECHECKCOMMAND': 'check_mk-lnx_thermal', 'SERVICEPROBLEMID': '138', 'HOST_SL': '', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'SERVICESTATE': 'WARNING', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': 'temp=75;70;80;;', 'NOTIFICATIONAUTHORALIAS': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'MICROTIME': '1502452826145843', 'SERVICEOUTPUT': 'WARN - 75.0 \xc2\xb0C (warn/crit at 70/80 \xc2\xb0C)', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICECONTACTGROUPNAMES': 'all', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '138', 'HOST_FILENAME': '/wato/hosts.mk', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'CONTACTS': '', 'SERVICEDISPLAYNAME': 'Temperature Zone 0', 'HOSTNAME': 'localhost', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'NOTIFICATIONTYPE': 'PROBLEM', 'SVC_SL': '', 'SERVICESTATEID': '1', 'LASTHOSTSTATE': 'PENDING', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'HOSTADDRESS': '127.0.0.1', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}, {'SERVICEACKCOMMENT': '', 'HOSTPERFDATA': '', 'SERVICEDOWNTIME': '0', 'PREVIOUSSERVICEHARDSTATEID': '0', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'LASTSERVICESTATE': 'OK', 'LONGSERVICEOUTPUT': '', 'NOTIFICATIONTYPE': 'PROBLEM', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'HOSTNAME': 'localhost', 'NOTIFICATIONAUTHORNAME': '', 'SERVICEDESC': 'Check_MK Agent', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICECONTACTGROUPNAMES': 'all', 'SERVICE_EC_CONTACT': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'MICROTIME': '1502452826145283', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTHOSTSTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTADDRESS': '127.0.0.1', 'SERVICEPROBLEMID': '137', 'HOST_SL': '', 'LASTSERVICESTATEID': '0', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'HOST_ADDRESS_6': '', 'SERVICEOUTPUT': 'WARN - error: This host is not registered for deployment(!), last update check: 2017-05-22 10:28:43 (warn at 2 days)(!), last agent update: 2017-05-22 09:28:24', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICENOTES': '', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '137', 'HOST_FILENAME': '/wato/hosts.mk', 'LASTHOSTSTATE': 'PENDING', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'SERVICECHECKCOMMAND': 'check_mk-check_mk.agent_update', 'SERVICEDISPLAYNAME': 'Check_MK Agent', 'CONTACTS': '', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LASTHOSTPROBLEMID': '0', 'SVC_SL': '', 'SERVICESTATEID': '1', 'SERVICESTATE': 'WARNING', 'NOTIFICATIONAUTHORALIAS': '', 'SERVICENOTESURL': '', 'HOSTDOWNTIME': '0', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}]"
    )

    data = _execute_automation(site, "notification-replay", args=["0"])
    assert data is None


def test_automation_notification_analyse(test_cfg, site):
    site.write_file(
        "var/check_mk/notify/backlog.mk",
        "[{'SERVICEACKCOMMENT': '', 'SERVICE_EC_CONTACT': '', 'PREVIOUSSERVICEHARDSTATEID': '0', 'HOST_ADDRESS_6': '', 'NOTIFICATIONAUTHORNAME': '', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LONGSERVICEOUTPUT': '', 'LASTHOSTPROBLEMID': '0', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'SERVICEDOWNTIME': '0', 'LASTSERVICESTATE': 'OK', 'SERVICEDESC': 'Temperature Zone 0', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICENOTES': '', 'HOSTPERFDATA': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'LASTHOSTSTATEID': '0', 'SERVICENOTESURL': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTSERVICESTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTDOWNTIME': '0', 'SERVICECHECKCOMMAND': 'check_mk-lnx_thermal', 'SERVICEPROBLEMID': '138', 'HOST_SL': '', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'SERVICESTATE': 'WARNING', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': 'temp=75;70;80;;', 'NOTIFICATIONAUTHORALIAS': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'MICROTIME': '1502452826145843', 'SERVICEOUTPUT': 'WARN - 75.0 \xc2\xb0C (warn/crit at 70/80 \xc2\xb0C)', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICECONTACTGROUPNAMES': 'all', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '138', 'HOST_FILENAME': '/wato/hosts.mk', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'CONTACTS': '', 'SERVICEDISPLAYNAME': 'Temperature Zone 0', 'HOSTNAME': 'localhost', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'NOTIFICATIONTYPE': 'PROBLEM', 'SVC_SL': '', 'SERVICESTATEID': '1', 'LASTHOSTSTATE': 'PENDING', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'HOSTADDRESS': '127.0.0.1', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}, {'SERVICEACKCOMMENT': '', 'HOSTPERFDATA': '', 'SERVICEDOWNTIME': '0', 'PREVIOUSSERVICEHARDSTATEID': '0', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'LASTSERVICESTATE': 'OK', 'LONGSERVICEOUTPUT': '', 'NOTIFICATIONTYPE': 'PROBLEM', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'HOSTNAME': 'localhost', 'NOTIFICATIONAUTHORNAME': '', 'SERVICEDESC': 'Check_MK Agent', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICECONTACTGROUPNAMES': 'all', 'SERVICE_EC_CONTACT': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'MICROTIME': '1502452826145283', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTHOSTSTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTADDRESS': '127.0.0.1', 'SERVICEPROBLEMID': '137', 'HOST_SL': '', 'LASTSERVICESTATEID': '0', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'HOST_ADDRESS_6': '', 'SERVICEOUTPUT': 'WARN - error: This host is not registered for deployment(!), last update check: 2017-05-22 10:28:43 (warn at 2 days)(!), last agent update: 2017-05-22 09:28:24', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICENOTES': '', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '137', 'HOST_FILENAME': '/wato/hosts.mk', 'LASTHOSTSTATE': 'PENDING', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'SERVICECHECKCOMMAND': 'check_mk-check_mk.agent_update', 'SERVICEDISPLAYNAME': 'Check_MK Agent', 'CONTACTS': '', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LASTHOSTPROBLEMID': '0', 'SVC_SL': '', 'SERVICESTATEID': '1', 'SERVICESTATE': 'WARNING', 'NOTIFICATIONAUTHORALIAS': '', 'SERVICENOTESURL': '', 'HOSTDOWNTIME': '0', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}]"
    )

    data = _execute_automation(site, "notification-analyse", args=["0"])
    assert isinstance(data, tuple)


def test_automation_notification_get_bulks(test_cfg, site):
    data = _execute_automation(site, "notification-get-bulks", args=["0"])
    assert data == []


def test_automation_get_agent_output(test_cfg, site):
    data = _execute_automation(site, "get-agent-output", args=["modes-test-host", "agent"])
    assert isinstance(data, tuple)
    assert len(data) == 3

    assert data[1] == ""
    assert isinstance(data[2], bytes)
    assert b"<<<uptime>>>" in data[2]
    assert data[0] is True


def test_automation_get_agent_output_unknown_host(test_cfg, site):
    data = _execute_automation(site, "get-agent-output", args=["xxxhost", "agent"])
    assert isinstance(data, tuple)
    assert len(data) == 3

    assert data[1].startswith("Failed to fetch data from ")
    assert data[2] == b""
    assert data[0] is False


# TODO: active-check: Add test for real active_checks check
# TODO: active-check: Add test for real custom_checks check
def test_automation_active_check_unknown(test_cfg, site):
    data = _execute_automation(site, "active-check", args=["xxxhost", "xxxplugin", "xxxitem"])
    assert data is None


def test_automation_active_check_unknown_custom(test_cfg, site):
    data = _execute_automation(site, "active-check", args=["xxxhost", "custom", "xxxitem"])
    assert data is None


def test_automation_get_configuration(test_cfg, site):
    variable_names = [
        "agent_port",
    ]

    data = _execute_automation(site, "get-configuration", stdin=repr(variable_names))
    assert isinstance(data, dict)
    assert data["agent_port"] == 6556

    try:
        site.write_file("etc/check_mk/main.mk", "agent_port = 6558")

        data = _execute_automation(site, "get-configuration", stdin=repr(variable_names))
        assert data["agent_port"] == 6558

        site.write_file("etc/check_mk/conf.d/agent-port.mk", "agent_port = 1234")

        data = _execute_automation(site, "get-configuration", stdin=repr(variable_names))
        assert data["agent_port"] == 6558

        site.write_file("etc/check_mk/main.mk", "")

        data = _execute_automation(site, "get-configuration", stdin=repr(variable_names))
        assert data["agent_port"] == 6556

        site.delete_file("etc/check_mk/conf.d/agent-port.mk")

        data = _execute_automation(site, "get-configuration", stdin=repr(variable_names))
        assert data["agent_port"] == 6556
    finally:
        if site.file_exists("etc/check_mk/conf.d/agent-port.mk"):
            site.delete_file("etc/check_mk/conf.d/agent-port.mk")

        site.write_file("etc/check_mk/main.mk", "")


def test_automation_get_service_configurations(test_cfg, site):
    data = _execute_automation(site, "get-service-configurations")
    assert isinstance(data, dict)
    assert data["checkgroup_of_checks"]
    assert data["hosts"]["modes-test-host"]
    assert ('cpu.loads', u'CPU load', (5.0, 10.0)) in data["hosts"]["modes-test-host"]["checks"]


def test_automation_create_diagnostics_dump(test_cfg, site):
    data = _execute_automation(site, "create-diagnostics-dump")
    tarfile_path = data["tarfile_path"]
    assert isinstance(data, dict)
    assert "Collect diagnostics information" in data["output"]
    assert tarfile_path.endswith(".tar.gz")
    assert "var/check_mk/diagnostics" in tarfile_path


# TODO: rename-hosts
# TODO: delete-hosts
# TODO: scan-parents
# TODO: diag-host
