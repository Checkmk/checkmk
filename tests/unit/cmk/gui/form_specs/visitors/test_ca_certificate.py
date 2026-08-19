#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tests for the ``CACertificate`` form spec / visitor.

The stored value is the PEM text of a CA certificate or certificate chain, so
the visitor is a ``MultilineText`` one that additionally rejects text which is
not a loadable PEM. Whether the frontend may offer the "fetch from server"
button depends on the ``general.server_side_requests`` permission.
"""

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.form_specs.unstable import CACertificate
from cmk.gui.permissions import permission_registry
from cmk.gui.session_context import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.rulesets.v1 import Title
from cmk.shared_typing import vue_formspec_components as shared_type_defs

# Self signed test CA, valid until 2126.
CA_PEM = """-----BEGIN CERTIFICATE-----
MIIBezCCASGgAwIBAgIUDIcyg85XfQmA4RzNHo/JfB+j5AowCgYIKoZIzj0EAwIw
EjEQMA4GA1UEAwwHVGVzdCBDQTAgFw0yNjA4MTkwODI0MThaGA8yMTI2MDcyNjA4
MjQxOFowEjEQMA4GA1UEAwwHVGVzdCBDQTBZMBMGByqGSM49AgEGCCqGSM49AwEH
A0IABI4UJNAiwjKWK6rW3XnWnFdGTyBbDfIaZpXLqDrvEsx+pqhL0ShCE9FB1JjN
R2FHJXvxUztuLzXEZab8JkABfB2jUzBRMB0GA1UdDgQWBBSyGh6qYtVZJjGg7GSz
QVGa3DJkpjAfBgNVHSMEGDAWgBSyGh6qYtVZJjGg7GSzQVGa3DJkpjAPBgNVHRMB
Af8EBTADAQH/MAoGCCqGSM49BAMCA0gAMEUCIFiWceF954tCCPqV2KEJ6LMNl+Zb
W6UwWFko7ZZvNwLYAiEAyTjDYETA0XhtxzcXKyzGECbeZUHbZpYz2xJpZGuAzKw=
-----END CERTIFICATE-----
"""


@pytest.fixture(scope="module", name="spec")
def ca_certificate_spec() -> CACertificate:
    return CACertificate(title=Title("Certificate chain"))


def test_valid_pem_passes_validation(spec: CACertificate, request_context: None) -> None:
    assert (
        get_visitor(spec, VisitorOptions(migrate_values=False, mask_values=False)).validate(
            RawDiskData(CA_PEM)
        )
        == []
    )


def test_garbage_fails_validation(spec: CACertificate, request_context: None) -> None:
    messages = get_visitor(spec, VisitorOptions(migrate_values=False, mask_values=False)).validate(
        RawDiskData("this is not a certificate")
    )
    assert len(messages) == 1
    assert "Invalid certificate" in messages[0].message


def test_empty_value_fails_validation(spec: CACertificate, request_context: None) -> None:
    """An empty text area is not a certificate either - the element must not be
    stored empty, matching the ``allow_empty=False`` of the old valuespec."""
    messages = get_visitor(spec, VisitorOptions(migrate_values=False, mask_values=False)).validate(
        RawDiskData("")
    )
    assert len(messages) == 1


def _user_permissions(config: Config, user_id: UserId, role: str) -> UserPermissions:
    return UserPermissions(config.roles, permission_registry, {user_id: [role]}, [])


def test_to_vue_allows_fetch_for_permitted_user(
    spec: CACertificate,
    load_config: Config,
    with_admin: tuple[UserId, str],
) -> None:
    """Fetching a certificate needs "general.server_side_requests", a permission
    only admins hold by default."""
    with UserContext(with_admin[0], _user_permissions(load_config, with_admin[0], "admin")):
        vue_spec, value = get_visitor(
            spec, VisitorOptions(migrate_values=False, mask_values=False)
        ).to_vue(RawDiskData(CA_PEM))
    assert isinstance(vue_spec, shared_type_defs.CaCertificate)
    assert vue_spec.allow_fetch is True
    assert value == CA_PEM


def test_to_vue_hides_fetch_without_permission(
    spec: CACertificate,
    load_config: Config,
    with_user: tuple[UserId, str],
) -> None:
    with UserContext(with_user[0], _user_permissions(load_config, with_user[0], "user")):
        vue_spec, _value = get_visitor(
            spec, VisitorOptions(migrate_values=False, mask_values=False)
        ).to_vue(RawDiskData(CA_PEM))
    assert isinstance(vue_spec, shared_type_defs.CaCertificate)
    assert vue_spec.allow_fetch is False
