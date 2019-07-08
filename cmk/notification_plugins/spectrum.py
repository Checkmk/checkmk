# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import subprocess
import sys
from cmk.notification_plugins import utils

# Note: This script contains an example configuration
# You will probably have to modify the sent information


def send_trap(oids, target, community):
    cmd = [
        "/usr/bin/snmptrap", '-v', '1', '-c', community, target, "1.3.6.1.4.1.100.1.2.3",
        "172.25.221.23", "6", "1", "\"\""
    ]
    for oid, value in oids.items():
        # Feel free to add more types. Currently only Integer and Strings are supported
        oid_type = type(value)
        oid_id = 'i' if oid_type == int else 's'
        if oid_type in [str, unicode]:
            value = "\"%s\"" % value.replace("\"", " ")
        cmd += [oid, oid_id, "%s" % value]

    sys.stderr.write("%r" % cmd)
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    return p.wait()


def main():
    # gather all options from env
    context = utils.collect_context()

    # check if configured via flexible notifications
    if "PARAMETER_1" in context:
        context["PARAMETER_COMMUNITY"] = context["PARAMETER_1"]
        context["PARAMETER_DESTINATION"] = context["PARAMETER_2"]
        context["PARAMETER_BASEOID"] = context["PARAMETER_3"]

    base_oid = context.get("PARAMETER_BASEOID", "1.3.6.1.4.1.1234")

    # adjust these oids to your needs
    complete_url = "https://" + context["MONITORING_HOST"]
    if "OMD_SITE" in context:
        complete_url += "/" + context["OMD_SITE"]
    complete_url += context.get("SERVICEURL", context.get("HOSTURL"))

    oids = {
        base_oid + ".1": context['MONITORING_HOST'],
        base_oid + ".2": context['HOSTNAME'],
        base_oid + ".3": context['HOSTADDRESS'],
        base_oid + ".4": context.get('HOSTGROUPNAMES', ""),
        base_oid + ".5": context.get('SERVICEDESC', 'Connectivity'),
        base_oid + ".6": context.get('SERVICESTATE', context.get('HOSTSTATE')),
        base_oid + ".7": context.get('SERVICEOUTPUT', context.get("HOSTOUTPUT")),
        base_oid + ".8": "HARD",  # Notifications always are in HARDSTATE
        base_oid + ".9": context.get('SERVICEDESC', 'Connectivity'),
        base_oid + ".10": 3,  #SPECIFIC TRAP (type) NUMBER
        base_oid + ".11": "Call number 123456",  #CALLOUT STRING
        base_oid + ".12": complete_url,
        base_oid + ".13": "%s alarm on host %s" %
                          (context.get('SERVICEDESC', 'Connectivity'), context['HOSTNAME']),
        base_oid + ".14": context.get('SERVICEGROUPNAMES', ""),
    }

    sys.exit(send_trap(oids, context['PARAMETER_DESTINATION'], context['PARAMETER_COMMUNITY']))
