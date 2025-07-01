#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from tests.testlib.site import Site


@dataclass(frozen=True)
class MonitoringPlugin:
    """Data corresponding to 3rd party plugins.

    These plugins are maintained by 'Monitoring Plugins'
    (https://www.monitoring-plugins.org/).
    """

    binary_name: str
    path: str = "lib/nagios/plugins"
    # by default, output the version of the plugin
    cmd_line_option: str = "-V"
    expected: str = "v2.4.0"


@dataclass(frozen=True)
class CheckmkActiveCheck:
    """Data corresponding to Checkmk active checks."""

    binary_name: str
    path: str = "lib/nagios/plugins"
    usage_text: str = "usage"

    @property
    def cmd_line_option(self) -> str:
        return "-h"

    @property
    def expected(self) -> str:
        return f"{self.usage_text}: {self.binary_name} "


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
    CheckmkActiveCheck("check_always_crit"),
    CheckmkActiveCheck("check_bi_aggr", path="lib/python3/cmk/plugins/checkmk/libexec"),
    CheckmkActiveCheck("check_disk_smb", path="lib/python3/cmk/plugins/smb/libexec"),
    CheckmkActiveCheck(
        "check_elasticsearch_query",
        path="lib/python3/cmk/plugins/elasticsearch/libexec",
    ),
    CheckmkActiveCheck("check_form_submit", path="lib/python3/cmk/plugins/form_submit/libexec"),
    CheckmkActiveCheck("check_httpv2", usage_text="Usage"),
    CheckmkActiveCheck("check_mailboxes", path="lib/python3/cmk/plugins/emailchecks/libexec"),
    CheckmkActiveCheck("check_mail_loop", path="lib/python3/cmk/plugins/emailchecks/libexec"),
    CheckmkActiveCheck("check_mail", path="lib/python3/cmk/plugins/emailchecks/libexec"),
    CheckmkActiveCheck("check_notify_count", path="lib/python3/cmk/plugins/checkmk/libexec"),
    CheckmkActiveCheck("check_sftp", path="lib/python3/cmk/plugins/sftp/libexec"),
    CheckmkActiveCheck("check_sql", path="lib/python3/cmk/plugins/sql/libexec"),
    CheckmkActiveCheck("check_traceroute", path="lib/python3/cmk/plugins/traceroute/libexec"),
    CheckmkActiveCheck("check_uniserv", path="lib/python3/cmk/plugins/uniserv/libexec"),
)


@pytest.mark.parametrize(
    "plugin",
    (pytest.param(p, id=f"{p.binary_name}") for p in MONITORING_PLUGINS),
)
def test_monitoring_plugins_can_be_executed(plugin: Plugin, site: Site) -> None:
    """Validate the plugin's presence and version in the site."""

    cmd_line = [(site.root / plugin.path / plugin.binary_name).as_posix(), plugin.cmd_line_option]
    # check=False; '<plugin-name> -V' returns in exit-code 3 for most plugins!
    process = site.run(cmd_line, check=False)
    assert plugin.expected in process.stdout, (
        f"Expected command:'{' '.join(cmd_line)}'\nto result in output having '{plugin.expected}'!"
    )
    assert not process.stderr


def test_heirloommailx(site: Site) -> None:
    expected_version = "12.5"
    process = site.run(cmd := ["heirloom-mailx", "-V"])
    version = process.stdout if process.stdout else "<NO STDOUT>"
    # TODO: Sync this with a global version for heirloom (like we do it for python)
    assert expected_version in version, (
        f"Expected 'heirloom-mailx' version: {expected_version} in output! Command: "
        f"`{' '.join(cmd)}`"
    )


def test_heirloompkgtools_pkgmk(site: Site) -> None:
    process = site.run([tool := "pkgmk"], check=False)
    message = process.stderr if process.stderr else "<NO STDERR>"
    assert "pkgmk: ERROR: unable to find info for device <spool>" in message, (
        f"'{tool}' is not present in Checkmk '{site.version.version}'!"
    )


def test_heirloompkgtools_pkgtrans(site: Site) -> None:
    process = site.run([tool := "pkgtrans"], check=False)
    message = process.stderr if process.stderr else "<NO STDERR>"
    assert "usage: pkgtrans [-cinos] srcdev dstdev [pkg [pkg...]]" in message, (
        f"'{tool}' is not present in Checkmk '{site.version.version}'!"
    )


def test_stunnel(site: Site) -> None:
    expected_version = "5.63"
    process = site.run(cmd := ["stunnel", "-help"])
    help_text = process.stderr if process.stderr else "<EXPECTED ERROR; OBSERVED NO ERROR>"
    # TODO: Sync this with a global version for stunnel (like we do it for python)
    assert f"stunnel {expected_version}" in help_text, (
        f"Expected 'stunnel' version: {expected_version} in the output! Command: `{' '.join(cmd)}`"
    )


def test_unixcat(site: Site) -> None:
    tool = "unixcat"
    process = site.run([tool], check=False)
    message = process.stderr if process.stderr else "<NO STDERR>"
    assert "Usage: unixcat UNIX-socket" in message, (
        f"'{tool}' is not present in Checkmk '{site.version.version}'!"
    )


def test_navicli(site: Site) -> None:
    version = "7.33.9.1.84"
    process = site.run([tool := "naviseccli", "-Help"], check=False)
    help_text = process.stdout if process.stdout else "<EXPECTED OUTPUT; OBSERVED NO OUTPUT>"
    # TODO: Sync this with a global version for navicli (like we do it for python)
    assert f"Revision {version}" in help_text, f"Expected '{tool}' to have version: {version}!"


def test_nrpe(site: Site) -> None:
    version = "3.2.1"
    process = site.run([tool := "lib/nagios/plugins/check_nrpe", "-V"], check=False)
    help_text = process.stdout if process.stdout else "<EXPECTED OUTPUT; OBSERVED NO OUTPUT>"
    # TODO: Sync this with a global version for navicli (like we do it for python)
    assert f"Version: {version}" in help_text, f"Expected '{tool}' to have version: {version}!"
