#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Fire a monitoring command for a map object from the GUI.

The Maps GUI runs in a full Checkmk request context, so it issues host/service
commands the way Checkmk itself does (the monitoring-views command layer): via
``cmk.gui.livestatus_utils.commands`` and the ``cmk.livestatus_client`` command
classes, over ``sites.live()`` (the configured sites). This gives real RBAC
(``user.need_permission``) and routes through the same livestatus path as the
rest of the GUI — so the Flask-free Maps daemon no longer relays commands.

A command always targets a configured Checkmk site (resolved from the object's
``site_id`` or, for the verbs that look it up, the host identity). A map pointing
at a livestatus that is not a configured site is therefore view-only for
commands.
"""

import datetime as dt
from collections.abc import Callable, Mapping
from typing import override

from cmk.ccc.hostaddress import HostName, HostNameValidationError
from cmk.ccc.site import SiteId
from cmk.gui import sites
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.i18n import _
from cmk.gui.livestatus_utils.commands import acknowledgments, comment, downtimes, force_schedule
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.gui.utils.csrf_token import check_csrf_token
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

# Verbs Maps can issue — the single source of truth is the ticket permission map
# (the same verbs the GUI bakes into a ticket's capabilities). Deriving it here
# keeps the executable set and the granted set from drifting apart; an unknown
# action is still rejected rather than silently ignored.
_ACTIONS = frozenset(COMMAND_ACTION_PERMISSIONS)


def _require_str(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise MKUserError(key, _("Missing or invalid '%(key)s'.") % {"key": key})
    return value


def _require_host_name(payload: Mapping[str, object]) -> HostName:
    raw = _require_str(payload, "host_name")
    try:
        return HostName(raw)
    except HostNameValidationError:
        raise MKUserError("host_name", _("Invalid host name.")) from None


def _opt_str(payload: Mapping[str, object], key: str) -> str | None:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def _opt_service(payload: Mapping[str, object]) -> str | None:
    """The target service, or ``None`` for a host-level command.

    Absent/``null`` means "host", but an *empty* string is rejected rather than
    read as absent: this one value decides whether the command targets the service
    or its host, so a client sending ``""`` would silently acknowledge (or
    downtime) the host instead of the service.
    """
    if (value := payload.get("service_description")) is None:
        return None
    if not isinstance(value, str) or not value:
        raise MKUserError(
            "service_description",
            _("Missing or invalid '%(key)s'.") % {"key": "service_description"},
        )
    return value


def _bool(payload: Mapping[str, object], key: str, default: bool) -> bool:
    value = payload.get(key)
    return bool(value) if isinstance(value, bool) else default


def _opt_site(payload: Mapping[str, object]) -> SiteId | None:
    site = _opt_str(payload, "site_id")
    return SiteId(site) if site is not None else None


def _require_site(payload: Mapping[str, object]) -> SiteId:
    site = _opt_site(payload)
    if site is None:
        raise MKUserError("site_id", _("This command requires the object's site."))
    return site


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


def _epoch_to_datetime(payload: Mapping[str, object], key: str) -> dt.datetime:
    raw = payload.get(key)
    if not isinstance(raw, (int, float)) or isinstance(raw, bool) or raw <= 0:
        raise MKUserError(key, _("Missing or invalid '%(key)s'.") % {"key": key})
    # The instant is what matters; the command serialises back to epoch, so a
    # UTC-aware datetime round-trips to the same epoch the client sent. An
    # out-of-range epoch (fromtimestamp overflows time_t) is client input, not
    # a server fault, so it maps to the same MKUserError as a missing value.
    try:
        return dt.datetime.fromtimestamp(int(raw), tz=dt.UTC)
    except OverflowError, OSError, ValueError:
        raise MKUserError(key, _("Missing or invalid '%(key)s'.") % {"key": key})


# (service command, host command) per toggle verb. These verbs have no
# ``livestatus_utils`` helper; the views command layer builds the same
# ``cmk.livestatus_client`` command classes directly, so we do too.
_TOGGLE_COMMANDS: Mapping[
    str, tuple[Callable[[HostName, str], Command], Callable[[HostName], Command]]
] = {
    "enable_notifications": (EnableServiceNotifications, EnableHostNotifications),
    "disable_notifications": (DisableServiceNotifications, DisableHostNotifications),
    "enable_checks": (EnableServiceCheck, EnableHostCheck),
    "disable_checks": (DisableServiceCheck, DisableHostCheck),
}


def _toggle_command(action: str, host: HostName, service: str | None) -> Command:
    """Return the (notification|check)-toggle command for *action*.

    The permission is gated by the caller (like every other verb).
    """
    if (commands := _TOGGLE_COMMANDS.get(action)) is None:
        raise MKUserError("action", _("Unhandled toggle action '%(action)s'.") % {"action": action})
    service_command, host_command = commands
    return host_command(host) if service is None else service_command(host, service)


def run_map_command(payload: Mapping[str, object]) -> None:
    """Validate and execute one map-object command in the current request context."""
    action = _require_str(payload, "action")
    if action not in _ACTIONS:
        raise MKUserError("action", _("Unknown command '%(action)s'.") % {"action": action})

    host = _require_host_name(payload)
    service = _opt_service(payload)
    connection: MultiSiteConnection = sites.live()
    acting_user = user.ident
    comment_txt = _opt_str(payload, "comment") or ""

    # Authorize before issuing ANY command, the same way for every verb: the
    # per-verb permission (from the same map the ticket capabilities derive from)
    # gates the *capability*, the visibility check gates the *object*. Doing the
    # permission check here — rather than inside some match arms and via the
    # helpers' internal checks in others — is the single visible server-side RBAC
    # gate; no verb silently relies on a helper checking for it.
    user.need_permission(COMMAND_ACTION_PERMISSIONS[action])
    _require_target_visible(connection, host, service, _opt_site(payload))

    match action:
        case "acknowledge":
            sticky = _bool(payload, "sticky", True)
            notify = _bool(payload, "notify", True)
            persistent = _bool(payload, "persistent", False)
            if service is not None:
                acknowledgments.acknowledge_service_problem(
                    connection,
                    host,
                    service,
                    sticky=sticky,
                    notify=notify,
                    persistent=persistent,
                    user=acting_user,
                    comment=comment_txt,
                )
            else:
                acknowledgments.acknowledge_host_problem(
                    connection,
                    host,
                    sticky=sticky,
                    notify=notify,
                    persistent=persistent,
                    user=acting_user,
                    comment=comment_txt,
                )
        case "remove_acknowledgement":
            acknowledgments.remove_acknowledgement(
                connection, _require_site(payload), host, service
            )
        case "force_check":
            check_time = dt.datetime.now(tz=dt.UTC)
            # Route to the object's real site; without it a reschedule for a
            # remote host reaches the central core (which doesn't know the host)
            # and is silently dropped. Falls back to the local site when unset.
            site_id = _opt_site(payload)
            if service is not None:
                force_schedule.force_schedule_service_check(
                    connection, host, service, check_time, site_id
                )
            else:
                force_schedule.force_schedule_host_check(connection, host, check_time, site_id)
        case "schedule_downtime":
            start = _epoch_to_datetime(payload, "start_time")
            end = _epoch_to_datetime(payload, "end_time")
            if service is not None:
                downtimes.schedule_service_downtime(
                    connection,
                    _require_site(payload),
                    host,
                    service,
                    start,
                    end,
                    user_id=acting_user,
                    comment=comment_txt,
                )
            else:
                downtimes.schedule_host_downtime(
                    connection, host, start, end, user_id=acting_user, comment=comment_txt
                )
        case "add_comment":
            if not comment_txt:
                raise MKUserError("comment", _("A comment is required."))
            site_id = _require_site(payload)
            if service is not None:
                comment.add_service_comment(
                    connection, host, service, comment_txt, site_id, user=acting_user
                )
            else:
                comment.add_host_comment(connection, host, comment_txt, site_id, user=acting_user)
        case _:
            cmd = _toggle_command(action, host, service)
            LivestatusClient(connection).command(cmd, _require_site(payload))


class AjaxMapsCommand(AjaxPage):
    """Execute a host/service command for a map object via Checkmk's command layer."""

    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("maps.use")
        # State-changing POST: same CSRF guard as the save endpoint.
        check_csrf_token()
        api_request = ctx.request.get_request()
        run_map_command(api_request)
        return {"ok": True}
