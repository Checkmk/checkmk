#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Dispatch + authorization tests for the map-object command endpoint.

``run_map_command`` runs the verbs Checkmk's REST API does not offer through
Checkmk's own command layer (``livestatus_utils.commands`` / the
``cmk.livestatus_client`` command classes) over ``sites.live()``, with real
``user.need_permission`` gating. The livestatus layer itself is mocked here; what
we pin is the request model's own rejections, the verb→call routing, and the
permission/site checks a directly-reachable command endpoint must enforce.
"""

import contextlib
from collections.abc import Iterator
from typing import get_args
from unittest.mock import MagicMock

import pytest
from pydantic import TypeAdapter, ValidationError

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.logged_in import user
from cmk.gui.session_context import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.livestatus_client import DisableHostCheck, EnableServiceNotifications
from cmk.maps.gui import _commands
from cmk.maps.gui._commands import MapCommand, MapCommandVerb
from cmk.maps.gui._tickets import COMMAND_ACTION_PERMISSIONS, gather_capabilities
from cmk.maps.rest_api.internal.models.request_models import MapsCommandRequest
from cmk.maps.shared.ticket import CommandVerb

_MODULE = "cmk.maps.gui._commands"

_REQUEST_MODEL: TypeAdapter[MapsCommandRequest] = TypeAdapter(MapsCommandRequest)


def _parse_request(**fields: object) -> MapsCommandRequest:
    """One request as it arrives on the wire, through the endpoint's own model."""
    return _REQUEST_MODEL.validate_python(fields)


@pytest.fixture
def live(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """Stub ``sites.live()`` so no real livestatus connection is needed."""
    connection = MagicMock(name="MultiSiteConnection")
    monkeypatch.setattr(f"{_MODULE}.sites.live", lambda: connection)
    return connection


@pytest.fixture
def commands(monkeypatch: pytest.MonkeyPatch) -> dict[str, MagicMock]:
    """Replace the command-layer entry points with recording mocks.

    Also stubs ``_require_target_visible`` to a no-op so these routing/permission
    tests exercise the intended path; the visibility gate itself is pinned
    separately in :func:`test_invisible_target_is_rejected`.
    """
    targets = {
        "force_schedule_host_check": f"{_MODULE}.force_schedule.force_schedule_host_check",
        "force_schedule_service_check": f"{_MODULE}.force_schedule.force_schedule_service_check",
        "LivestatusClient": f"{_MODULE}.LivestatusClient",
        "_require_target_visible": f"{_MODULE}._require_target_visible",
    }
    stubs: dict[str, MagicMock] = {}
    for name, target in targets.items():
        stub = MagicMock(name=name)
        monkeypatch.setattr(target, stub)
        stubs[name] = stub
    return stubs


@contextlib.contextmanager
def _scoped(uid: UserId, *perms: str) -> Iterator[None]:
    with UserContext(uid, UserPermissions({}, {}, {}, []), explicit_permissions=set(perms)):
        yield


def test_unknown_action_is_rejected() -> None:
    # The verb set is the model's, so an unknown one never reaches a connection.
    with pytest.raises(ValidationError):
        _parse_request(action="reboot", host_name=HostName("h1"))


def test_missing_host_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _parse_request(action="force_check")


def test_invalid_host_name_is_rejected() -> None:
    # A malformed host name is a 400 from the request model, not an uncaught
    # HostNameValidationError -> crash report.
    with pytest.raises(ValidationError):
        _parse_request(action="force_check", host_name="bad name")


def test_the_ticket_grants_exactly_the_verbs_the_permissions_map_gates() -> None:
    """The ticket must not grant a verb nothing authorises, or hide one.

    ``COMMAND_ACTION_PERMISSIONS`` is where a verb is mapped to its Checkmk
    permission; the ``CommandVerb`` literal is what the generated OpenAPI (and
    from it the SPA) sees.
    """
    assert set(get_args(CommandVerb.__value__)) == set(COMMAND_ACTION_PERMISSIONS)


def test_a_verb_the_rest_api_offers_is_rejected() -> None:
    # Acknowledging goes to Checkmk's own endpoint, so this one refuses it.
    with pytest.raises(ValidationError):
        _parse_request(action="acknowledge", host_name=HostName("h1"))


def test_the_ticket_grants_no_command_without_the_command_gate(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
) -> None:
    with _scoped(with_user[0], *COMMAND_ACTION_PERMISSIONS.values()):
        assert gather_capabilities(user)["commands"] == []


def test_a_command_without_the_command_gate_is_forbidden(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],
) -> None:
    # The views refuse every command without ``general.act``, so this does too.
    with _scoped(with_user[0], "action.reschedule"), pytest.raises(MKAuthException):
        _commands.run_map_command(MapCommand(action="force_check", host_name=HostName("h1")))
    commands["force_schedule_host_check"].assert_not_called()


def test_disable_checks_toggle_sends_command_with_site(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,
    commands: dict[str, MagicMock],
) -> None:
    uid = with_user[0]
    with _scoped(uid, "general.act", "action.enablechecks"):
        _commands.run_map_command(
            MapCommand(action="disable_checks", host_name=HostName("h1"), site_id=SiteId("s1"))
        )
    commands["LivestatusClient"].assert_called_once_with(live)
    sent_cmd, sent_site = commands["LivestatusClient"].return_value.command.call_args.args
    assert sent_cmd == DisableHostCheck(host_name=HostName("h1"))
    assert sent_site == SiteId("s1")


def test_enable_notifications_service_uses_service_command(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],
) -> None:
    with _scoped(with_user[0], "general.act", "action.notifications"):
        _commands.run_map_command(
            MapCommand(
                action="enable_notifications",
                host_name=HostName("h1"),
                service_description="CPU",
                site_id=SiteId("s1"),
            )
        )
    sent_cmd, _site = commands["LivestatusClient"].return_value.command.call_args.args
    assert sent_cmd == EnableServiceNotifications(host_name=HostName("h1"), description="CPU")


def test_toggle_without_permission_is_forbidden(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],
) -> None:
    # No action.enablechecks granted -> need_permission raises.
    with _scoped(with_user[0]), pytest.raises(MKAuthException):
        _commands.run_map_command(
            MapCommand(action="disable_checks", host_name=HostName("h1"), site_id=SiteId("s1"))
        )
    commands["LivestatusClient"].return_value.command.assert_not_called()


def test_toggle_without_site_is_rejected(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],  # noqa: ARG001
) -> None:
    with _scoped(with_user[0], "general.act", "action.enablechecks"), pytest.raises(MKUserError):
        _commands.run_map_command(MapCommand(action="disable_checks", host_name=HostName("h1")))


@pytest.mark.parametrize("service", [None, "CPU"])
def test_invisible_target_is_rejected(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
    service: str | None,
) -> None:
    """A target outside the user's contact-group scope is rejected before any
    command is sent, even with the verb permission granted (authz bypass guard)."""
    query = MagicMock(name="Query")
    query.return_value.fetchall.return_value = []  # target not visible to the user
    monkeypatch.setattr(f"{_MODULE}.Query", query)
    sent = MagicMock(name="LivestatusClient")
    monkeypatch.setattr(f"{_MODULE}.LivestatusClient", sent)
    with (
        _scoped(with_user[0], "general.act", "action.enablechecks"),
        pytest.raises(MKAuthException),
    ):
        _commands.run_map_command(
            MapCommand(
                action="disable_checks",
                host_name=HostName("h1"),
                site_id=SiteId("s1"),
                service_description=service,
            )
        )
    sent.return_value.command.assert_not_called()


def test_empty_service_description_is_rejected(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],
) -> None:
    """An empty service must not silently downgrade to the *host* command.

    ``service_description`` is what decides host vs. service, so treating "" as
    absent would reschedule the host instead of the service.
    """
    with _scoped(with_user[0], "general.act", "action.reschedule"), pytest.raises(MKUserError):
        _commands.run_map_command(
            MapCommand(action="force_check", host_name=HostName("h1"), service_description="")
        )
    commands["force_schedule_host_check"].assert_not_called()


@pytest.mark.parametrize("action", sorted(get_args(MapCommandVerb.__value__)))
def test_every_verb_is_dispatchable(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],
    action: MapCommandVerb,
) -> None:
    """Every verb the request model accepts must reach a command, not a dead branch."""
    with _scoped(with_user[0], "general.act", COMMAND_ACTION_PERMISSIONS[action]):
        _commands.run_map_command(
            MapCommand(action=action, host_name=HostName("h1"), site_id=SiteId("s1"))
        )
    dispatched = any(
        stub.called for name, stub in commands.items() if name != "_require_target_visible"
    )
    assert dispatched, f"{action} reached no command"


def test_a_site_the_caller_may_not_see_is_rejected(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
) -> None:
    """The site is validated against what the caller may see, not just against
    the configured set: ``should_exist`` would let a restricted user enumerate
    the sites they are not authorized for (werks 18993, 18994)."""
    with _scoped(with_user[0], "action.reschedule"), pytest.raises(ValidationError):
        _parse_request(action="force_check", host_name="h1", site_id="no-such-site")
