#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import socket
from typing import Any

import cmk.utils.paths
import cmk.utils.version as cmk_version

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui.config import active_config
from cmk.gui.i18n import _


# Rule matching for simulation. Yes - there is some hateful code duplication
# here. But it does not make sense to query the live eventd here since it
# does not know anything about the currently configured but not yet activated
# rules. And also we do not want to have shared code.
def event_rule_matches(
    rule_pack: ec.ECRulePack,
    rule: ec.Rule,
    event: dict[str, Any],
) -> str | tuple[bool, tuple]:
    result = event_rule_matches_non_inverted(rule_pack, rule, event)
    if rule.get("invert_matching"):
        if isinstance(result, tuple):
            return _("The rule would match, but matching is inverted.")
        return False, ()
    return result


def event_rule_matches_non_inverted(  # pylint: disable=too-many-branches
    rule_pack: ec.ECRulePack,
    rule: ec.Rule,
    event: dict[str, Any],
) -> str | tuple[bool, tuple]:
    if not ec.match_ipv4_network(rule.get("match_ipaddress", "0.0.0.0/0"), event["ipaddress"]):
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


def check_timeperiod(tpname: str) -> str | None:
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


def match(pattern: ec.TextPattern, text: str, complete: bool = True) -> bool | tuple:
    if pattern is None:
        return True
    assert not isinstance(pattern, re.Pattern)  # Hmmm...
    if complete:
        if not pattern.endswith("$"):
            pattern += "$"
        m = re.compile(pattern, re.IGNORECASE).match(text)
    else:
        m = re.compile(pattern, re.IGNORECASE).search(text)
    if m:
        return m.groups()
    return False
