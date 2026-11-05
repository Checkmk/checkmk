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
from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.gui.config import Config
from cmk.gui.form_specs import get_visitor, RawDiskData, VisitorOptions
from cmk.gui.form_specs.unstable import CACertificate, CACertificates
from cmk.gui.permissions import all_permissions
from cmk.gui.session_context import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue
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


@pytest.mark.usefixtures("request_context")
def test_valid_pem_passes_validation(spec: CACertificate) -> None:
    assert (
        get_visitor(spec, VisitorOptions(migrate_values=False, mask_values=False)).validate(
            RawDiskData(CA_PEM)
        )
        == []
    )


@pytest.mark.usefixtures("request_context")
def test_garbage_fails_validation(spec: CACertificate) -> None:
    messages = get_visitor(spec, VisitorOptions(migrate_values=False, mask_values=False)).validate(
        RawDiskData("this is not a certificate")
    )
    assert len(messages) == 1
    assert "Invalid certificate" in messages[0].message


@pytest.mark.usefixtures("request_context")
def test_empty_value_fails_validation(spec: CACertificate) -> None:
    """An empty text area is not a certificate either - the element must not be
    stored empty, matching the ``allow_empty=False`` of the old valuespec."""
    messages = get_visitor(spec, VisitorOptions(migrate_values=False, mask_values=False)).validate(
        RawDiskData("")
    )
    assert len(messages) == 1


def _user_permissions(config: Config, user_id: UserId, role: str) -> UserPermissions:
    return UserPermissions(
        config.roles,
        all_permissions(),
        {user_id: [role]},
        [],
    )


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


def _list_spec(pems: list[str], element: CACertificate) -> shared_type_defs.FormSpec:
    spec, _value = get_visitor(
        CACertificates(element_template=element, prefill=DefaultValue([])),
        VisitorOptions(migrate_values=False, mask_values=False),
    ).to_vue(RawDiskData(pems))
    return spec


@pytest.mark.usefixtures("request_context")
def test_a_list_of_certificates_summarizes_each_certificate(spec: CACertificate) -> None:
    list_spec = _list_spec([CA_PEM], spec)
    assert isinstance(list_spec, shared_type_defs.List) and list_spec.element_summaries == [
        shared_type_defs.ValueSummary(
            value=CA_PEM,
            label=None,
            detail_groups=[
                [
                    shared_type_defs.ValueSummaryDetail(title="Subject", text="CN=Test CA"),
                    shared_type_defs.ValueSummaryDetail(title="Issuer", text="CN=Test CA"),
                    shared_type_defs.ValueSummaryDetail(
                        title="Validity", text="2026-08-19 to 2126-07-26"
                    ),
                    shared_type_defs.ValueSummaryDetail(
                        title="Fingerprint",
                        text="7C:19:13:DA:71:2D:2E:20:E9:F7:4B:46:A6:8B:AB:48:76:C6:A2:DF:12:43:"
                        "21:16:F7:85:B5:DE:55:97:FA:37",
                    ),
                ]
            ],
        )
    ]


@pytest.mark.usefixtures("request_context")
def test_a_certificate_chain_is_summarized_per_certificate(spec: CACertificate) -> None:
    second_ca = (
        CertificateWithPrivateKey.generate_self_signed(
            common_name="Second CA", organization="test", key_size=1024
        )
        .certificate.dump_pem()
        .str
    )
    list_spec = _list_spec([CA_PEM + second_ca], spec)
    assert isinstance(list_spec, shared_type_defs.List) and [
        details[0].text
        for summary in list_spec.element_summaries or []
        for details in summary.detail_groups
    ] == ["CN=Test CA", "O=test,CN=Second CA"]


@pytest.mark.usefixtures("request_context")
def test_an_unreadable_certificate_is_summarized_as_such(spec: CACertificate) -> None:
    list_spec = _list_spec(["not a certificate"], spec)
    assert isinstance(list_spec, shared_type_defs.List) and list_spec.element_summaries == [
        shared_type_defs.ValueSummary(
            value="not a certificate",
            label=None,
            detail_groups=[
                [shared_type_defs.ValueSummaryDetail(title="Certificate", text="Unreadable")]
            ],
        )
    ]
