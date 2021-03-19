#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import pytest  # type: ignore[import]


@pytest.mark.parametrize("plugin", [
    "check_apt",
    "check_bi_aggr",
    "check_breeze",
    "check_by_ssh",
    "check_clamd",
    "check_cluster",
    "check_cpu_peaks",
    "check_dhcp",
    "check_dig",
    "check_disk",
    "check_disk_smb",
    "check_dns",
    "check_dummy",
    "check_file_age",
    "check_flexlm",
    "check_form_submit",
    "check_ftp",
    "check_host",
    "check_hpjd",
    "check_http",
    "check_icmp",
    "check_ide_smart",
    "check_ifoperstatus",
    "check_ifstatus",
    "check_imap",
    "check_ircd",
    "check_jabber",
    "check_jmx4perl",
    "check_ldap",
    "check_ldaps",
    "check_load",
    "check_log",
    "check_mail",
    "check_mailboxes",
    "check_mail_loop",
    "check_mailq",
    "check_mkevents",
    "check_mrtg",
    "check_mrtgtraf",
    "check_mysql",
    "check_mysql_health",
    "check_mysql_query",
    "check_nagios",
    "check_nntp",
    "check_nntps",
    "check_notify_count",
    "check_nrpe",
    "check_nt",
    "check_ntp",
    "check_ntp_peer",
    "check_ntp_time",
    "check_nwstat",
    "check_oracle",
    "check_oracle_health",
    "check_overcr",
    "check_pgsql",
    "check_ping",
    "check_pop",
    "check_procs",
    "check_real",
    "check_rpc",
    "check_sensors",
    "check_sftp",
    "check_simap",
    "check_smtp",
    "check_snmp",
    "check_spop",
    "check_sql",
    "check_ssh",
    "check_ssmtp",
    "check_swap",
    "check_tcp",
    "check_time",
    "check_traceroute",
    "check_udp",
    "check_uniserv",
    "check_ups",
    "check_users",
    "check_wave",
    "check_webinject",
    "negate",
    "urlize",
    "utils.pm",
    "utils.sh",
])
def test_monitoring_plugins(site, plugin):
    # TODO: Extend use of our own postgres library to make this plugin compile again
    if (plugin == "check_pgsql" and os.path.exists("/etc/redhat-release") and
            "CentOS release 6" in open("/etc/redhat-release").read()):
        raise pytest.skip("Temporarily disabled during py3 migration")

    plugin_path = site.path(os.path.join("lib/nagios/plugins", plugin))
    assert os.path.exists(plugin_path)
    assert os.access(plugin_path, os.X_OK)
