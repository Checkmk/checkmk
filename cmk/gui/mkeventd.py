#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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

from __future__ import division
import ast
import re
import socket
import time
import os
from pathlib2 import Path
import livestatus

import cmk.utils.paths
import cmk.ec.settings
import cmk.ec.export
import cmk.utils.store
import cmk.utils

import cmk.gui.config as config
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.permissions import (
    permission_section_registry,
    PermissionSection,
)

# ASN1 MIB source directory candidates. Non existing dirs are ok.
# Please sync these paths with htdocs/mkeventd.py
mib_dirs = [('/usr/share/snmp/mibs', 'System MIBs')]

socket_path = cmk.utils.paths.omd_root + "/tmp/run/mkeventd/status"
compiled_mibs_dir = cmk.utils.paths.omd_root + "/local/share/check_mk/compiled_mibs"

# Please sync these paths with htdocs/mkeventd.py
mib_upload_dir = cmk.utils.paths.omd_root + "/local/share/snmp/mibs"
mib_dirs.insert(0, (cmk.utils.paths.omd_root + "/share/snmp/mibs", 'MIBs shipped with Check_MK'))
mib_dirs.insert(0, (mib_upload_dir, 'Custom MIBs'))

syslog_priorities = [
    (0, "emerg"),
    (1, "alert"),
    (2, "crit"),
    (3, "err"),
    (4, "warning"),
    (5, "notice"),
    (6, "info"),
    (7, "debug"),
]

syslog_facilities = [
    (0, "kern"),
    (1, "user"),
    (2, "mail"),
    (3, "daemon"),
    (4, "auth"),
    (5, "syslog"),
    (6, "lpr"),
    (7, "news"),
    (8, "uucp"),
    (9, "cron"),
    (10, "authpriv"),
    (11, "ftp"),
    (12, "(12: unused)"),
    (13, "(13: unused)"),
    (14, "(14: unused)"),
    (15, "(15: unused)"),
    (16, "local0"),
    (17, "local1"),
    (18, "local2"),
    (19, "local3"),
    (20, "local4"),
    (21, "local5"),
    (22, "local6"),
    (23, "local7"),
    (31, "snmptrap"),
]

phase_names = {
    'counting': _("counting"),
    'delayed': _("delayed"),
    'open': _("open"),
    'ack': _("acknowledged"),
    'closed': _("closed"),
}

action_whats = {
    "ORPHANED": _("Event deleted in counting state because rule was deleted."),
    "NOCOUNT": _("Event deleted in counting state because rule does not count anymore"),
    "DELAYOVER":
        _("Event opened because the delay time has elapsed before cancelling event arrived."),
    "EXPIRED": _("Event deleted because its livetime expired"),
    "COUNTREACHED": _("Event deleted because required count had been reached"),
    "COUNTFAILED": _("Event created by required count was not reached in time"),
    "UPDATE": _("Event information updated by user"),
    "NEW": _("New event created"),
    "DELETE": _("Event deleted manually by user"),
    "EMAIL": _("Email sent"),
    "SCRIPT": _("Script executed"),
    "CANCELLED": _("The event was cancelled because the corresponding OK message was received"),
    "ARCHIVED": _(
        "Event was archived because no rule matched and archiving is activated in global settings."
    ),
    "AUTODELETE": _("Event was deleted automatically"),
    "CHANGESTATE": _("State of event changed by user"),
}


@permission_section_registry.register
class PermissionSectionEventConsole(PermissionSection):
    @property
    def name(self):
        return "mkeventd"

    @property
    def title(self):
        return _("Event Console")


def service_levels():
    return config.mkeventd_service_levels


def action_choices(omit_hidden=False):
    # The possible actions are configured in mkeventd.mk,
    # not in multisite.mk (like the service levels). That
    # way we have not direct access to them but need
    # to load them from the configuration.
    return [ ( "@NOTIFY", _("Send monitoring notification")) ] + \
           [ (a["id"], a["title"])
             for a in eventd_configuration().get("actions", [])
             if not omit_hidden or not a.get("hidden") ]


cached_config = None


def eventd_configuration():
    global cached_config
    if cached_config and cached_config[0] is html:
        return cached_config[1]

    settings = cmk.ec.settings.settings('', Path(cmk.utils.paths.omd_root),
                                        Path(cmk.utils.paths.default_config_dir), [''])
    cfg = cmk.ec.export.load_config(settings)
    cached_config = (html, cfg)
    return cfg


def daemon_running():
    return os.path.exists(socket_path)


# Note: in order to be able to simulate an original IP address
# we put hostname|ipaddress into the host name field. The EC
# recognizes this and unpacks the data correctly.
def send_event(event):
    # "<%PRI%>@%TIMESTAMP%;%SL% %HOSTNAME% %syslogtag% %msg%\n"
    prio = (event["facility"] << 3) + event["priority"]

    rfc = [
        "<%d>@%d" % (prio, int(time.time())),
        "%d %s|%s %s: %s\n" %
        (event["sl"], event["host"], event["ipaddress"], event["application"], event["text"]),
    ]

    execute_command("CREATE", map(cmk.utils.make_utf8, rfc), site=event["site"])

    return ";".join(rfc)


def get_local_ec_status():
    response = livestatus.LocalConnection().query("GET eventconsolestatus")
    return dict(zip(response[0], response[1]))


def replication_mode():
    try:
        status = get_local_ec_status()
        return status["status_replication_slavemode"]
    except livestatus.MKLivestatusSocketError:
        return "stopped"


# Only use this for master/slave replication. For status queries use livestatus
def query_ec_directly(query):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(config.mkeventd_connect_timeout)
        sock.connect(socket_path)
        sock.sendall(query)
        sock.shutdown(socket.SHUT_WR)

        response_text = ""
        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return ast.literal_eval(response_text)
    except SyntaxError as e:
        raise MKGeneralException(
            _("Invalid response from event daemon: "
              "<pre>%s</pre>") % response_text)

    except Exception as e:
        raise MKGeneralException(_("Cannot connect to event daemon via %s: %s") % (socket_path, e))


def execute_command(name, args=None, site=None):
    if args:
        formated_args = ";" + ";".join(args)
    else:
        formated_args = ""

    query = "[%d] EC_%s%s" % (int(time.time()), name, formated_args)
    sites.live().command(query, site)


def get_total_stats(only_sites):
    stats_keys = [
        "status_average_message_rate",
        "status_average_rule_trie_rate",
        "status_average_rule_hit_rate",
        "status_average_event_rate",
        "status_average_connect_rate",
        "status_average_overflow_rate",
        "status_average_rule_trie_rate",
        "status_average_rule_hit_rate",
        "status_average_processing_time",
        "status_average_request_time",
        "status_average_sync_time",
    ]

    stats_per_site = list(get_stats_per_site(only_sites, stats_keys))

    # First simply add rates. Times must then be averaged
    # weighted by message rate or connect rate
    total_stats = {}
    for row in stats_per_site:
        for key, value in row.items():
            if key.endswith("rate"):
                total_stats.setdefault(key, 0.0)
                total_stats[key] += value
    if not total_stats:
        if only_sites is None:
            raise MKGeneralException(_("Got no data from any site"))
        else:
            raise MKGeneralException(_("Got no data from this site"))

    for row in stats_per_site:
        for time_key, in_relation_to in [
            ("status_average_processing_time", "status_average_message_rate"),
            ("status_average_request_time", "status_average_connect_rate"),
        ]:
            total_stats.setdefault(time_key, 0.0)
            if total_stats[in_relation_to]:  # avoid division by zero
                my_weight = row[in_relation_to] / total_stats[
                    in_relation_to]  # fixed: true-division
                total_stats[time_key] += my_weight * row[time_key]

    total_sync_time = 0.0
    count = 0
    for row in stats_per_site:
        if row["status_average_sync_time"] > 0.0:
            count += 1
            total_sync_time += row["status_average_sync_time"]

    if count > 0:
        total_stats["status_average_sync_time"] = total_sync_time / count  # fixed: true-division

    return total_stats


def get_stats_per_site(only_sites, stats_keys):
    try:
        sites.live().set_only_sites(only_sites)
        for list_row in sites.live().query("GET eventconsolestatus\nColumns: %s" %
                                           " ".join(stats_keys)):
            yield dict(zip(stats_keys, list_row))
    finally:
        sites.live().set_only_sites(None)


# Rule matching for simulation. Yes - there is some hateful code duplication
# here. But it does not make sense to query the live eventd here since it
# does not know anything about the currently configured but not yet activated
# rules. And also we do not want to have shared code.
def event_rule_matches(rule_pack, rule, event):
    result = event_rule_matches_non_inverted(rule_pack, rule, event)
    if rule.get("invert_matching"):
        if isinstance(result, tuple):
            return _("The rule would match, but matching is inverted.")
        return False, ()
    return result


def event_rule_matches_non_inverted(rule_pack, rule, event):
    if not match_ipv4_network(rule.get("match_ipaddress", "0.0.0.0/0"), event["ipaddress"]):
        return _("The source IP address does not match.")

    if match(rule.get("match_host"), event["host"], complete=True) is False:
        return _("The host name does not match.")

    if match(rule.get("match_application"), event["application"], complete=False) is False:
        return _("The application (syslog tag) does not match")

    if "match_facility" in rule and event["facility"] != rule["match_facility"]:
        return _("The syslog facility does not match")

    # First try cancelling rules
    if "match_ok" in rule or "cancel_priority" in rule:
        if "cancel_priority" in rule:
            up, lo = rule["cancel_priority"]
            cp = event["priority"] >= lo and event["priority"] <= up
        else:
            cp = True

        match_groups = match(rule.get("match_ok", ""), event["text"], complete=False)
        if match_groups != False and cp:
            if match_groups is True:
                match_groups = ()
            return True, match_groups

    try:
        match_groups = match(rule.get("match"), event["text"], complete=False)
    except Exception as e:
        return _("Invalid regular expression: %s") % e
    if match_groups is False:
        return _("The message text does not match the required pattern.")

    if "match_priority" in rule:
        prio_from, prio_to = rule["match_priority"]
        if prio_from > prio_to:
            prio_to, prio_from = prio_from, prio_to
        p = event["priority"]
        if p < prio_from or p > prio_to:
            return _("The syslog priority is not in the required range.")

    if "match_sl" in rule:
        sl_from, sl_to = rule["match_sl"]
        if sl_from > sl_to:
            sl_to, sl_from = sl_from, sl_to
        p = event.get("sl")
        if p is None:
            return _("No service level is set in event")

        if p < sl_from or p > sl_to:
            return _("Wrong service level %d (need %d..%d)") % (p, sl_from, sl_to)

    if "match_timeperiod" in rule:
        reason = check_timeperiod(rule["match_timeperiod"])
        if reason:
            return reason

    if cmk.is_managed_edition():
        import cmk.gui.cme.managed as managed
        if "customer" in rule_pack:
            rule_customer_id = rule_pack["customer"]
        else:
            rule_customer_id = rule.get("customer", managed.SCOPE_GLOBAL)

        site_customer_id = managed.get_customer_id(config.sites[event["site"]])

        if rule_customer_id != managed.SCOPE_GLOBAL and site_customer_id != rule_customer_id:
            return _("Wrong customer")

    if match_groups is True:
        match_groups = ()  # no matching groups
    return False, match_groups


def check_timeperiod(tpname):
    try:
        livesock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        livesock.connect(cmk.utils.paths.livestatus_unix_socket)
        livesock.send("GET timeperiods\nFilter: name = %s\nColumns: in\n" % tpname)
        livesock.shutdown(socket.SHUT_WR)
        answer = livesock.recv(100).strip()
        if answer == "":
            return _("The timeperiod %s is not known to the local monitoring core") % tpname
        elif int(answer) == 0:
            return _("The timeperiod %s is currently not active") % tpname
    except Exception as e:
        if config.debug:
            raise
        return _("Cannot update timeperiod information for %s: %s") % (tpname, e)


def match(pattern, text, complete=True):
    if pattern is None:
        return True
    else:
        if complete:
            if not pattern.endswith("$"):
                pattern += '$'
            m = re.compile(pattern, re.IGNORECASE).match(text)
        else:
            m = re.compile(pattern, re.IGNORECASE).search(text)
        if m:
            return m.groups()
        return False


def match_ipv4_network(pattern, ipaddress_text):
    network, network_bits = parse_ipv4_network(pattern)  # is validated by valuespec
    if network_bits == 0:
        return True  # event if ipaddress is empty
    try:
        ipaddress = parse_ipv4_address(ipaddress_text)
    except Exception:
        return False  # invalid address never matches

    # first network_bits of network and ipaddress must be
    # identical. Create a bitmask.
    bitmask = 0
    for n in range(32):
        bitmask = bitmask << 1
        if n < network_bits:
            bit = 1
        else:
            bit = 0
        bitmask += bit

    return (network & bitmask) == (ipaddress & bitmask)


def parse_ipv4_address(text):
    parts = map(int, text.split("."))
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]


def parse_ipv4_network(text):
    if "/" not in text:
        return parse_ipv4_address(text), 32

    network_text, bits_text = text.split("/")
    return parse_ipv4_address(network_text), int(bits_text)
