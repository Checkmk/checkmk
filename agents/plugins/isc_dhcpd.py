#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__version__ = "2.1.0b3"

# Monitor leases if ISC-DHCPD
import calendar
import os
import re
import sys
import time

conf_file = None
for path in ["/etc/dhcpd.conf", "/etc/dhcp/dhcpd.conf", "/usr/local/etc/dhcpd.conf"]:
    if os.path.exists(path):
        conf_file = path
        break

leases_file = None
for path in [
    "/var/lib/dhcp/db/dhcpd.leases",
    "/var/lib/dhcp/dhcpd.leases",
    "/var/lib/dhcpd/dhcpd.leases",  # CentOS
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

    # workaround for bug in sysvinit-utils in debian buster
    # https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=926896
    lsb_path = "/etc/lsb-release"
    if os.path.exists(lsb_path):
        with open(lsb_path) as lsb_file:
            for line in lsb_file:
                if "buster" in line:
                    cmd = "ps aux | grep -w [d]hcpd | awk {'printf (\"%s \", $2)'}"
                    break

    return os.popen(cmd).read().strip()  # nosec


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
