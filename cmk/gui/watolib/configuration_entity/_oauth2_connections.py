#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs import (
    get_visitor,
    process_validation_messages,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.form_specs.unstable.oauth2_connection_setup import OAuth2ConnectionSetup
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.oauth2_connections.watolib.store import (
    extract_password_store_entry,
    save_reference_to_config_file,
    save_tokens_to_passwordstore,
)
from cmk.utils.oauth2_connection import OAuth2Connection


def save_oauth2_connection_and_passwords_from_slidein_schema(
    data: RawFrontendData, *, user: LoggedInUser, pprint_value: bool, use_git: bool
) -> tuple[str, OAuth2Connection]:
    form_spec = OAuth2ConnectionSetup()
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))

    validation_errors = visitor.validate(data)
    process_validation_messages(validation_errors)

    disk_data = visitor.to_disk(data)
    assert isinstance(disk_data, dict)

    save_tokens_to_passwordstore(
        ident=disk_data["ident"],
        title=disk_data["title"],
        client_secret=extract_password_store_entry(disk_data["client_secret"]),
        access_token=extract_password_store_entry(disk_data["access_token"]),
        refresh_token=extract_password_store_entry(disk_data["refresh_token"]),
        user_id=user.id,
        pprint_value=pprint_value,
        use_git=use_git,
    )

    return save_reference_to_config_file(
        ident=disk_data["ident"],
        title=disk_data["title"],
        client_id=disk_data["client_id"],
        tenant_id=disk_data["tenant_id"],
        authority=disk_data["authority"],
        user_id=user.id,
        pprint_value=pprint_value,
        use_git=use_git,
    )
