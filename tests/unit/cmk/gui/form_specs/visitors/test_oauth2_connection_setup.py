#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from unittest import mock

import pytest

from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.form_specs import (
    get_visitor,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.form_specs.unstable.oauth2_connection_setup import OAuth2ConnectionSetup
from cmk.gui.form_specs.visitors.single_choice import SingleChoiceVisitor
from cmk.gui.oauth2_connections.wato import _modes as oauth2_modes
from cmk.gui.session import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.rulesets.v1.form_specs import CascadingSingleChoice
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from tests.unit.cmk.gui.users import create_and_destroy_user


def test_oauth2_connection_setup_to_disk(
    monkeypatch: pytest.MonkeyPatch,
    request_context: None,
    with_user: tuple[UserId, str],
) -> None:
    monkeypatch.setattr(oauth2_modes, "get_configured_site_choices", lambda: [])
    user_id = with_user[0]
    with UserContext(user_id, UserPermissions({}, {}, {}, [])):
        visitor = get_visitor(
            OAuth2ConnectionSetup(connector_type="microsoft_entra_id"),
            VisitorOptions(migrate_values=True, mask_values=False),
        )
        assert visitor.to_disk(
            RawFrontendData(
                value={
                    "ident": "my_ident",
                    "title": "my_title",
                    "authority": SingleChoiceVisitor.option_id("global"),
                    "tenant_id": "my_tenant",
                    "client_id": "my_client",
                    "client_secret": ("explicit_password", "", "my_secret", False),
                    "sites": ("all", None),
                }
            )
        ) == {
            "ident": "my_ident",
            "title": "my_title",
            "authority": "global",
            "tenant_id": "my_tenant",
            "client_id": "my_client",
            "client_secret": ("cmk_postprocessed", "explicit_password", (mock.ANY, "my_secret")),
            "sites": ("all", None),
        }


def test_oauth2_connection_setup_to_disk_with_proxy(
    monkeypatch: pytest.MonkeyPatch,
    request_context: None,
    with_user: tuple[UserId, str],
) -> None:
    monkeypatch.setattr(oauth2_modes, "get_configured_site_choices", list)
    user_id = with_user[0]
    with UserContext(user_id, UserPermissions({}, {}, {}, [])):
        visitor = get_visitor(
            OAuth2ConnectionSetup(connector_type="microsoft_entra_id"),
            VisitorOptions(migrate_values=True, mask_values=False),
        )
        disk_data = visitor.to_disk(
            RawFrontendData(
                value={
                    "ident": "my_ident",
                    "title": "my_title",
                    "authority": SingleChoiceVisitor.option_id("global"),
                    "tenant_id": "my_tenant",
                    "client_id": "my_client",
                    "client_secret": ("explicit_password", "", "my_secret", False),
                    "sites": ("all", None),
                    "proxy": ("url", "http://proxy.example:3128"),
                }
            )
        )
        assert isinstance(disk_data, dict)
        assert disk_data["proxy"] == (
            "cmk_postprocessed",
            "explicit_proxy",
            "http://proxy.example:3128",
        )


def test_oauth2_connection_setup_to_vue(
    request_context: None, with_user: tuple[UserId, str]
) -> None:
    user_id = with_user[0]
    with UserContext(user_id, UserPermissions({}, {}, {}, [])):
        visitor = get_visitor(
            OAuth2ConnectionSetup(connector_type="microsoft_entra_id"),
            VisitorOptions(migrate_values=True, mask_values=False),
        )
        assert isinstance(
            visitor.to_vue(
                RawDiskData(
                    value={
                        "ident": "my_ident",
                        "title": "my_title",
                        "authority": "global",
                        "tenant_id": "my_tenant",
                        "client_id": "my_client",
                        "client_secret": (
                            "cmk_postprocessed",
                            "explicit_password",
                            ("", "my_secret"),
                        ),
                    }
                )
            )[0],
            shared_type_defs.Oauth2ConnectionSetup,
        )


@pytest.mark.xfail(strict=True, raises=ValueError, reason="Crash report 387b0036: ValueError")
@pytest.mark.usefixtures("request_context")
def test_oauth2_connection_form_for_a_user_without_contact_groups(
    monkeypatch: pytest.MonkeyPatch, load_config: Config
) -> None:
    monkeypatch.setattr(oauth2_modes, "get_configured_site_choices", list)
    with (
        create_and_destroy_user(
            automation=False, config=load_config, custom_attrs={"contactgroups": []}
        ) as (user_id, _password),
        UserContext(user_id, UserPermissions({}, {}, {}, [])),
    ):
        form_spec = oauth2_modes.get_oauth2_connection_form_spec()

    editable_by = form_spec.elements["editable_by"].parameter_form
    assert isinstance(editable_by, CascadingSingleChoice)
    assert [element.name for element in editable_by.elements] == ["contact_group"]
