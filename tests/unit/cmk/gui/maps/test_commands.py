#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Dispatch + authorization tests for the GUI map-object command endpoint.

``run_map_command`` is the GUI-side replacement for the daemon's command relay:
it routes each verb to Checkmk's own command layer (``livestatus_utils.commands``
/ the ``cmk.livestatus_client`` command classes) over ``sites.live()``, with real
``user.need_permission`` gating. The livestatus layer itself is mocked here; what
we pin is the validation, the verb→call routing, and the permission/site checks a
directly-reachable command endpoint must enforce.
"""

import contextlib
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.exceptions import MKAuthException, MKUserError
from cmk.gui.session_context import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.livestatus_client import DisableHostCheck, EnableServiceNotifications
from cmk.maps.gui import _commands
from cmk.maps.gui._tickets import COMMAND_ACTION_PERMISSIONS

_MODULE = "cmk.maps.gui._commands"


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
        "acknowledge_host_problem": f"{_MODULE}.acknowledgments.acknowledge_host_problem",
        "acknowledge_service_problem": f"{_MODULE}.acknowledgments.acknowledge_service_problem",
        "remove_acknowledgement": f"{_MODULE}.acknowledgments.remove_acknowledgement",
        "force_schedule_host_check": f"{_MODULE}.force_schedule.force_schedule_host_check",
        "schedule_host_downtime": f"{_MODULE}.downtimes.schedule_host_downtime",
        "add_host_comment": f"{_MODULE}.comment.add_host_comment",
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
    # Rejected before any connection/permission work.
    with pytest.raises(MKUserError):
        _commands.run_map_command({"action": "reboot", "host_name": "h1"})


def test_missing_host_is_rejected() -> None:
    with pytest.raises(MKUserError):
        _commands.run_map_command({"action": "acknowledge"})


def test_invalid_host_name_is_rejected() -> None:
    # A malformed host name must surface as MKUserError (400), not an uncaught
    # HostNameValidationError -> crash report. Rejected before any connection work.
    with pytest.raises(MKUserError):
        _commands.run_map_command({"action": "acknowledge", "host_name": "bad name"})


def test_acknowledge_host_routes_to_command_layer(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,
    commands: dict[str, MagicMock],
) -> None:
    uid = with_user[0]
    with _scoped(uid, "action.acknowledge"):
        _commands.run_map_command(
            {"action": "acknowledge", "host_name": "h1", "comment": "boom", "sticky": True}
        )
    commands["acknowledge_host_problem"].assert_called_once()
    args, kwargs = commands["acknowledge_host_problem"].call_args
    assert args[0] is live
    assert args[1] == "h1"
    assert kwargs["comment"] == "boom"
    assert kwargs["user"] == uid


def test_acknowledge_service_routes_to_service_command(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],
) -> None:
    with _scoped(with_user[0], "action.acknowledge"):
        _commands.run_map_command(
            {
                "action": "acknowledge",
                "host_name": "h1",
                "service_description": "CPU",
                "comment": "x",
            }
        )
    commands["acknowledge_service_problem"].assert_called_once()
    commands["acknowledge_host_problem"].assert_not_called()


def test_disable_checks_toggle_sends_command_with_site(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,
    commands: dict[str, MagicMock],
) -> None:
    uid = with_user[0]
    with _scoped(uid, "action.enablechecks"):
        _commands.run_map_command({"action": "disable_checks", "host_name": "h1", "site_id": "s1"})
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
    with _scoped(with_user[0], "action.notifications"):
        _commands.run_map_command(
            {
                "action": "enable_notifications",
                "host_name": "h1",
                "service_description": "CPU",
                "site_id": "s1",
            }
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
        _commands.run_map_command({"action": "disable_checks", "host_name": "h1", "site_id": "s1"})
    commands["LivestatusClient"].return_value.command.assert_not_called()


def test_toggle_without_site_is_rejected(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],  # noqa: ARG001
) -> None:
    with _scoped(with_user[0], "action.enablechecks"), pytest.raises(MKUserError):
        _commands.run_map_command({"action": "disable_checks", "host_name": "h1"})


def test_remove_acknowledgement_requires_site(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],  # noqa: ARG001
) -> None:
    with _scoped(with_user[0], "action.acknowledge"), pytest.raises(MKUserError):
        _commands.run_map_command({"action": "remove_acknowledgement", "host_name": "h1"})


def test_add_comment_requires_comment_text(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],  # noqa: ARG001
) -> None:
    with _scoped(with_user[0], "action.addcomment"), pytest.raises(MKUserError):
        _commands.run_map_command(
            {"action": "add_comment", "host_name": "h1", "site_id": "s1", "comment": ""}
        )


@pytest.mark.parametrize("payload", [{}, {"service_description": "CPU"}])
def test_invisible_target_is_rejected(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    monkeypatch: pytest.MonkeyPatch,
    payload: dict[str, str],
) -> None:
    """A target outside the user's contact-group scope is rejected before any
    command is sent, even with the verb permission granted (authz bypass guard)."""
    query = MagicMock(name="Query")
    query.return_value.fetchall.return_value = []  # target not visible to the user
    monkeypatch.setattr(f"{_MODULE}.Query", query)
    sent = MagicMock(name="LivestatusClient")
    monkeypatch.setattr(f"{_MODULE}.LivestatusClient", sent)
    with _scoped(with_user[0], "action.enablechecks"), pytest.raises(MKAuthException):
        _commands.run_map_command(
            {"action": "disable_checks", "host_name": "h1", "site_id": "s1", **payload}
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
    absent would acknowledge the host instead of the service.
    """
    with _scoped(with_user[0], "action.acknowledge"), pytest.raises(MKUserError):
        _commands.run_map_command(
            {
                "action": "acknowledge",
                "host_name": "h1",
                "service_description": "",
                "comment": "c",
            }
        )
    commands["acknowledge_host_problem"].assert_not_called()


@pytest.mark.parametrize("action", sorted(_commands._ACTIONS))  # noqa: SLF001
def test_every_granted_verb_is_dispatchable(
    request_context: None,  # noqa: ARG001
    with_user: tuple[UserId, str],
    live: MagicMock,  # noqa: ARG001
    commands: dict[str, MagicMock],
    action: str,
) -> None:
    """Every verb the ticket may grant must reach a command, not a dead branch.

    ``_ACTIONS`` (and the ticket's ``commands`` capability) are both derived from
    ``COMMAND_ACTION_PERMISSIONS``, so adding a verb there advertises it to the
    SPA. Without this test, a verb without a dispatch arm would only fail at the
    end of the ``match`` — for the user, a command that vanishes.
    """
    payload = {
        "action": action,
        "host_name": "h1",
        "site_id": "s1",
        "comment": "c",
        "start_time": 1_700_000_000,
        "end_time": 1_700_003_600,
    }
    with _scoped(with_user[0], COMMAND_ACTION_PERMISSIONS[action]):
        _commands.run_map_command(payload)
    dispatched = any(
        stub.called for name, stub in commands.items() if name != "_require_target_visible"
    )
    assert dispatched, f"{action} reached no command"


@pytest.mark.parametrize("raw", [1e300, 10**20, -5, 0, "not-a-number", True])
def test_epoch_to_datetime_rejects_invalid_input(raw: object) -> None:
    # Regression: an out-of-range epoch (fromtimestamp overflows time_t) must
    # surface as MKUserError, not an uncaught OverflowError / crash report.
    with pytest.raises(MKUserError):
        _commands._epoch_to_datetime({"start_time": raw}, "start_time")  # noqa: SLF001


def test_epoch_to_datetime_accepts_valid_epoch() -> None:
    assert _commands._epoch_to_datetime({"start_time": 1_700_000_000}, "start_time").year == 2023  # noqa: SLF001
