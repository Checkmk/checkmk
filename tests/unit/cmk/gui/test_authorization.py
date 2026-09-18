#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.authorization import Authorization, READ_PERMISSIONS, request_authorization
from cmk.gui.permissions import permission_registry
from cmk.gui.scopes import ScopeId
from cmk.gui.session import session


def test_unrestricted_permits_anything() -> None:
    assert Authorization.UNRESTRICTED.permits("wato.activate")
    assert Authorization.UNRESTRICTED.permits("a.permission.that.does.not.exist")


def test_unrestricted_rejects_an_allow_list() -> None:
    """The two would contradict each other, and permits() would silently ignore the list."""
    with pytest.raises(RuntimeError):
        Authorization(unrestricted=True, allowed_permissions=frozenset({"general.use"}))


def test_write_scope_permits_anything() -> None:
    write = Authorization.from_scopes({ScopeId.READ, ScopeId.WRITE})
    assert write.permits("wato.activate")
    assert write.permits("general.use")


def test_read_scope_permits_a_listed_read_permission() -> None:
    assert Authorization.from_scopes({ScopeId.READ}).permits("general.use")


def test_read_scope_denies_a_write_permission() -> None:
    read = Authorization.from_scopes({ScopeId.READ})
    assert not read.permits("wato.edit")
    assert not read.permits("wato.activate")
    # the write counterpart of the allow-listed wato.see_all_folders
    assert not read.permits("wato.all_folders")


def test_read_scope_denies_an_unknown_permission() -> None:
    assert not Authorization.from_scopes({ScopeId.READ}).permits("newsection.brand_new")


def test_read_permissions_are_registered() -> None:
    """Catches typos and entries left behind by a renamed permission."""
    unregistered = READ_PERMISSIONS - set(permission_registry)
    assert not unregistered, f"allowlist names no longer registered: {sorted(unregistered)}"


@pytest.mark.usefixtures("request_context")
def test_request_authorization_defaults_to_unrestricted() -> None:
    assert request_authorization() is Authorization.UNRESTRICTED


@pytest.mark.usefixtures("request_context")
def test_request_authorization_round_trips() -> None:
    read_only = Authorization.from_scopes({ScopeId.READ})
    session.authorization = read_only
    assert request_authorization() is read_only


def test_request_authorization_outside_request_context_is_unrestricted() -> None:
    """Background jobs, cron and CLI code run without a request and present no
    credential, so there is nothing that could restrict them."""
    assert request_authorization() is Authorization.UNRESTRICTED
