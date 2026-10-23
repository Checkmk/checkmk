#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

"""Server-side authorization gates for maps as pagetypes.

The edit/delete escalation surface is the pagetype authorization itself
(``MapPage.may_edit``/``may_delete``), which the list, save and delete endpoints
delegate to: built-ins are read-only, own maps need the create/edit permission,
foreign maps need the explicit "edit/delete foreign maps" permissions.
``_authorized_public`` decides who may publish a map (and to which groups/sites).
The client cannot be trusted to self-limit, so these must clamp server-side.
``gather_capabilities`` resolves the per-user flags baked into a ticket — the UI
only shows what they permit.
"""

from cmk.ccc.user import UserId
from cmk.gui.logged_in import user as global_user
from cmk.gui.session_context import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.maps.gui._pages import _authorized_public
from cmk.maps.gui._tickets import gather_capabilities
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.type_defs import map_config_from_spec


def _map(owner: str) -> MapPage:
    return MapPage(map_config_from_spec(UserId(owner), "m", {"view": {"type": "static"}}))


def test_admin_may_edit_and_delete_own_and_foreign_but_not_builtin(
    request_context: None, with_admin_login: UserId
) -> None:
    own = _map(str(with_admin_login))
    assert own.may_edit() and own.may_delete()
    foreign = _map("another-owner")
    assert foreign.may_edit() and foreign.may_delete()
    builtin = _map("")
    assert not builtin.may_edit() and not builtin.may_delete()


def test_scoped_user_cannot_edit_or_delete_foreign(
    request_context: None, with_user: tuple[UserId, str]
) -> None:
    uid = with_user[0]
    with UserContext(
        uid, UserPermissions({}, {}, {}, []), explicit_permissions={"general.edit_map"}
    ):
        own = _map(str(uid))
        assert own.may_edit() and own.may_delete()
        foreign = _map("another-owner")
        assert not foreign.may_edit() and not foreign.may_delete()


def test_without_edit_permission_own_map_is_read_only(
    request_context: None, with_user: tuple[UserId, str]
) -> None:
    uid = with_user[0]
    with UserContext(uid, UserPermissions({}, {}, {}, [])):
        own = _map(str(uid))
        assert not own.may_edit() and not own.may_delete()


def test_authorized_public_admin_may_publish_all(
    request_context: None, with_admin_login: UserId
) -> None:
    assert _authorized_public(True) is True


def test_authorized_public_clamps_group_user_cannot_publish_to(
    request_context: None, with_admin_login: UserId
) -> None:
    # A contact group the user isn't authorized for is dropped; with nothing
    # left, the map stays private rather than leaking to that group.
    assert _authorized_public(("contact_groups", ["nonexistent-group"])) is False


def test_authorized_public_rejects_malformed_request(
    request_context: None, with_admin_login: UserId
) -> None:
    assert _authorized_public(42) is False


def test_authorized_public_empty_scope_list_is_private(
    request_context: None, with_admin_login: UserId
) -> None:
    # A scope tuple with no names leaves nothing to publish to -> private, never
    # a (scope, []) that the daemon/UI might misread as "shared".
    assert _authorized_public(("contact_groups", [])) is False
    assert _authorized_public(("sites", [])) is False


def test_authorized_public_rejects_unknown_scope(
    request_context: None, with_admin_login: UserId
) -> None:
    # Only contact_groups / sites are valid publish scopes; anything else (e.g. a
    # crafted "roles" scope) must clamp to private rather than be honoured.
    assert _authorized_public(("roles", ["admin"])) is False


def test_authorized_public_is_private_without_publish_permission(
    request_context: None, with_user: tuple[UserId, str]
) -> None:
    # A user who may edit but not publish cannot make a map public by crafting the
    # request: the publish gate clamps even an explicit ``True`` to private.
    uid = with_user[0]
    with UserContext(
        uid, UserPermissions({}, {}, {}, []), explicit_permissions={"general.edit_map"}
    ):
        assert _authorized_public(True) is False
        assert _authorized_public(("contact_groups", ["all"])) is False


def test_gather_capabilities_reflects_only_granted_permissions(
    request_context: None, with_user: tuple[UserId, str]
) -> None:
    uid = with_user[0]
    with UserContext(
        uid, UserPermissions({}, {}, {}, []), explicit_permissions={"general.edit_map"}
    ):
        caps = gather_capabilities(global_user)
    assert caps["may_edit"] is True
    assert caps["configure"] is False
    assert caps["commands"] == []
