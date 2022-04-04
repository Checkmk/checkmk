#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import re
import subprocess

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import get_standard_linux_agent_output

import cmk.utils.paths
from cmk.utils.type_defs import DiscoveryResult, HostName, SetAutochecksTable

from cmk.automations import results

import cmk.base.autochecks as autochecks


@pytest.fixture(name="test_cfg", scope="module")
def test_cfg_fixture(site: Site, web):
    site.ensure_running()

    print("Applying default config")
    site.openapi.create_host(
        "modes-test-host",
        attributes={
            "ipaddress": "127.0.0.1",
        },
    )
    site.openapi.create_host(
        "modes-test-host2",
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "test",
        },
    )
    site.openapi.create_host(
        "modes-test-host3",
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "test",
        },
    )
    site.openapi.create_host(
        "modes-test-host4",
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "offline",
        },
    )
    site.openapi.create_host(
        "host_with_secondary_ip",
        attributes={"ipaddress": "127.0.0.1", "additional_ipv4addresses": ["127.0.0.1"]},
    )

    site.write_text_file(
        "etc/check_mk/conf.d/modes-test-host.mk",
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ALL_HOSTS))\n",
    )

    site.makedirs("var/check_mk/agent_output/")
    site.write_text_file(
        "var/check_mk/agent_output/modes-test-host", get_standard_linux_agent_output()
    )
    site.write_text_file(
        "var/check_mk/agent_output/modes-test-host2", get_standard_linux_agent_output()
    )
    site.write_text_file(
        "var/check_mk/agent_output/modes-test-host3", get_standard_linux_agent_output()
    )

    web.discover_services("modes-test-host")  # Replace with RestAPI call, see CMK-9249
    web.discover_services("modes-test-host2")  # Replace with RestAPI call, see CMK-9249
    web.discover_services("modes-test-host3")  # Replace with RestAPI call, see CMK-9249
    web.discover_services("host_with_secondary_ip")  # Replace with RestAPI call, see CMK-9249
    icmp_rule_id = site.openapi.create_rule(
        ruleset_name="active_checks:icmp", value={"address": "all_ipv4addresses"}
    )

    try:
        site.activate_changes_and_wait_for_core_reload()
        yield None
    finally:
        #
        # Cleanup code
        #
        print("Cleaning up test config")

        site.delete_dir("var/check_mk/agent_output")

        site.delete_file("etc/check_mk/conf.d/modes-test-host.mk")

        site.openapi.delete_host("modes-test-host")
        site.openapi.delete_host("modes-test-host2")
        site.openapi.delete_host("modes-test-host3")
        site.openapi.delete_host("modes-test-host4")
        site.openapi.delete_host("host_with_secondary_ip")
        site.openapi.delete_rule(icmp_rule_id)
        site.activate_changes_and_wait_for_core_reload()


# .
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


def _execute_automation(
    site: Site,
    cmd,
    args=None,
    stdin=None,
    expect_stdout=None,
    expect_stderr="",
    expect_stderr_pattern="",
    expect_exit_code=0,
    parse_data=True,
):
    cmdline = ["cmk", "--automation", cmd] + ([] if args is None else args)
    print(cmdline)
    p = site.execute(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

    stdout, stderr = p.communicate(stdin)

    error_msg = "Exit code: %d, Output: %r, Error: %r" % (p.wait(), stdout, stderr)

    assert p.wait() == expect_exit_code, error_msg

    if expect_stderr_pattern:
        assert re.match(expect_stderr_pattern, stderr) is not None, error_msg
    else:
        assert stderr == expect_stderr, error_msg

    if expect_stdout is not None:
        assert stdout == expect_stdout, error_msg

    if parse_data:
        return results.result_type_registry[cmd].deserialize(stdout)

    return None


def test_automation_discovery_no_host(test_cfg, site: Site):
    # NOTE: We can't use @raiseerrors here, because this would redirect stderr to /dev/null!
    p = site.execute(
        ["cmk", "--automation", "inventory", "@scan", "new"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = p.communicate()
    assert "Need two arguments:" in stderr
    assert stdout == ""
    assert p.wait() == 1


def test_automation_discovery_single_host(test_cfg, site: Site):
    result = _execute_automation(
        site,
        "inventory",
        args=["@raiseerrors", "new", "modes-test-host"],
    )

    assert isinstance(result, results.DiscoveryResult)
    assert result.hosts["modes-test-host"].diff_text == "Nothing was changed."
    assert result.hosts["modes-test-host"].error_text is None


def test_automation_discovery_multiple_hosts(test_cfg, site: Site):
    result = _execute_automation(
        site,
        "inventory",
        args=["@raiseerrors", "new", "modes-test-host", "modes-test-host2"],
    )

    assert isinstance(result, results.DiscoveryResult)
    assert result.hosts["modes-test-host"].diff_text == "Nothing was changed."
    assert result.hosts["modes-test-host"].error_text is None
    assert result.hosts["modes-test-host2"].diff_text == "Nothing was changed."
    assert result.hosts["modes-test-host2"].error_text is None


def test_automation_discovery_not_existing_host(test_cfg, site: Site):
    result = _execute_automation(
        site,
        "inventory",
        args=["@raiseerrors", "new", "xxxhost"],
    )

    assert isinstance(result, results.DiscoveryResult)
    assert result.hosts == {
        "xxxhost": DiscoveryResult(
            clustered_new=0,
            clustered_old=0,
            clustered_vanished=0,
            diff_text=None,
            error_text="",
            self_kept=0,
            self_new=0,
            self_new_host_labels=0,
            self_removed=0,
            self_total=0,
            self_total_host_labels=0,
        )
    }


def test_automation_discovery_with_cache_option(test_cfg, site: Site):
    result = _execute_automation(
        site,
        "inventory",
        args=["new", "modes-test-host"],
    )

    assert isinstance(result, results.DiscoveryResult)
    assert result.hosts["modes-test-host"].diff_text == "Nothing was changed."
    assert result.hosts["modes-test-host"].error_text is None


def test_automation_analyse_service_autocheck(test_cfg, site: Site):
    automation_result = _execute_automation(
        site,
        "analyse-service",
        args=["modes-test-host", "Apache 127.0.0.1:5000 Status"],
    )
    assert isinstance(automation_result, results.AnalyseServiceResult)
    assert automation_result.service_info["origin"] == "auto"
    assert automation_result.service_info["checktype"] == "apache_status"
    assert automation_result.service_info["item"] == "127.0.0.1:5000"
    assert automation_result.service_info["checkgroup"] == "apache_status"


def test_automation_analyse_service_no_check(test_cfg, site: Site):
    automation_result = _execute_automation(
        site,
        "analyse-service",
        args=["modes-test-host", "XXX CPU load"],
    )
    assert isinstance(automation_result, results.AnalyseServiceResult)
    assert automation_result.service_info == {}


def test_automation_try_discovery_not_existing_host(test_cfg, site: Site):
    _execute_automation(
        site,
        "try-inventory",
        args=["xxx-not-existing-host"],
        expect_stderr_pattern=(
            r"Failed to lookup IPv4 address of xxx-not-existing-host "
            r"via DNS: (\[Errno -2\] Name or service not known"
            r"|\[Errno -3\] Temporary failure in name resolution"
            r"|\[Errno -5\] No address associated with hostname)\n"
        ),
        expect_stdout="",
        expect_exit_code=2,
        parse_data=False,
    )


def test_automation_try_discovery_host(test_cfg, site: Site):
    result = _execute_automation(
        site,
        "try-inventory",
        args=["modes-test-host"],
    )
    assert isinstance(result, results.TryDiscoveryResult)
    assert isinstance(result.output, str)
    assert isinstance(result.check_table, list)


def test_automation_set_autochecks(test_cfg, site: Site):
    hostname = HostName("blablahost")
    new_items: SetAutochecksTable = {
        ("df", "xxx"): ("Filesystem xxx", {}, {"xyz": "123"}, [hostname]),
        ("uptime", None): ("Uptime", None, {}, [hostname]),
    }

    try:
        assert isinstance(
            _execute_automation(
                site,
                "set-autochecks",
                args=[hostname],
                stdin=repr(new_items),
            ),
            results.SetAutochecksResult,
        )

        autochecks_file = "%s/%s.mk" % (cmk.utils.paths.autochecks_dir, hostname)
        assert os.path.exists(autochecks_file)

        data = autochecks.AutochecksStore(hostname).read()
        services = [
            (
                (str(s.check_plugin_name), s.item),
                s.parameters,
                s.service_labels,
            )
            for s in data
        ]
        assert sorted(services) == [
            (
                ("df", "xxx"),
                {},
                {"xyz": "123"},
            ),
            (
                ("uptime", None),
                None,
                {},
            ),
        ]

        assert site.file_exists("var/check_mk/autochecks/%s.mk" % hostname)
    finally:
        if site.file_exists("var/check_mk/autochecks/%s.mk" % hostname):
            site.delete_file("var/check_mk/autochecks/%s.mk" % hostname)


def test_automation_update_dns_cache(test_cfg, site: Site):
    cache_path = "var/check_mk/ipaddresses.cache"

    if site.file_exists(cache_path):
        site.delete_file(cache_path)

    try:
        site.openapi.create_host("update-dns-cache-host")
        site.openapi.create_host("localhost")

        site.write_text_file(cache_path, "{('bla', 4): '127.0.0.1'}")

        result = _execute_automation(site, "update-dns-cache")
        assert isinstance(result, results.UpdateDNSCacheResult)

        assert result.n_updated > 0
        assert result.failed_hosts == ["update-dns-cache-host"]

        assert site.file_exists(cache_path)

        cache = eval(site.read_file(cache_path))  # pylint:disable=eval-used
        assert isinstance(cache, dict)
        assert cache[("localhost", 4)] == "127.0.0.1"
        assert ("bla", 4) not in cache

    finally:
        site.openapi.delete_host("localhost")
        site.openapi.delete_host("update-dns-cache-host")


# TODO: Test with the different cores
def test_automation_reload(test_cfg, site: Site):
    result = _execute_automation(site, "reload")
    assert isinstance(result, results.ReloadResult)
    assert not result.config_warnings


# TODO: Test with the different cores
def test_automation_restart(test_cfg, site: Site):
    result = _execute_automation(site, "restart")
    assert isinstance(result, results.RestartResult)
    assert not result.config_warnings


def test_automation_get_check_information(test_cfg, site: Site):
    result = _execute_automation(site, "get-check-information")
    assert isinstance(result, results.GetCheckInformationResult)
    assert len(result.plugin_infos) > 1000

    for info in result.plugin_infos.values():
        assert isinstance(info["title"], str)
        assert "service_description" in info


def test_automation_get_section_information(test_cfg, site: Site):
    result = _execute_automation(site, "get-section-information")
    assert isinstance(result, results.GetSectionInformationResult)
    assert len(result.section_infos) > 1000

    for info in result.section_infos.values():
        assert isinstance(info["name"], str)
        assert "type" in info
        assert info["type"] in ("snmp", "agent")


def test_automation_notification_replay(test_cfg, site: Site):
    site.write_text_file(
        "var/check_mk/notify/backlog.mk",
        "[{'SERVICEACKCOMMENT': '', 'SERVICE_EC_CONTACT': '', 'PREVIOUSSERVICEHARDSTATEID': '0', 'HOST_ADDRESS_6': '', 'NOTIFICATIONAUTHORNAME': '', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LONGSERVICEOUTPUT': '', 'LASTHOSTPROBLEMID': '0', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'SERVICEDOWNTIME': '0', 'LASTSERVICESTATE': 'OK', 'SERVICEDESC': 'Temperature Zone 0', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICENOTES': '', 'HOSTPERFDATA': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'LASTHOSTSTATEID': '0', 'SERVICENOTESURL': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTSERVICESTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTDOWNTIME': '0', 'SERVICECHECKCOMMAND': 'check_mk-lnx_thermal', 'SERVICEPROBLEMID': '138', 'HOST_SL': '', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'SERVICESTATE': 'WARNING', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': 'temp=75;70;80;;', 'NOTIFICATIONAUTHORALIAS': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'MICROTIME': '1502452826145843', 'SERVICEOUTPUT': 'WARN - 75.0 \xc2\xb0C (warn/crit at 70/80 \xc2\xb0C)', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICECONTACTGROUPNAMES': 'all', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '138', 'HOST_FILENAME': '/wato/hosts.mk', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'CONTACTS': '', 'SERVICEDISPLAYNAME': 'Temperature Zone 0', 'HOSTNAME': 'localhost', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'NOTIFICATIONTYPE': 'PROBLEM', 'SVC_SL': '', 'SERVICESTATEID': '1', 'LASTHOSTSTATE': 'PENDING', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'HOSTADDRESS': '127.0.0.1', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}, {'SERVICEACKCOMMENT': '', 'HOSTPERFDATA': '', 'SERVICEDOWNTIME': '0', 'PREVIOUSSERVICEHARDSTATEID': '0', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'LASTSERVICESTATE': 'OK', 'LONGSERVICEOUTPUT': '', 'NOTIFICATIONTYPE': 'PROBLEM', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'HOSTNAME': 'localhost', 'NOTIFICATIONAUTHORNAME': '', 'SERVICEDESC': 'Check_MK Agent', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICECONTACTGROUPNAMES': 'all', 'SERVICE_EC_CONTACT': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'MICROTIME': '1502452826145283', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTHOSTSTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTADDRESS': '127.0.0.1', 'SERVICEPROBLEMID': '137', 'HOST_SL': '', 'LASTSERVICESTATEID': '0', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'HOST_ADDRESS_6': '', 'SERVICEOUTPUT': 'WARN - error: This host is not registered for deployment(!), last update check: 2017-05-22 10:28:43 (warn at 2 days)(!), last agent update: 2017-05-22 09:28:24', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICENOTES': '', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '137', 'HOST_FILENAME': '/wato/hosts.mk', 'LASTHOSTSTATE': 'PENDING', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'SERVICECHECKCOMMAND': 'check_mk-check_mk.agent_update', 'SERVICEDISPLAYNAME': 'Check_MK Agent', 'CONTACTS': '', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LASTHOSTPROBLEMID': '0', 'SVC_SL': '', 'SERVICESTATEID': '1', 'SERVICESTATE': 'WARNING', 'NOTIFICATIONAUTHORALIAS': '', 'SERVICENOTESURL': '', 'HOSTDOWNTIME': '0', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}]",  # noqa: E501
    )
    assert isinstance(
        _execute_automation(site, "notification-replay", args=["0"]),
        results.NotificationReplayResult,
    )


def test_automation_notification_analyse(test_cfg, site: Site):
    site.write_text_file(
        "var/check_mk/notify/backlog.mk",
        "[{'SERVICEACKCOMMENT': '', 'SERVICE_EC_CONTACT': '', 'PREVIOUSSERVICEHARDSTATEID': '0', 'HOST_ADDRESS_6': '', 'NOTIFICATIONAUTHORNAME': '', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LONGSERVICEOUTPUT': '', 'LASTHOSTPROBLEMID': '0', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'SERVICEDOWNTIME': '0', 'LASTSERVICESTATE': 'OK', 'SERVICEDESC': 'Temperature Zone 0', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICENOTES': '', 'HOSTPERFDATA': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'LASTHOSTSTATEID': '0', 'SERVICENOTESURL': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTSERVICESTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTDOWNTIME': '0', 'SERVICECHECKCOMMAND': 'check_mk-lnx_thermal', 'SERVICEPROBLEMID': '138', 'HOST_SL': '', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'SERVICESTATE': 'WARNING', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': 'temp=75;70;80;;', 'NOTIFICATIONAUTHORALIAS': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'MICROTIME': '1502452826145843', 'SERVICEOUTPUT': 'WARN - 75.0 \xc2\xb0C (warn/crit at 70/80 \xc2\xb0C)', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICECONTACTGROUPNAMES': 'all', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '138', 'HOST_FILENAME': '/wato/hosts.mk', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'CONTACTS': '', 'SERVICEDISPLAYNAME': 'Temperature Zone 0', 'HOSTNAME': 'localhost', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'NOTIFICATIONTYPE': 'PROBLEM', 'SVC_SL': '', 'SERVICESTATEID': '1', 'LASTHOSTSTATE': 'PENDING', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'HOSTADDRESS': '127.0.0.1', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}, {'SERVICEACKCOMMENT': '', 'HOSTPERFDATA': '', 'SERVICEDOWNTIME': '0', 'PREVIOUSSERVICEHARDSTATEID': '0', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'LASTSERVICESTATE': 'OK', 'LONGSERVICEOUTPUT': '', 'NOTIFICATIONTYPE': 'PROBLEM', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'HOSTNAME': 'localhost', 'NOTIFICATIONAUTHORNAME': '', 'SERVICEDESC': 'Check_MK Agent', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICECONTACTGROUPNAMES': 'all', 'SERVICE_EC_CONTACT': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'MICROTIME': '1502452826145283', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTHOSTSTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTADDRESS': '127.0.0.1', 'SERVICEPROBLEMID': '137', 'HOST_SL': '', 'LASTSERVICESTATEID': '0', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'HOST_ADDRESS_6': '', 'SERVICEOUTPUT': 'WARN - error: This host is not registered for deployment(!), last update check: 2017-05-22 10:28:43 (warn at 2 days)(!), last agent update: 2017-05-22 09:28:24', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICENOTES': '', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '137', 'HOST_FILENAME': '/wato/hosts.mk', 'LASTHOSTSTATE': 'PENDING', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'SERVICECHECKCOMMAND': 'check_mk-check_mk.agent_update', 'SERVICEDISPLAYNAME': 'Check_MK Agent', 'CONTACTS': '', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LASTHOSTPROBLEMID': '0', 'SVC_SL': '', 'SERVICESTATEID': '1', 'SERVICESTATE': 'WARNING', 'NOTIFICATIONAUTHORALIAS': '', 'SERVICENOTESURL': '', 'HOSTDOWNTIME': '0', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}]",  # noqa: E501
    )
    assert isinstance(
        _execute_automation(site, "notification-analyse", args=["0"]),
        results.NotificationAnalyseResult,
    )


def test_automation_notification_get_bulks(test_cfg, site: Site):
    result = _execute_automation(site, "notification-get-bulks", args=["0"])
    assert isinstance(result, results.NotificationGetBulksResult)
    assert not result.result


def test_automation_get_agent_output(test_cfg, site: Site):
    result = _execute_automation(
        site,
        "get-agent-output",
        args=["modes-test-host", "agent"],
    )
    assert isinstance(result, results.GetAgentOutputResult)

    assert result.service_details == ""
    assert isinstance(result.raw_agent_data, bytes)
    assert b"<<<uptime>>>" in bytes(result.raw_agent_data)
    assert result.success is True


def test_automation_get_agent_output_unknown_host(test_cfg, site: Site):
    result = _execute_automation(
        site,
        "get-agent-output",
        args=["xxxhost", "agent"],
    )
    assert isinstance(result, results.GetAgentOutputResult)

    assert result.service_details.startswith("Failed to fetch data from ")
    assert result.raw_agent_data == b""
    assert result.success is False


# TODO: active-check: Add test for real custom_checks check
def test_automation_active_check_unknown(test_cfg, site: Site):
    result = _execute_automation(
        site,
        "active-check",
        args=["xxxhost", "xxxplugin", "xxxitem"],
    )
    assert isinstance(result, results.ActiveCheckResult)
    assert result.state is None
    assert result.output == "Failed to compute check result"


def test_automation_active_check_icmp_all_ipv4(test_cfg, site: Site):
    for host in ("modes-test-host", "host_with_secondary_ip"):
        result = _execute_automation(
            site,
            "active-check",
            args=[host, "icmp", "PING all IPv4 Addresses"],
        )
        assert isinstance(result, results.ActiveCheckResult)
        assert result.state == 0
        assert result.output.startswith("OK - 127.0.0.1: rta")


def test_automation_active_check_unknown_custom(test_cfg, site: Site):
    result = _execute_automation(
        site,
        "active-check",
        args=["xxxhost", "custom", "xxxitem"],
    )
    assert isinstance(result, results.ActiveCheckResult)
    assert result.state is None
    assert result.output == "Failed to compute check result"


def test_automation_get_configuration(test_cfg, site: Site):
    variable_names = [
        "agent_port",
    ]

    automation_result = _execute_automation(
        site,
        "get-configuration",
        stdin=repr(variable_names),
    )
    assert isinstance(automation_result, results.GetConfigurationResult)
    assert automation_result.result["agent_port"] == 6556

    try:
        site.write_text_file("etc/check_mk/main.mk", "agent_port = 6558")

        result = _execute_automation(site, "get-configuration", stdin=repr(variable_names)).result
        assert result["agent_port"] == 6558

        site.write_text_file("etc/check_mk/conf.d/agent-port.mk", "agent_port = 1234")

        result = _execute_automation(site, "get-configuration", stdin=repr(variable_names)).result
        assert result["agent_port"] == 6558

        site.write_text_file("etc/check_mk/main.mk", "")

        result = _execute_automation(site, "get-configuration", stdin=repr(variable_names)).result
        assert result["agent_port"] == 6556

        site.delete_file("etc/check_mk/conf.d/agent-port.mk")

        result = _execute_automation(site, "get-configuration", stdin=repr(variable_names)).result
        assert result["agent_port"] == 6556
    finally:
        if site.file_exists("etc/check_mk/conf.d/agent-port.mk"):
            site.delete_file("etc/check_mk/conf.d/agent-port.mk")

        site.write_text_file("etc/check_mk/main.mk", "")


def test_automation_create_diagnostics_dump(test_cfg, site: Site):
    result = _execute_automation(site, "create-diagnostics-dump")
    assert isinstance(result, results.CreateDiagnosticsDumpResult)
    assert "+ COLLECT DIAGNOSTICS INFORMATION" in result.output
    assert result.tarfile_path.endswith(".tar.gz")
    assert "var/check_mk/diagnostics" in result.tarfile_path


# TODO: rename-hosts
# TODO: delete-hosts
# TODO: scan-parents
# TODO: diag-host
