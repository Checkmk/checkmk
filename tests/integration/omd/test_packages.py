#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import subprocess
from dataclasses import dataclass
from typing import Literal

import pytest

from tests.testlib.pytest_helpers.calls import abort_if_not_containerized
from tests.testlib.site import Site

StreamType = Literal["stderr", "stdout"]


@dataclass
class MonitoringPlugin:
    binary_name: str
    stream: StreamType = "stdout"
    cmd_line_option: str = "-V"
    expected: str = "v2.3.3"

    def __post_init__(self):
        self.path = f"lib/nagios/plugins/{self.binary_name}"


# Not all plugins have the same cmd_line options nor using the same stream...
MONITORING_PLUGINS = (
    MonitoringPlugin("check_apt"),
    MonitoringPlugin("check_breeze"),
    MonitoringPlugin("check_by_ssh"),
    MonitoringPlugin("check_clamd"),
    MonitoringPlugin("check_cluster"),
    MonitoringPlugin("check_dhcp"),
    MonitoringPlugin("check_dig"),
    MonitoringPlugin("check_disk"),
    MonitoringPlugin("check_disk_smb"),
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
    MonitoringPlugin("check_ircd"),
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
    MonitoringPlugin(
        "check_sftp",
        stream="stderr",
        cmd_line_option="-h",
        expected="USAGE: check_sftp",
    ),
    MonitoringPlugin(
        "check_mail",
        cmd_line_option="-h",
        expected="usage: check_mail",
    ),
    MonitoringPlugin(
        "check_mailboxes",
        cmd_line_option="-h",
        expected="usage: check_mailboxes",
    ),
    MonitoringPlugin(
        "check_mail_loop",
        cmd_line_option="-h",
        expected="usage: check_mail_loop",
    ),
    MonitoringPlugin(
        "check_form_submit",
        cmd_line_option="-h",
        expected="usage: check_form_submit",
    ),
    MonitoringPlugin(
        "check_mkevents",
        cmd_line_option="",
        expected="OK - no events for ",
    ),
    MonitoringPlugin(
        "check_nrpe",
        expected="Version: 3.2.1",
    ),
    MonitoringPlugin(
        "check_sql",
        cmd_line_option="-h",
        expected="usage: check_sql",
    ),
    MonitoringPlugin(
        "check_snmp",
        cmd_line_option="-h",
    ),
    MonitoringPlugin(
        "check_notify_count",
        stream="stderr",
        cmd_line_option="-h",
        expected="USAGE: check_notify_count",
    ),
    MonitoringPlugin(
        "check_traceroute",
        cmd_line_option="-h",
        expected="check_traceroute",
    ),
    MonitoringPlugin(
        "check_uniserv",
        cmd_line_option="-h",
        expected="Usage: check_uniserv",
    ),
    MonitoringPlugin(
        "check_bi_aggr",
        stream="stderr",
        cmd_line_option="-h",
        expected="USAGE: check_bi_aggr",
    ),
)


@pytest.mark.parametrize(
    "cmd_line,stream_type,expected",
    (
        pytest.param([p.path, p.cmd_line_option], p.stream, p.expected, id=f"{p.binary_name}")
        for p in MONITORING_PLUGINS
    ),
)
def test_monitoring_plugins_can_be_executed(
    cmd_line: list[str],
    expected: str,
    stream_type: StreamType,
    site: Site,
) -> None:
    abort_if_not_containerized("check_mysql" in cmd_line[0])

    cmd_line[0] = f"{site.root}/{cmd_line[0]}"

    p = site.execute(cmd_line, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stream = {"stdout": p.stdout, "stderr": p.stderr}[stream_type]

    actual = stream.read() if stream else ""
    assert expected in actual


def test_heirloommailx(site: Site) -> None:
    p = site.execute(["heirloom-mailx", "-V"], stdout=subprocess.PIPE)
    version = p.stdout.read() if p.stdout else "<NO STDOUT>"
    # TODO: Sync this with a global version for heirloom (like we do it for python)
    assert "12.5" in version


def test_stunnel(site: Site) -> None:
    p = site.execute(["stunnel", "-help"], stderr=subprocess.PIPE)
    help_text = p.stderr.read() if p.stderr else ""
    # TODO: Sync this with a global version for stunnel (like we do it for python)
    assert "stunnel 5.63" in help_text
