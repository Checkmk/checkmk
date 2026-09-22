#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Fire the monitoring commands Checkmk's REST API does not offer for a map object.

Acknowledging, removing an acknowledgement, scheduling a downtime and commenting
go straight to Checkmk's own REST API, the same endpoints the SPA's bulk actions
use. What is left here has no such endpoint yet: rescheduling a check (the
Monitor family's reschedule does not check the target's visibility) and the
notification and active-check toggles.

They run the way the monitoring views run them, through the
``cmk.livestatus_client`` command classes over ``sites.live()`` (the configured
sites), in the caller's request context. A map pointing at a livestatus that is
not a configured site is therefore view-only for these commands.
"""

import datetime as dt
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.livestatus_utils.commands import force_schedule
from cmk.gui.logged_in import user
from cmk.livestatus_client import (
    Command,
    DisableHostCheck,
    DisableHostNotifications,
    DisableServiceCheck,
    DisableServiceNotifications,
    EnableHostCheck,
    EnableHostNotifications,
    EnableServiceCheck,
    EnableServiceNotifications,
    LivestatusClient,
    MultiSiteConnection,
)
from cmk.livestatus_client.expressions import And
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables.hosts import Hosts
from cmk.livestatus_client.tables.services import Services
from cmk.maps.gui._tickets import COMMAND_ACTION_PERMISSIONS

# The part of ``CommandVerb`` that is run here; the rest goes to the REST API.
# TODO: These belong into Checkmk's Monitor endpoint family (``cmk.gui.monitor``),
# next to its reschedule, which would first have to check the target's
# visibility. Once they exist there, the SPA calls them and this module goes.
type MapCommandVerb = Literal[
    "force_check",
    "enable_notifications",
    "disable_notifications",
    "enable_checks",
    "disable_checks",
]


@dataclass(frozen=True, kw_only=True)
class MapCommand:
    """One monitoring command for one map object."""

    action: MapCommandVerb
    host_name: HostName
    service_description: str | None = None
    site_id: SiteId | None = None


def _service(command: MapCommand) -> str | None:
    """The target service, or ``None`` for a host-level command.

    An absent service means "host", but an *empty* string is rejected rather
    than read as absent: this one value decides whether the command targets the
    service or its host, so a client sending ``""`` would silently act on the
    host instead of the service.
    """
    if command.service_description is None:
        return None
    if not command.service_description:
        raise MKUserError(
            "service_description",
            _("Missing or invalid '%(key)s'.") % {"key": "service_description"},
        )
    return command.service_description


def _require_site(command: MapCommand) -> SiteId:
    if command.site_id is None:
        raise MKUserError("site_id", _("This command requires the object's site."))
    return command.site_id


def _require_target_visible(
    connection: MultiSiteConnection,
    host: HostName,
    service: str | None,
    site_id: SiteId | None,
) -> None:
    """Reject commands on objects outside the user's contact-group visibility.

    The livestatus command pipe enforces no ACLs of its own, so ``need_permission``
    alone would let a user act on *any* host/service by POSTing its name — in
    Checkmk itself the command ACL restricts actions to visible objects. This
    mirrors the daemon's ``_require_target_visible`` and the implicit precheck the
    downtime/ack helpers already do: an auth-scoped livestatus query on the target
    returns nothing when it is not visible (see-all users run unscoped, so the
    lookup then only catches typos).
    """
    only_sites = [site_id] if site_id is not None else None
    if service is None:
        rows = Query([Hosts.name], Hosts.name.equals(host)).fetchall(connection, False, only_sites)
    else:
        rows = Query(
            [Services.description],
            And(Services.host_name.equals(host), Services.description.equals(service)),
        ).fetchall(connection, False, only_sites)
    if not rows:
        # Same wording as the helpers; do not leak whether the object exists.
        raise MKAuthException(_("Cannot find the requested resource."))


# (service command, host command) per toggle verb. These verbs have no
# ``livestatus_utils`` helper; the views command layer builds the same
# ``cmk.livestatus_client`` command classes directly, so we do too.
_TOGGLE_COMMANDS: Mapping[
    MapCommandVerb, tuple[Callable[[HostName, str], Command], Callable[[HostName], Command]]
] = {
    "enable_notifications": (EnableServiceNotifications, EnableHostNotifications),
    "disable_notifications": (DisableServiceNotifications, DisableHostNotifications),
    "enable_checks": (EnableServiceCheck, EnableHostCheck),
    "disable_checks": (DisableServiceCheck, DisableHostCheck),
}


def _toggle_command(action: MapCommandVerb, host: HostName, service: str | None) -> Command:
    """Return the (notification|check)-toggle command for *action*.

    The permission is gated by the caller (like every other verb).
    """
    if (commands := _TOGGLE_COMMANDS.get(action)) is None:
        raise MKUserError("action", _("Unhandled toggle action '%(action)s'.") % {"action": action})
    service_command, host_command = commands
    return host_command(host) if service is None else service_command(host, service)


def run_map_command(command: MapCommand) -> None:
    """Validate and execute one map-object command in the current request context."""
    host = command.host_name
    service = _service(command)

    # Authorize before issuing ANY command, the same way for every verb: the
    # views' command gate, then the per-verb permission (from the same map the
    # ticket capabilities derive from) for the *capability*, then the visibility
    # check for the *object*.
    user.need_permission("general.act")
    user.need_permission(COMMAND_ACTION_PERMISSIONS[command.action])
    connection: MultiSiteConnection = sites.live()
    _require_target_visible(connection, host, service, command.site_id)

    if command.action == "force_check":
        check_time = dt.datetime.now(tz=dt.UTC)
        # Route to the object's real site; without it a reschedule for a remote
        # host reaches the central core (which doesn't know the host) and is
        # silently dropped. Falls back to the local site when unset.
        if service is not None:
            force_schedule.force_schedule_service_check(
                connection, host, service, check_time, command.site_id
            )
        else:
            force_schedule.force_schedule_host_check(connection, host, check_time, command.site_id)
        return
    LivestatusClient(connection).command(
        _toggle_command(command.action, host, service), _require_site(command)
    )
