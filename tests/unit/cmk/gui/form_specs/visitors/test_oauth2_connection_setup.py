#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from unittest import mock

from cmk.ccc.user import UserId
from cmk.gui.form_specs import (
    get_visitor,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.form_specs.unstable.oauth2_connection_setup import OAuth2ConnectionSetup
from cmk.gui.form_specs.visitors.single_choice import SingleChoiceVisitor
from cmk.gui.session import UserContext
from cmk.gui.utils.roles import UserPermissions
from cmk.shared_typing import vue_formspec_components as shared_type_defs


def test_oauth2_connection_setup_to_disk() -> None:
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
            }
        )
    ) == {
        "ident": "my_ident",
        "title": "my_title",
        "authority": "global",
        "tenant_id": "my_tenant",
        "client_id": "my_client",
        "client_secret": ("cmk_postprocessed", "explicit_password", (mock.ANY, "my_secret")),
    }


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
