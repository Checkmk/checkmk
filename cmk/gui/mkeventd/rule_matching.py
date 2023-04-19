#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import socket

import cmk.utils.paths

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.gui.config import active_config
from cmk.gui.i18n import _


# Rule matching for simulation. Yes - there is some hateful code duplication
# here. But it does not make sense to query the live eventd here since it
# does not know anything about the currently configured but not yet activated
# rules. And also we do not want to have shared code.
def event_rule_matches(
    rule: ec.Rule,
    event: ec.Event,
) -> ec.MatchResult:
    result = event_rule_matches_non_inverted(rule, event)
    if rule.get("invert_matching"):
        if isinstance(result, ec.MatchSuccess):
            return ec.MatchFailure(reason=_("The rule would match, but matching is inverted."))
        return ec.MatchSuccess(cancelling=False, match_groups=ec.MatchGroups())
    return result


def event_rule_matches_non_inverted(  # pylint: disable=too-many-branches
    rule: ec.Rule,
    event: ec.Event,
) -> ec.MatchResult:
    if not ec.match_ip_network(rule.get("match_ipaddress", "0.0.0.0/0"), event["ipaddress"]):
        return ec.MatchFailure(reason=_("The source IP address does not match."))

    if match(rule.get("match_host"), event["host"], complete=True) is False:
        return ec.MatchFailure(reason=_("The host name does not match."))

    if match(rule.get("match_application"), event["application"], complete=False) is False:
        return ec.MatchFailure(reason=_("The application (syslog tag) does not match"))

    if "match_facility" in rule and event["facility"] != rule["match_facility"]:
        return ec.MatchFailure(reason=_("The syslog facility does not match"))

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
            return ec.MatchSuccess(
                cancelling=True, match_groups=ec.MatchGroups(match_groups_message=match_groups)
            )

    try:
        match_groups = match(rule.get("match"), event["text"], complete=False)
    except Exception as e:
        return ec.MatchFailure(reason=_("Invalid regular expression: %s") % e)
    if match_groups is False:
        return ec.MatchFailure(reason=_("The message text does not match the required pattern."))

    if "match_priority" in rule:
        prio_from, prio_to = rule["match_priority"]
        if prio_from > prio_to:
            prio_to, prio_from = prio_from, prio_to
        p = event["priority"]
        if p < prio_from or p > prio_to:
            return ec.MatchFailure(reason=_("The syslog priority is not in the required range."))

    if "match_sl" in rule:
        sl_from, sl_to = rule["match_sl"]
        if sl_from > sl_to:
            sl_to, sl_from = sl_from, sl_to
        p = event.get("sl", 0)

        if p < sl_from or p > sl_to:
            return ec.MatchFailure(
                reason=_("Wrong service level %d (need %d..%d)") % (p, sl_from, sl_to)
            )

    if "match_timeperiod" in rule:
        reason = check_timeperiod(rule["match_timeperiod"])
        if reason:
            return ec.MatchFailure(reason)

    if match_groups is True:
        match_groups = ()  # no matching groups
    return ec.MatchSuccess(
        cancelling=False, match_groups=ec.MatchGroups(match_groups_message=match_groups)
    )


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


def match(pattern: ec.TextPattern, text: str, complete: bool = True) -> bool | ec.TextMatchResult:
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
