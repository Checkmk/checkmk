#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import logging
import re
from collections.abc import Iterator, MutableMapping, Sequence

import pytest

from tests.testlib.site import Site
from tests.testlib.utils import get_standard_linux_agent_output

from cmk.ccc.hostaddress import HostName

from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.servicename import ServiceName

from cmk.automations import results
from cmk.automations.results import SetAutochecksInput

from cmk.checkengine.discovery import DiscoveryReport, DiscoverySettings
from cmk.checkengine.discovery._autochecks import _AutochecksSerializer
from cmk.checkengine.plugins import AutocheckEntry, CheckPluginName

logger = logging.getLogger(__name__)


@pytest.fixture(name="test_cfg", scope="module")
def test_cfg_fixture(site: Site) -> Iterator[None]:
    site.ensure_running()

    logger.info("Applying default config")
    site.openapi.hosts.create(
        "modes-test-host",
        attributes={
            "ipaddress": "127.0.0.1",
        },
    )
    site.openapi.hosts.create(
        "modes-test-host2",
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "test",
        },
    )
    site.openapi.hosts.create(
        "modes-test-host3",
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "test",
        },
    )
    site.openapi.hosts.create(
        "modes-test-host4",
        attributes={
            "ipaddress": "127.0.0.1",
            "tag_criticality": "offline",
        },
    )
    site.openapi.hosts.create(
        "host_with_secondary_ip",
        attributes={"ipaddress": "127.0.0.1", "additional_ipv4addresses": ["127.0.0.1"]},
    )

    site.write_file(
        "etc/check_mk/conf.d/modes-test-host.mk",
        "datasource_programs.append({'condition': {}, 'value': 'cat ~/var/check_mk/agent_output/<HOST>'})\n",
    )

    site.makedirs("var/check_mk/agent_output/")
    site.write_file("var/check_mk/agent_output/modes-test-host", get_standard_linux_agent_output())
    site.write_file("var/check_mk/agent_output/modes-test-host2", get_standard_linux_agent_output())
    site.write_file("var/check_mk/agent_output/modes-test-host3", get_standard_linux_agent_output())

    site.openapi.service_discovery.run_discovery_and_wait_for_completion("modes-test-host")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion("modes-test-host2")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion("modes-test-host3")
    site.openapi.service_discovery.run_discovery_and_wait_for_completion("host_with_secondary_ip")
    icmp_rule_id = site.openapi.rules.create(
        ruleset_name=RuleGroup.ActiveChecks("icmp"),
        value={"address": "all_ipv4addresses"},
    )

    try:
        site.activate_changes_and_wait_for_core_reload()
        yield None
    finally:
        #
        # Cleanup code
        #
        logger.info("Cleaning up test config")

        site.delete_dir("var/check_mk/agent_output")

        site.delete_file("etc/check_mk/conf.d/modes-test-host.mk")

        site.openapi.hosts.delete("modes-test-host")
        site.openapi.hosts.delete("modes-test-host2")
        site.openapi.hosts.delete("modes-test-host3")
        site.openapi.hosts.delete("modes-test-host4")
        site.openapi.hosts.delete("host_with_secondary_ip")
        site.openapi.rules.delete(icmp_rule_id)
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
    cmd: str,
    args: Sequence[str] | None = None,
    stdin: str | None = None,
    expect_stdout: str | None = None,
    expect_stderr: str = "",
    expect_stderr_pattern: str = "",
    expect_exit_code: int = 0,
    parse_data: bool = True,
) -> object:
    cmdline = ["cmk", "--automation", cmd, *([] if args is None else args)]
    p = site.run(cmdline, input_=stdin, check=False)
    error_msg = "Exit code: %d, Output: %r, Error: %r" % (p.returncode, p.stdout, p.stderr)

    assert p.returncode == expect_exit_code, error_msg

    if expect_stderr_pattern:
        assert re.match(expect_stderr_pattern, p.stderr) is not None, error_msg
    else:
        assert p.stderr == expect_stderr, error_msg

    if expect_stdout is not None:
        assert p.stdout == expect_stdout, error_msg

    if parse_data:
        return results.result_type_registry[cmd].deserialize(p.stdout)

    return None


_DISCO_SETTINGS = DiscoverySettings(
    update_host_labels=True,
    add_new_services=True,
    remove_vanished_services=False,
    update_changed_service_labels=False,
    update_changed_service_parameters=False,
).to_automation_arg()


@pytest.mark.usefixtures("test_cfg")
def test_automation_discovery_no_host(site: Site) -> None:
    # NOTE: We can't use @raiseerrors here, because this would redirect stderr to /dev/null!
    p = site.run(
        ["cmk", "--automation", "service-discovery", "@scan", _DISCO_SETTINGS],
        check=False,
    )

    assert "Need two arguments:" in p.stderr
    assert p.stdout == ""
    assert p.returncode == 1


@pytest.mark.usefixtures("test_cfg")
def test_automation_discovery_single_host(site: Site) -> None:
    result = _execute_automation(
        site,
        "service-discovery",
        args=["@raiseerrors", _DISCO_SETTINGS, "modes-test-host"],
    )

    assert isinstance(result, results.ServiceDiscoveryResult)
    assert result.hosts[HostName("modes-test-host")].diff_text == "Nothing was changed."
    assert result.hosts[HostName("modes-test-host")].error_text is None


@pytest.mark.usefixtures("test_cfg")
def test_automation_discovery_multiple_hosts(site: Site) -> None:
    result = _execute_automation(
        site,
        "service-discovery",
        args=["@raiseerrors", _DISCO_SETTINGS, "modes-test-host", "modes-test-host2"],
    )

    assert isinstance(result, results.ServiceDiscoveryResult)
    assert result.hosts[HostName("modes-test-host")].diff_text == "Nothing was changed."
    assert result.hosts[HostName("modes-test-host")].error_text is None
    assert result.hosts[HostName("modes-test-host2")].diff_text == "Nothing was changed."
    assert result.hosts[HostName("modes-test-host2")].error_text is None


@pytest.mark.usefixtures("test_cfg")
def test_automation_discovery_not_existing_host(site: Site) -> None:
    result = _execute_automation(
        site,
        "service-discovery",
        args=["@raiseerrors", _DISCO_SETTINGS, "xxxhost"],
    )

    assert isinstance(result, results.ServiceDiscoveryResult)
    assert result.hosts == {"xxxhost": DiscoveryReport(error_text="")}


@pytest.mark.usefixtures("test_cfg")
def test_automation_discovery_with_cache_option(site: Site) -> None:
    result = _execute_automation(
        site,
        "service-discovery",
        args=[_DISCO_SETTINGS, "modes-test-host"],
    )

    assert isinstance(result, results.ServiceDiscoveryResult)
    assert result.hosts[HostName("modes-test-host")].diff_text == "Nothing was changed."
    assert result.hosts[HostName("modes-test-host")].error_text is None


@pytest.mark.usefixtures("test_cfg")
def test_automation_analyse_service_autocheck(site: Site) -> None:
    automation_result = _execute_automation(
        site,
        "analyse-service",
        args=["modes-test-host", "Apache 127.0.0.1:5000 Status"],
    )
    assert isinstance(automation_result, results.AnalyseServiceResult)
    assert automation_result.service_info.get("origin") == "auto"
    assert automation_result.service_info.get("checktype") == "apache_status"
    assert automation_result.service_info.get("item") == "127.0.0.1:5000"
    assert automation_result.service_info.get("checkgroup") == "apache_status"


@pytest.mark.usefixtures("test_cfg")
def test_automation_analyse_service_no_check(site: Site) -> None:
    automation_result = _execute_automation(
        site,
        "analyse-service",
        args=["modes-test-host", "XXX CPU load"],
    )
    assert isinstance(automation_result, results.AnalyseServiceResult)
    assert automation_result.service_info == {}
    assert automation_result.labels == {}
    assert automation_result.label_sources == {}


@pytest.mark.usefixtures("test_cfg")
def test_automation_analyze_host_rule_matches(site: Site) -> None:
    automation_result = _execute_automation(
        site,
        "analyze-host-rule-matches",
        args=["modes-test-host"],
        stdin=repr(
            [
                [
                    {
                        "id": "b92a5406-1d56-4f1d-953d-225b111239e3",
                        "value": "ag",
                        "condition": {},
                        "options": {
                            "description": "",
                        },
                    }
                ],
                [
                    {
                        "id": "aaaaaaaa-1d56-4f1d-953d-225b111239e3",
                        "value": "duda",
                        "condition": {
                            "host_tags": {
                                "criticality": "test",
                            }
                        },
                        "options": {
                            "description": "",
                        },
                    }
                ],
            ]
        ),
    )

    assert isinstance(automation_result, results.AnalyzeHostRuleMatchesResult)
    assert automation_result.results == {
        "b92a5406-1d56-4f1d-953d-225b111239e3": ["ag"],
        "aaaaaaaa-1d56-4f1d-953d-225b111239e3": [],
    }


@pytest.mark.usefixtures("test_cfg")
def test_automation_analyze_service_rule_matches(site: Site) -> None:
    automation_result = _execute_automation(
        site,
        "analyze-service-rule-matches",
        args=["modes-test-host", "Ding"],
        stdin=repr(
            (
                [
                    [
                        {
                            "id": "b92a5406-1d56-4f1d-953d-225b111239e3",
                            "value": "yay",
                            "condition": {"service_description": [{"$regex": "Ding$"}]},
                            "options": {
                                "description": "",
                            },
                        }
                    ],
                    [
                        {
                            "id": "aaaaaaaa-1d56-4f1d-953d-225b111239e3",
                            "value": "nono",
                            "condition": {"service_description": [{"$regex": "Dong$"}]},
                            "options": {
                                "description": "",
                            },
                        }
                    ],
                ],
                {},
            )
        ),
    )

    assert isinstance(automation_result, results.AnalyzeServiceRuleMatchesResult)
    assert automation_result.results == {
        "b92a5406-1d56-4f1d-953d-225b111239e3": ["yay"],
        "aaaaaaaa-1d56-4f1d-953d-225b111239e3": [],
    }


def test_automation_discovery_preview_not_existing_host(site: Site) -> None:
    _execute_automation(
        site,
        "service-discovery-preview",
        args=["xxx-not-existing-host."],
        expect_stderr_pattern=(
            r"Failed to lookup IPv4 address of xxx-not-existing-host. "
            r"via DNS: (\[Errno -2\] Name or service not known"
            r"|\[Errno -3\] Temporary failure in name resolution"
            r"|\[Errno -5\] No address associated with hostname)\n"
        ),
        expect_stdout="",
        expect_exit_code=1,
        parse_data=False,
    )


@pytest.mark.usefixtures("test_cfg")
def test_automation_discovery_preview_host(site: Site) -> None:
    result = _execute_automation(
        site,
        "service-discovery-preview",
        args=["modes-test-host"],
    )
    assert isinstance(result, results.ServiceDiscoveryPreviewResult)
    assert isinstance(result.output, str)
    assert isinstance(result.check_table, list)
    assert isinstance(result.nodes_check_table, dict)
    for _h, node_check_table in result.nodes_check_table.items():
        assert isinstance(node_check_table, list)


@pytest.mark.usefixtures("test_cfg")
def test_automation_set_autochecks_v2(site: Site) -> None:
    host_name = HostName("blablahost")
    autochecks_table: MutableMapping[ServiceName, AutocheckEntry] = {
        "Filesystem xxx": AutocheckEntry(CheckPluginName("df"), "xxx", {}, {"xyz": "123"}),
        "Uptime": AutocheckEntry(CheckPluginName("uptime"), None, {}, {}),
    }
    new_items: SetAutochecksInput = SetAutochecksInput(
        host_name,
        autochecks_table,
        {host_name: autochecks_table},
    )

    try:
        assert isinstance(
            _execute_automation(
                site,
                "set-autochecks-v2",
                args=None,
                stdin=new_items.serialize(),
            ),
            results.SetAutochecksV2Result,
        )

        autochecks_file = f"var/check_mk/autochecks/{host_name}.mk"
        assert site.file_exists(autochecks_file)

        data = _AutochecksSerializer().deserialize(site.read_file(autochecks_file).encode("utf-8"))
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
                {},
                {},
            ),
        ]

        assert site.file_exists("var/check_mk/autochecks/%s.mk" % host_name)
    finally:
        if site.file_exists("var/check_mk/autochecks/%s.mk" % host_name):
            site.delete_file("var/check_mk/autochecks/%s.mk" % host_name)


@pytest.mark.usefixtures("test_cfg")
def test_automation_update_dns_cache(site: Site) -> None:
    cache_path = "var/check_mk/ipaddresses.cache"

    if site.file_exists(cache_path):
        site.delete_file(cache_path)

    # use .internal. FQDN to avoid false positives in name resolution
    unknown_host = "update-dns-cache-host.internal."
    try:
        site.openapi.hosts.create(hostname=unknown_host)
        site.openapi.hosts.create(hostname="localhost")

        site.write_file(cache_path, "{('bla', 4): '127.0.0.1'}")

        result = _execute_automation(site, "update-dns-cache")
        assert isinstance(result, results.UpdateDNSCacheResult)

        assert result.n_updated > 0
        assert result.failed_hosts == [unknown_host], (
            f'Successfully resolved unknown host "{unknown_host}"!'
        )

        assert site.file_exists(cache_path)

        cache = ast.literal_eval(site.read_file(cache_path))
        assert isinstance(cache, dict)
        assert cache[("localhost", 4)] == "127.0.0.1"
        assert ("bla", 4) not in cache
    finally:
        site.openapi.hosts.delete("localhost")
        site.openapi.hosts.delete(unknown_host)
        site.openapi.changes.activate_and_wait_for_completion(timeout=120)


# TODO: Test with the different cores
@pytest.mark.usefixtures("test_cfg")
def test_automation_reload(site: Site) -> None:
    result = _execute_automation(site, "reload")
    assert isinstance(result, results.ReloadResult)
    assert not result.config_warnings


# TODO: Test with the different cores
@pytest.mark.usefixtures("test_cfg")
def test_automation_restart(site: Site) -> None:
    result = _execute_automation(site, "restart")
    assert isinstance(result, results.RestartResult)
    assert not result.config_warnings


@pytest.mark.usefixtures("test_cfg")
def test_automation_get_check_information(site: Site) -> None:
    result = _execute_automation(site, "get-check-information")
    assert isinstance(result, results.GetCheckInformationResult)
    assert len(result.plugin_infos) > 1000

    for info in result.plugin_infos.values():
        assert isinstance(info["title"], str)
        assert "service_description" in info


@pytest.mark.usefixtures("test_cfg")
def test_automation_get_section_information(site: Site) -> None:
    result = _execute_automation(site, "get-section-information")
    assert isinstance(result, results.GetSectionInformationResult)
    assert len(result.section_infos) > 1000

    for info in result.section_infos.values():
        assert isinstance(info["name"], str)
        assert "type" in info
        assert info["type"] in ("snmp", "agent")


@pytest.mark.usefixtures("test_cfg")
def test_automation_notification_replay(site: Site) -> None:
    site.write_file(
        "var/check_mk/notify/backlog.mk",
        "[{'SERVICEACKCOMMENT': '', 'SERVICE_EC_CONTACT': '', 'PREVIOUSSERVICEHARDSTATEID': '0', 'HOST_ADDRESS_6': '', 'NOTIFICATIONAUTHORNAME': '', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LONGSERVICEOUTPUT': '', 'LASTHOSTPROBLEMID': '0', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'SERVICEDOWNTIME': '0', 'LASTSERVICESTATE': 'OK', 'SERVICEDESC': 'Temperature Zone 0', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICENOTES': '', 'HOSTPERFDATA': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'LASTHOSTSTATEID': '0', 'SERVICENOTESURL': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTSERVICESTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTDOWNTIME': '0', 'SERVICECHECKCOMMAND': 'check_mk-lnx_thermal', 'SERVICEPROBLEMID': '138', 'HOST_SL': '', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'SERVICESTATE': 'WARNING', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': 'temp=75;70;80;;', 'NOTIFICATIONAUTHORALIAS': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'MICROTIME': '1502452826145843', 'SERVICEOUTPUT': 'WARN - 75.0 \xc2\xb0C (warn/crit at 70/80 \xc2\xb0C)', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICECONTACTGROUPNAMES': 'all', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '138', 'HOST_FILENAME': '/wato/hosts.mk', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'CONTACTS': '', 'SERVICEDISPLAYNAME': 'Temperature Zone 0', 'HOSTNAME': 'localhost', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'NOTIFICATIONTYPE': 'PROBLEM', 'SVC_SL': '', 'SERVICESTATEID': '1', 'LASTHOSTSTATE': 'PENDING', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'HOSTADDRESS': '127.0.0.1', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}, {'SERVICEACKCOMMENT': '', 'HOSTPERFDATA': '', 'SERVICEDOWNTIME': '0', 'PREVIOUSSERVICEHARDSTATEID': '0', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'LASTSERVICESTATE': 'OK', 'LONGSERVICEOUTPUT': '', 'NOTIFICATIONTYPE': 'PROBLEM', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'HOSTNAME': 'localhost', 'NOTIFICATIONAUTHORNAME': '', 'SERVICEDESC': 'Check_MK Agent', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICECONTACTGROUPNAMES': 'all', 'SERVICE_EC_CONTACT': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'MICROTIME': '1502452826145283', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTHOSTSTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTADDRESS': '127.0.0.1', 'SERVICEPROBLEMID': '137', 'HOST_SL': '', 'LASTSERVICESTATEID': '0', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'HOST_ADDRESS_6': '', 'SERVICEOUTPUT': 'WARN - error: This host is not registered for deployment(!), last update check: 2017-05-22 10:28:43 (warn at 2 days)(!), last agent update: 2017-05-22 09:28:24', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICENOTES': '', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '137', 'HOST_FILENAME': '/wato/hosts.mk', 'LASTHOSTSTATE': 'PENDING', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'SERVICECHECKCOMMAND': 'check_mk-check_mk.agent_update', 'SERVICEDISPLAYNAME': 'Check_MK Agent', 'CONTACTS': '', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LASTHOSTPROBLEMID': '0', 'SVC_SL': '', 'SERVICESTATEID': '1', 'SERVICESTATE': 'WARNING', 'NOTIFICATIONAUTHORALIAS': '', 'SERVICENOTESURL': '', 'HOSTDOWNTIME': '0', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}]",
    )
    assert isinstance(
        _execute_automation(site, "notification-replay", args=["0"]),
        results.NotificationReplayResult,
    )


@pytest.mark.usefixtures("test_cfg")
def test_automation_notification_analyse(site: Site) -> None:
    site.write_file(
        "var/check_mk/notify/backlog.mk",
        "[{'SERVICEACKCOMMENT': '', 'SERVICE_EC_CONTACT': '', 'PREVIOUSSERVICEHARDSTATEID': '0', 'HOST_ADDRESS_6': '', 'NOTIFICATIONAUTHORNAME': '', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LONGSERVICEOUTPUT': '', 'LASTHOSTPROBLEMID': '0', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'SERVICEDOWNTIME': '0', 'LASTSERVICESTATE': 'OK', 'SERVICEDESC': 'Temperature Zone 0', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICENOTES': '', 'HOSTPERFDATA': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'LASTHOSTSTATEID': '0', 'SERVICENOTESURL': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTSERVICESTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTDOWNTIME': '0', 'SERVICECHECKCOMMAND': 'check_mk-lnx_thermal', 'SERVICEPROBLEMID': '138', 'HOST_SL': '', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'SERVICESTATE': 'WARNING', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': 'temp=75;70;80;;', 'NOTIFICATIONAUTHORALIAS': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'MICROTIME': '1502452826145843', 'SERVICEOUTPUT': 'WARN - 75.0 \xc2\xb0C (warn/crit at 70/80 \xc2\xb0C)', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICECONTACTGROUPNAMES': 'all', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '138', 'HOST_FILENAME': '/wato/hosts.mk', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'CONTACTS': '', 'SERVICEDISPLAYNAME': 'Temperature Zone 0', 'HOSTNAME': 'localhost', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'NOTIFICATIONTYPE': 'PROBLEM', 'SVC_SL': '', 'SERVICESTATEID': '1', 'LASTHOSTSTATE': 'PENDING', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'HOSTADDRESS': '127.0.0.1', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}, {'SERVICEACKCOMMENT': '', 'HOSTPERFDATA': '', 'SERVICEDOWNTIME': '0', 'PREVIOUSSERVICEHARDSTATEID': '0', 'LASTSERVICESTATECHANGE': '1502452826', 'HOSTGROUPNAMES': 'check_mk', 'LASTSERVICESTATE': 'OK', 'LONGSERVICEOUTPUT': '', 'NOTIFICATIONTYPE': 'PROBLEM', 'HOSTPROBLEMID': '0', 'HOSTNOTIFICATIONNUMBER': '0', 'SERVICE_SL': '', 'HOSTSTATE': 'PENDING', 'HOSTACKCOMMENT': '', 'LONGHOSTOUTPUT': '', 'LASTHOSTSTATECHANGE': '0', 'HOSTOUTPUT': '', 'HOSTNOTESURL': '', 'HOSTATTEMPT': '1', 'HOSTNAME': 'localhost', 'NOTIFICATIONAUTHORNAME': '', 'SERVICEDESC': 'Check_MK Agent', 'NOTIFICATIONAUTHOR': '', 'HOSTALIAS': 'localhost', 'PREVIOUSHOSTHARDSTATEID': '0', 'SERVICECONTACTGROUPNAMES': 'all', 'SERVICE_EC_CONTACT': '', 'SERVICEACKAUTHOR': '', 'SERVICEATTEMPT': '1', 'HOSTTAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'SERVICEGROUPNAMES': '', 'HOSTNOTES': '', 'NOTIFICATIONCOMMENT': '', 'HOST_ADDRESS_FAMILY': '4', 'MICROTIME': '1502452826145283', 'LASTHOSTUP': '0', 'PREVIOUSHOSTHARDSTATE': 'PENDING', 'LASTHOSTSTATEID': '0', 'LASTSERVICEOK': '0', 'HOSTADDRESS': '127.0.0.1', 'SERVICEPROBLEMID': '137', 'HOST_SL': '', 'LASTSERVICESTATEID': '0', 'HOSTCHECKCOMMAND': 'check-mk-host-smart', 'HOSTACKAUTHOR': '', 'SERVICEPERFDATA': '', 'HOST_ADDRESS_4': '127.0.0.1', 'HOSTSTATEID': '0', 'HOST_ADDRESS_6': '', 'SERVICEOUTPUT': 'WARN - error: This host is not registered for deployment(!), last update check: 2017-05-22 10:28:43 (warn at 2 days)(!), last agent update: 2017-05-22 09:28:24', 'HOSTCONTACTGROUPNAMES': 'all', 'HOST_EC_CONTACT': '', 'SERVICENOTES': '', 'MAXSERVICEATTEMPTS': '1', 'LASTSERVICEPROBLEMID': '137', 'HOST_FILENAME': '/wato/hosts.mk', 'LASTHOSTSTATE': 'PENDING', 'PREVIOUSSERVICEHARDSTATE': 'OK', 'SERVICECHECKCOMMAND': 'check_mk-check_mk.agent_update', 'SERVICEDISPLAYNAME': 'Check_MK Agent', 'CONTACTS': '', 'HOST_TAGS': '/wato/ cmk-agent ip-v4 ip-v4-only lan prod site:heute tcp wato', 'LASTHOSTPROBLEMID': '0', 'SVC_SL': '', 'SERVICESTATEID': '1', 'SERVICESTATE': 'WARNING', 'NOTIFICATIONAUTHORALIAS': '', 'SERVICENOTESURL': '', 'HOSTDOWNTIME': '0', 'SERVICENOTIFICATIONNUMBER': '1', 'MAXHOSTATTEMPTS': '1'}]",
    )
    assert isinstance(
        _execute_automation(site, "notification-analyse", args=["0"]),
        results.NotificationAnalyseResult,
    )


@pytest.mark.usefixtures("test_cfg")
def test_automation_notification_get_bulks(site: Site) -> None:
    result = _execute_automation(site, "notification-get-bulks", args=["0"])
    assert isinstance(result, results.NotificationGetBulksResult)
    assert not result.result


@pytest.mark.usefixtures("test_cfg")
def test_automation_get_agent_output(site: Site) -> None:
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


def test_automation_get_agent_output_unknown_host(site: Site) -> None:
    result = _execute_automation(
        site,
        "get-agent-output",
        args=["xxxhost.", "agent"],
    )
    assert isinstance(result, results.GetAgentOutputResult)

    assert result.service_details.startswith("Failed to fetch data from ")
    assert result.raw_agent_data == b""
    assert result.success is False


# TODO: active-check: Add test for real custom_checks check
def test_automation_active_check_unknown(site: Site) -> None:
    result = _execute_automation(
        site,
        "active-check",
        args=["xxxhost.", "xxxplugin", "xxxitem"],
    )
    assert isinstance(result, results.ActiveCheckResult)
    assert result.state is None
    assert result.output == "Failed to compute check result"


@pytest.mark.usefixtures("test_cfg")
def test_automation_active_check_icmp_all_ipv4(site: Site) -> None:
    for host in ("modes-test-host", "host_with_secondary_ip"):
        result = _execute_automation(
            site,
            "active-check",
            args=[host, "icmp", "PING all IPv4 Addresses"],
        )
        assert isinstance(result, results.ActiveCheckResult)
        assert result.state == 0
        assert result.output.startswith("OK - 127.0.0.1 rta")


def test_automation_active_check_unknown_custom(site: Site) -> None:
    result = _execute_automation(
        site,
        "active-check",
        args=["xxxhost.", "custom", "xxxitem"],
    )
    assert isinstance(result, results.ActiveCheckResult)
    assert result.state is None
    assert result.output == "Failed to compute check result"


@pytest.mark.usefixtures("test_cfg")
def test_automation_get_configuration(site: Site) -> None:
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
        site.write_file("etc/check_mk/main.mk", "agent_port = 6558")

        automation_result = _execute_automation(
            site, "get-configuration", stdin=repr(variable_names)
        )
        assert isinstance(automation_result, results.GetConfigurationResult)
        assert automation_result.result["agent_port"] == 6558

        site.write_file("etc/check_mk/conf.d/agent-port.mk", "agent_port = 1234")

        automation_result = _execute_automation(
            site, "get-configuration", stdin=repr(variable_names)
        )
        assert isinstance(automation_result, results.GetConfigurationResult)
        assert automation_result.result["agent_port"] == 6558

        site.write_file("etc/check_mk/main.mk", "")

        automation_result = _execute_automation(
            site, "get-configuration", stdin=repr(variable_names)
        )
        assert isinstance(automation_result, results.GetConfigurationResult)
        assert automation_result.result["agent_port"] == 6556

        site.delete_file("etc/check_mk/conf.d/agent-port.mk")

        automation_result = _execute_automation(
            site, "get-configuration", stdin=repr(variable_names)
        )
        assert isinstance(automation_result, results.GetConfigurationResult)
        assert automation_result.result["agent_port"] == 6556
    finally:
        if site.file_exists("etc/check_mk/conf.d/agent-port.mk"):
            site.delete_file("etc/check_mk/conf.d/agent-port.mk")

        site.write_file("etc/check_mk/main.mk", "")


@pytest.mark.usefixtures("test_cfg")
@pytest.mark.parametrize(
    "additional_options",
    [
        None,
        ["local-files"],
        ["omd-config"],
        ["checkmk-crashes"],
        ["local-files", "omd-config", "checkmk-crashes"],
    ],
    ids=[
        "default",
        "local_files",
        "omd_config",
        "checkmk_crashes",
        "local_files+omd_config+checkmk_crashes",
    ],
)
def test_automation_create_diagnostics_dump(
    site: Site, additional_options: list[str] | None
) -> None:
    result = _execute_automation(site, "create-diagnostics-dump", additional_options)
    assert isinstance(result, results.CreateDiagnosticsDumpResult)
    assert "+ COLLECT DIAGNOSTICS INFORMATION" in result.output
    assert result.tarfile_path.endswith(".tar.gz")
    assert "var/check_mk/diagnostics" in result.tarfile_path
    assert site.file_exists(result.tarfile_path)


def test_automation_restart_with_non_resolvable_host(site: Site) -> None:
    host = "modes-test-host-unresolvable"
    site.openapi.hosts.create(host)
    try:
        result = _execute_automation(site, "restart", expect_stderr_pattern=".*")
    finally:
        site.openapi.hosts.delete(host)
        site.openapi.changes.activate_and_wait_for_completion()

    assert isinstance(result, results.RestartResult)
    assert any(f"Failed to lookup IPv4 address of {host}" in w for w in result.config_warnings)
