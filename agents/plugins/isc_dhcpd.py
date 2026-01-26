#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.4.0p21"

# Monitor leases if ISC-DHCPD
import calendar
import os
import platform
import re
import sys
import time

conf_file = None
for path in [
    "/etc/dhcpd.conf",
    "/etc/dhcp/dhcpd.conf",
    "/var/dhcpd/etc/dhcpd.conf",
    "/usr/local/etc/dhcpd.conf",
]:
    if os.path.exists(path):
        conf_file = path
        break

leases_file = None
for path in [
    "/var/lib/dhcp/db/dhcpd.leases",
    "/var/lib/dhcp/dhcpd.leases",
    "/var/lib/dhcpd/dhcpd.leases",  # CentOS
    "/var/dhcpd/var/db/dhcpd.leases",  # OPNsense
]:
    if os.path.exists(path):
        leases_file = path
        break

# If no configuration and leases are found, we assume that
# no dhcpd is running.
if not conf_file or not leases_file:
    sys.exit(0)


def get_pid():
    cmd = "pidof dhcpd"

    if "debian-10" in platform.platform().lower():
        # workaround for bug in sysvinit-utils in debian buster
        # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=926896
        cmd = "ps aux | grep -w [d]hcpd | awk {'printf (\"%s \", $2)'}"

    if "freebsd" in platform.platform().lower():
        # workaround for freebsd
        cmd = "ps aux | grep -w \"[d]hcpd\" | awk '{print $2}'"

    # This produces a false warning in Bandit, claiming there was no failing test for this nosec.
    # The warning is a bug in Bandit: https://github.com/PyCQA/bandit/issues/942
    p = os.popen(cmd)  # nosec B605 # BNS:f6c1b9
    return p.read().strip()


pidof_dhcpd = get_pid()
sys.stdout.write("<<<isc_dhcpd>>>\n[general]\nPID: %s\n" % pidof_dhcpd)

sys.stdout.write("[pools]\n")


def parse_config(filename):
    with open(filename) as config_file:
        for l in config_file:
            line = l.strip()
            if line.startswith("include"):
                regex_result = re.search(r'include\s+"(.*)"', line)
                if regex_result:
                    included_file = regex_result.group(1)
                parse_config(included_file)
            elif line.startswith("range"):
                sys.stdout.write(line[5:].strip("\t ;") + "\n")


parse_config(conf_file)

# lease 10.1.1.81 {
#   starts 3 2015/09/09 11:42:20;
#   ends 3 2015/09/09 19:42:20;
#   tstp 3 2015/09/09 19:42:20;
#   cltt 3 2015/09/09 11:42:20;
#   binding state free;
#   hardware ethernet a4:5e:60:de:1f:c3;
#   uid "\001\244^`\336\037\303";
#   set ddns-txt = "318c69bae8aeae6f8c723e96de933c7149";
#   set ddns-fwd-name = "Sebastians-MBP.dhcp.mathias-kettner.de";
# }

sys.stdout.write("[leases]\n")
now = time.time()
ip_address = None
binding_state = None
seen_addresses = set()
with open(leases_file) as leases_file_obj:
    for lease_line in leases_file_obj:
        parts = lease_line.strip().rstrip(";").split()
        if not parts:
            continue

        if parts[0] == "lease":
            ip_address = parts[1]
        elif parts[0] == "ends":
            if parts[1] != "never":
                ends_date_string = parts[2] + " " + parts[3]
                ends_date = calendar.timegm(time.strptime(ends_date_string, "%Y/%m/%d %H:%M:%S"))
                if ends_date < now:
                    ip_address = None  # skip this address, this lease is outdated

        elif parts[0] == "binding" and parts[1] == "state":
            binding_state = parts[2]

        elif parts[0] == "}":
            if ip_address and binding_state == "active" and ip_address not in seen_addresses:
                sys.stdout.write("%s\n" % ip_address)
                seen_addresses.add(ip_address)
            ip_address = None
            binding_state = None
