#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation
from cmk.gui.i18n import _, _l

syslog_priorities: Sequence[tuple[int, str]] = list(ec.SyslogPriority.NAMES.items())
syslog_facilities: Sequence[tuple[int, str]] = list(ec.SyslogFacility.NAMES.items())

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
