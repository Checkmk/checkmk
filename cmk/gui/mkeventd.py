#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import re
import socket
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import livestatus
from livestatus import SiteId

import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

import cmk.gui.sites as sites
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKGeneralException
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _, _l
from cmk.gui.permissions import PermissionSection
from cmk.gui.valuespec import DropdownChoiceEntries


def _socket_path() -> Path:
    return cmk.utils.paths.omd_root / "tmp/run/mkeventd/status"


def mib_upload_dir() -> Path:
    return cmk.utils.paths.local_mib_dir


def mib_dirs() -> List[Tuple[Path, str]]:
    # ASN1 MIB source directory candidates. Non existing dirs are ok.
    return [
        (mib_upload_dir(), _("Custom MIBs")),
        (cmk.utils.paths.mib_dir, _("MIBs shipped with Checkmk")),
        (Path("/usr/share/snmp/mibs"), _("System MIBs")),
    ]


syslog_priorities: DropdownChoiceEntries = [
    (0, "emerg"),
    (1, "alert"),
    (2, "crit"),
    (3, "err"),
    (4, "warning"),
    (5, "notice"),
    (6, "info"),
    (7, "debug"),
]

syslog_facilities: DropdownChoiceEntries = [
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
    "counting": _("counting"),
    "delayed": _("delayed"),
    "open": _("open"),
    "ack": _("acknowledged"),
    "closed": _("closed"),
}

action_whats = {
    "ORPHANED": _l("Event deleted in counting state because rule was deleted."),
    "NOCOUNT": _l("Event deleted in counting state because rule does not count anymore"),
    "DELAYOVER": _l(
        "Event opened because the delay time has elapsed before cancelling event arrived."
    ),
    "EXPIRED": _l("Event deleted because its livetime expired"),
    "COUNTREACHED": _l("Event deleted because required count had been reached"),
    "COUNTFAILED": _l("Event created by required count was not reached in time"),
    "UPDATE": _l("Event information updated by user"),
    "NEW": _l("New event created"),
    "DELETE": _l("Event deleted manually by user"),
    "EMAIL": _l("Email sent"),
    "SCRIPT": _l("Script executed"),
    "CANCELLED": _l("The event was cancelled because the corresponding OK message was received"),
    "ARCHIVED": _l(
        "Event was archived because no rule matched and archiving is activated in global settings."
    ),
    "AUTODELETE": _l("Event was deleted automatically"),
    "CHANGESTATE": _l("State of event changed by user"),
}


class PermissionSectionEventConsole(PermissionSection):
    @property
    def name(self) -> str:
        return "mkeventd"

    @property
    def title(self) -> str:
        return _("Event Console")


def service_levels():
    return active_config.mkeventd_service_levels


def action_choices(omit_hidden=False) -> List[Tuple[str, str]]:
    # The possible actions are configured in mkeventd.mk,
    # not in multisite.mk (like the service levels). That
    # way we have not direct access to them but need
    # to load them from the configuration.
    return [("@NOTIFY", _("Send monitoring notification"))] + [
        (a["id"], a["title"])
        for a in _eventd_configuration().get("actions", [])
        if not omit_hidden or not a.get("hidden")
    ]


@request_memoize()
def _eventd_configuration() -> ec.ConfigFromWATO:
    return ec.load_config(
        ec.settings("", cmk.utils.paths.omd_root, Path(cmk.utils.paths.default_config_dir), [""])
    )


def daemon_running() -> bool:
    return _socket_path().exists()


def send_event(event) -> str:
    syslog_message_str = repr(
        ec.SyslogMessage(
            facility=event["facility"],
            severity=event["priority"],
            timestamp=time.time(),
            host_name=event["host"],
            application=event["application"],
            text=event["text"],
            ip_address=event["ipaddress"],
            service_level=event["sl"],
        )
    )

    execute_command("CREATE", [syslog_message_str], site=event["site"])

    return syslog_message_str


def get_local_ec_status():
    response = livestatus.LocalConnection().query("GET eventconsolestatus")
    if len(response) == 1:
        return None  # In case the EC is not running, there may be some
    return dict(zip(response[0], response[1]))


def replication_mode():
    try:
        status = get_local_ec_status()
        if not status:
            return "stopped"
        return status["status_replication_slavemode"]
    except livestatus.MKLivestatusSocketError:
        return "stopped"


# Only use this for master/slave replication. For status queries use livestatus
def query_ec_directly(query):
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(active_config.mkeventd_connect_timeout)
        sock.connect(str(_socket_path()))
        sock.sendall(query)
        sock.shutdown(socket.SHUT_WR)

        response_text = b""
        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return ast.literal_eval(response_text.decode())
    except SyntaxError:
        raise MKGeneralException(
            _("Invalid response from event daemon: " "<pre>%s</pre>") % response_text
        )

    except Exception as e:
        raise MKGeneralException(
            _("Cannot connect to event daemon via %s: %s") % (_socket_path(), e)
        )


def execute_command(
    name: str, args: Optional[List[str]] = None, site: Optional[SiteId] = None
) -> None:
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
    total_stats: Dict[str, float] = {}
    for row in stats_per_site:
        for key, value in row.items():
            if key.endswith("rate"):
                total_stats.setdefault(key, 0.0)
                total_stats[key] += value
    if not total_stats:
        if only_sites is None:
            raise MKGeneralException(_("Got no data from any site"))
        raise MKGeneralException(_("Got no data from this site"))

    for row in stats_per_site:
        for time_key, in_relation_to in [
            ("status_average_processing_time", "status_average_message_rate"),
            ("status_average_request_time", "status_average_connect_rate"),
        ]:
            total_stats.setdefault(time_key, 0.0)
            if total_stats[in_relation_to]:  # avoid division by zero
                my_weight = (
                    row[in_relation_to] / total_stats[in_relation_to]
                )  # fixed: true-division
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
        # Do not mark the site as dead in case the Event Console is not available.
        query = livestatus.Query(
            "GET eventconsolestatus\nColumns: %s" % " ".join(stats_keys),
            suppress_exceptions=(
                livestatus.MKLivestatusTableNotFoundError,
                livestatus.MKLivestatusBadGatewayError,
            ),
        )
        for list_row in sites.live().query(query):
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
        if match_groups is not False and cp:
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

    if cmk_version.is_managed_edition():
        import cmk.gui.cme.managed as managed  # pylint: disable=no-name-in-module,import-outside-toplevel

        if "customer" in rule_pack:
            rule_customer_id = rule_pack["customer"]
        else:
            rule_customer_id = rule.get("customer", managed.SCOPE_GLOBAL)

        site_customer_id = managed.get_customer_id(active_config.sites[event["site"]])

        if rule_customer_id not in (managed.SCOPE_GLOBAL, site_customer_id):
            return _("Wrong customer")

    if match_groups is True:
        match_groups = ()  # no matching groups
    return False, match_groups


def check_timeperiod(tpname):
    try:
        livesock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        livesock.connect(cmk.utils.paths.livestatus_unix_socket)
        livesock.send(("GET timeperiods\nFilter: name = %s\nColumns: in\n" % tpname).encode())
        livesock.shutdown(socket.SHUT_WR)
        answer = livesock.recv(100).strip()
        if answer == b"":
            return _("The timeperiod %s is not known to the local monitoring core") % tpname
        if int(answer) == 0:
            return _("The timeperiod %s is currently not active") % tpname
        return None
    except Exception as e:
        if active_config.debug:
            raise
        return _("Cannot update timeperiod information for %s: %s") % (tpname, e)


def match(pattern, text, complete=True):
    if pattern is None:
        return True
    if complete:
        if not pattern.endswith("$"):
            pattern += "$"
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
    parts = tuple(map(int, text.split(".")))
    return (parts[0] << 24) + (parts[1] << 16) + (parts[2] << 8) + parts[3]


def parse_ipv4_network(text):
    if "/" not in text:
        return parse_ipv4_address(text), 32

    network_text, bits_text = text.split("/")
    return parse_ipv4_address(network_text), int(bits_text)
