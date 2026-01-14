#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.testlib.site import Site


@dataclass(frozen=True)
class MonitoringPlugin:
    """Data corresponding to 3rd party plugins.

    These plugins are maintained by 'Monitoring Plugins'
    (https://www.monitoring-plugins.org/).
    """

    binary_name: str
    # by default, output the version of the plugin
    cmd_line_option: str = "-V"
    expected: str = "v2.4.0"

    def detect_full_path(self, site: Site) -> Path:
        return site.root / "lib/nagios/plugins" / self.binary_name


@dataclass(frozen=True)
class CheckmkActiveCheck:
    """Data corresponding to Checkmk active checks."""

    binary_name: str
    path: str | None = None
    usage_text: str = "usage"
    cmd_line_option: str = "-h"

    @property
    def expected(self) -> str:
        return f"{self.usage_text}: {self.binary_name} "

    def detect_full_path(self, site: Site) -> Path:
        if self.path:
            return site.root / self.path / self.binary_name
        return site.root / _find_libexec(site, self.binary_name)


@dataclass(frozen=True)
class SpecialAgent:
    """Data corresponding to Checkmk special agents."""

    binary_name: str
    usage_text: str = "usage"
    cmd_line_option: str = "-h"

    @property
    def expected(self) -> str:
        return f"{self.usage_text}: {self.binary_name} "

    def detect_full_path(self, site: Site) -> Path:
        return site.root / _find_libexec(site, self.binary_name)


Plugin = MonitoringPlugin | CheckmkActiveCheck

MONITORING_PLUGINS: Sequence[Plugin] = (
    MonitoringPlugin("check_apt"),
    MonitoringPlugin("check_breeze"),
    MonitoringPlugin("check_by_ssh"),
    MonitoringPlugin("check_clamd"),
    MonitoringPlugin("check_cluster"),
    MonitoringPlugin("check_dhcp"),
    MonitoringPlugin("check_dig"),
    MonitoringPlugin("check_disk"),
    MonitoringPlugin("check_dns"),
    MonitoringPlugin("check_dummy"),
    MonitoringPlugin("check_file_age"),
    MonitoringPlugin("check_flexlm"),
    MonitoringPlugin("check_ftp"),
    MonitoringPlugin("check_host"),
    MonitoringPlugin("check_hpjd"),
    MonitoringPlugin("check_http"),
    MonitoringPlugin("check_icmp"),
    MonitoringPlugin("check_ide_smart"),
    MonitoringPlugin("check_imap"),
    MonitoringPlugin("check_jabber"),
    MonitoringPlugin("check_ldap"),
    MonitoringPlugin("check_ldaps"),
    MonitoringPlugin("check_load"),
    MonitoringPlugin("check_log"),
    MonitoringPlugin("check_mailq"),
    MonitoringPlugin("check_mrtg"),
    MonitoringPlugin("check_mrtgtraf"),
    MonitoringPlugin("check_nagios"),
    MonitoringPlugin("check_nntp"),
    MonitoringPlugin("check_nntps"),
    MonitoringPlugin("check_nt"),
    MonitoringPlugin("check_ntp"),
    MonitoringPlugin("check_ntp_peer"),
    MonitoringPlugin("check_ntp_time"),
    MonitoringPlugin("check_nwstat"),
    MonitoringPlugin("check_oracle"),
    MonitoringPlugin("check_overcr"),
    MonitoringPlugin("check_pgsql"),
    MonitoringPlugin("check_ping"),
    MonitoringPlugin("check_pop"),
    MonitoringPlugin("check_procs"),
    MonitoringPlugin("check_real"),
    MonitoringPlugin("check_rpc"),
    MonitoringPlugin("check_sensors"),
    MonitoringPlugin("check_simap"),
    MonitoringPlugin("check_smtp"),
    MonitoringPlugin("check_spop"),
    MonitoringPlugin("check_ssh"),
    MonitoringPlugin("check_ssmtp"),
    MonitoringPlugin("check_swap"),
    MonitoringPlugin("check_tcp"),
    MonitoringPlugin("check_time"),
    MonitoringPlugin("check_udp"),
    MonitoringPlugin("check_ups"),
    MonitoringPlugin("check_users"),
    MonitoringPlugin("check_wave"),
    MonitoringPlugin("negate"),
    MonitoringPlugin("urlize"),
    MonitoringPlugin("check_mysql"),
    MonitoringPlugin("check_mysql_query"),
    MonitoringPlugin("check_mkevents", cmd_line_option="", expected="OK - no events for "),
    MonitoringPlugin("check_nrpe", expected="Version: 3.2.1"),
    MonitoringPlugin("check_snmp"),
    CheckmkActiveCheck("check_always_crit", path="lib/nagios/plugins"),
    CheckmkActiveCheck("check_bi_aggr"),
    CheckmkActiveCheck("check_cmk_inv"),
    CheckmkActiveCheck("check_disk_smb"),
    CheckmkActiveCheck("check_elasticsearch_query"),
    CheckmkActiveCheck("check_form_submit"),
    CheckmkActiveCheck("check_httpv2", path="lib/nagios/plugins", usage_text="Usage"),
    CheckmkActiveCheck("check_mailboxes"),
    CheckmkActiveCheck("check_mail_loop"),
    CheckmkActiveCheck("check_mail"),
    CheckmkActiveCheck("check_notify_count"),
    CheckmkActiveCheck("check_sftp"),
    CheckmkActiveCheck("check_sql"),
    CheckmkActiveCheck("check_traceroute"),
    CheckmkActiveCheck("check_uniserv"),
)


SPECIAL_AGENTS = [
    SpecialAgent("agent_activemq"),
    SpecialAgent("agent_alertmanager"),
    SpecialAgent("agent_allnet_ip_sensoric"),
    SpecialAgent("agent_appdynamics"),
    SpecialAgent("agent_aws"),
    SpecialAgent("agent_aws_status"),
    SpecialAgent("agent_azure"),
    SpecialAgent("agent_azure_status"),
    SpecialAgent("agent_azure_v2"),
    SpecialAgent("agent_bazel_cache"),
    SpecialAgent("agent_bi"),
    SpecialAgent("agent_cisco_meraki"),
    SpecialAgent("agent_cisco_prime"),
    SpecialAgent("agent_couchbase"),
    SpecialAgent("agent_datadog"),
    SpecialAgent("agent_ddn_s2a"),
    SpecialAgent("agent_elasticsearch"),
    SpecialAgent("agent_fritzbox"),
    SpecialAgent("agent_gcp"),
    SpecialAgent("agent_gcp_status"),
    SpecialAgent("agent_gerrit"),
    SpecialAgent("agent_graylog"),
    SpecialAgent("agent_hivemanager"),
    SpecialAgent("agent_hivemanager_ng"),
    SpecialAgent("agent_hp_msa"),
    SpecialAgent("agent_ibmsvc"),
    SpecialAgent("agent_innovaphone"),
    SpecialAgent("agent_ipmi_sensors"),
    SpecialAgent("agent_jenkins"),
    SpecialAgent("agent_jira"),
    SpecialAgent("agent_jolokia"),
    SpecialAgent("agent_kube"),
    SpecialAgent("agent_custom_query_metric_backend"),
    SpecialAgent("agent_mobileiron"),
    SpecialAgent("agent_mqtt"),
    SpecialAgent("agent_netapp_ontap"),
    SpecialAgent("agent_otel"),
    SpecialAgent("agent_prism"),
    SpecialAgent("agent_prometheus"),
    SpecialAgent("agent_proxmox_ve"),
    SpecialAgent("agent_pure_storage_fa"),
    SpecialAgent("agent_rabbitmq"),
    SpecialAgent("agent_random"),
    SpecialAgent("agent_redfish"),
    SpecialAgent("agent_redfish_power"),
    SpecialAgent("agent_ruckus_spot"),
    SpecialAgent("agent_salesforce"),
    SpecialAgent("agent_siemens_plc"),
    SpecialAgent("agent_smb_share"),
    SpecialAgent("agent_splunk"),
    SpecialAgent("agent_storeonce"),
    SpecialAgent("agent_storeonce4x"),
    SpecialAgent("agent_three_par"),
    SpecialAgent("agent_tinkerforge", usage_text="Usage"),
    SpecialAgent("agent_ucs_bladecenter"),
    SpecialAgent("agent_vnx_quotas"),
    SpecialAgent("agent_vsphere"),
    SpecialAgent("agent_zerto"),
]

_SKIPPED_SPECIAL_AGENTS = {
    "agent_acme_sbc",  # has no help option
}

_ULTIMATE_AGENTS = {
    "agent_custom_query_metric_backend",
    "agent_otel",
}


@pytest.mark.medium_test_chain
@pytest.mark.parametrize(
    "plugin",
    (pytest.param(p, id=f"{p.binary_name}") for p in MONITORING_PLUGINS),
)
def test_monitoring_plugins_can_be_executed(plugin: Plugin, site: Site) -> None:
    """Validate the plugin's presence and version in the site."""
    if site.edition.is_cloud_edition() and plugin.binary_name == "check_mkevents":
        pytest.skip("check_mkevents is disabled in SaaS edition")

    cmd_line = [plugin.detect_full_path(site).as_posix(), plugin.cmd_line_option]
    # check=False; '<plugin-name> -V' returns in exit-code 3 for most plugins!
    process = site.run(cmd_line, check=False)
    assert plugin.expected in process.stdout, (
        f"Expected command:'{' '.join(cmd_line)}'\nto result in output having '{plugin.expected}'!"
    )
    assert not process.stderr


@pytest.mark.medium_test_chain
@pytest.mark.parametrize(
    "agent",
    (pytest.param(p, id=f"{p.binary_name}") for p in SPECIAL_AGENTS),
)
def test_special_agents_can_be_executed(agent: SpecialAgent, site: Site) -> None:
    """Validate the plugin's presence and version in the site."""
    if not site.edition.is_ultimate_edition() and agent.binary_name in _ULTIMATE_AGENTS:
        pytest.skip(f"{agent.binary_name} is disabled in this edition")

    cmd_line = [agent.detect_full_path(site).as_posix(), agent.cmd_line_option]
    process = site.run(cmd_line, check=False)
    assert agent.expected in process.stdout, (
        f"Expected command:'{' '.join(cmd_line)}'\nto result in output having '{agent.expected}'!"
    )
    assert not process.stderr


@pytest.mark.medium_test_chain
def test_monitoring_plugins_coverage(site: Site) -> None:
    """Make sure `MONITORING_PLUGINS` is up to date.

    If this fails, add the new plugin you added to the list above.
    """
    covered = {p.binary_name for p in MONITORING_PLUGINS}
    found = {f.split("/")[-1] for f in _find_libexec(site, "check_*").split("\n")}
    assert found <= covered


@pytest.mark.medium_test_chain
def test_special_agents_coverage(site: Site) -> None:
    """Make sure `SPECIAL_AGENTS` is up to date.

    If this fails, add the new special agent you added to the list above.
    """
    covered = {p.binary_name for p in SPECIAL_AGENTS} | _SKIPPED_SPECIAL_AGENTS
    found = {f.split("/")[-1] for f in _find_libexec(site, "agent_*").split("\n")}
    assert found <= covered


def _find_libexec(site: Site, search_pattern: str) -> str:
    return str(
        site.run(["find", "lib/", "-wholename", f"*/libexec/{search_pattern}"]).stdout
    ).strip()


@pytest.mark.medium_test_chain
def test_heirloommailx(site: Site) -> None:
    expected_version = "12.5"
    process = site.run(cmd := ["heirloom-mailx", "-V"])
    version = process.stdout if process.stdout else "<NO STDOUT>"
    # TODO: Sync this with a global version for heirloom (like we do it for python)
    assert expected_version in version, (
        f"Expected 'heirloom-mailx' version: {expected_version} in output! Command: "
        f"`{' '.join(cmd)}`"
    )


@pytest.mark.medium_test_chain
def test_heirloompkgtools_pkgmk(site: Site) -> None:
    process = site.run([tool := "pkgmk"], check=False)
    message = process.stderr if process.stderr else "<NO STDERR>"
    assert "pkgmk: ERROR: unable to find info for device <spool>" in message, (
        f"'{tool}' is not present in Checkmk '{site.version.version}'!"
    )


@pytest.mark.medium_test_chain
def test_heirloompkgtools_pkgtrans(site: Site) -> None:
    process = site.run([tool := "pkgtrans"], check=False)
    message = process.stderr if process.stderr else "<NO STDERR>"
    assert "usage: pkgtrans [-cinos] srcdev dstdev [pkg [pkg...]]" in message, (
        f"'{tool}' is not present in Checkmk '{site.version.version}'!"
    )


@pytest.mark.medium_test_chain
def test_stunnel(site: Site) -> None:
    expected_version = "5.63"
    process = site.run(cmd := ["stunnel", "-help"])
    help_text = process.stderr if process.stderr else "<EXPECTED ERROR; OBSERVED NO ERROR>"
    # TODO: Sync this with a global version for stunnel (like we do it for python)
    assert f"stunnel {expected_version}" in help_text, (
        f"Expected 'stunnel' version: {expected_version} in the output! Command: `{' '.join(cmd)}`"
    )


@pytest.mark.medium_test_chain
def test_unixcat(site: Site) -> None:
    tool = "unixcat"
    process = site.run([tool], check=False)
    message = process.stderr if process.stderr else "<NO STDERR>"
    assert "Usage: unixcat UNIX-socket" in message, (
        f"'{tool}' is not present in Checkmk '{site.version.version}'!"
    )


@pytest.mark.medium_test_chain
@pytest.mark.parametrize(
    "distro,expectation",
    (
        ("aix", "64-bit XCOFF executable or object modul"),
        ("solaris", "ELF 64-bit LSB executable, x86-64, version 1 (Solaris), dynamically linked"),
    ),
)
def test_mk_oracle_exotic_distros(distro: str, expectation: str, site: Site) -> None:
    process = site.run(
        ["file", f"lib/python3/cmk/plugins/oracle/agents/mk-oracle.{distro}"], check=False
    )
    assert expectation in process.stdout, process.stdout


@pytest.mark.medium_test_chain
def test_nrpe(site: Site) -> None:
    version = "3.2.1"
    process = site.run([tool := "lib/nagios/plugins/check_nrpe", "-V"], check=False)
    help_text = process.stdout if process.stdout else "<EXPECTED OUTPUT; OBSERVED NO OUTPUT>"
    # TODO: Sync this with a global version for nrpe (like we do it for python)
    assert f"Version: {version}" in help_text, f"Expected '{tool}' to have version: {version}!"
