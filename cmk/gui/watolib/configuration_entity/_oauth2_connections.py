#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import NamedTuple

from marshmallow import ValidationError

from cmk.gui.form_specs import (
    FormSpecValidationError,
    get_visitor,
    process_validation_messages,
    RawDiskData,
    RawFrontendData,
    VisitorOptions,
)
from cmk.gui.form_specs.unstable.oauth2_connection_setup import OAuth2ConnectionSetup
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.oauth2_connections.watolib.store import (
    extract_password_store_entry,
    load_oauth2_connections,
    load_usable_oauth2_connections,
    OAuth2ConnectionsConfigFile,
    save_new_reference_to_config_file,
    save_tokens_to_passwordstore,
    update_reference,
)
from cmk.gui.watolib.passwords import load_passwords, password_id_in_use
from cmk.gui.watolib.pending_changes import PendingChanges
from cmk.shared_typing import vue_formspec_components as shared_type_defs
from cmk.utils.oauth2_connection import OAuth2Connection, OAuth2ConnectorType


def _validate_unique_title(title: str, exclude_ident: str | None = None) -> None:
    """Raise FormSpecValidationError if title is already used by another connection."""
    for ident, entry in load_oauth2_connections().items():
        if ident == exclude_ident:
            continue
        if entry["title"] == title:
            raise FormSpecValidationError(
                [
                    shared_type_defs.ValidationMessage(
                        location=["title"],
                        message=_(
                            "The title must be unique. The title '%(title)s' is already used by "
                            "the OAuth2 connection with ID %(ident)s."
                        )
                        % {"title": title, "ident": ident},
                        replacement_value=title,
                    )
                ]
            )


def update_oauth2_connection_and_passwords_from_slidein_schema(
    data: RawFrontendData,
    connector_type: OAuth2ConnectorType,
    *,
    pprint_value: bool,
    pending_changes: PendingChanges,
) -> tuple[str, OAuth2Connection]:
    form_spec = OAuth2ConnectionSetup(connector_type=connector_type)
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))

    validation_errors = visitor.validate(data)
    process_validation_messages(validation_errors)

    disk_data = visitor.to_disk(data)
    assert isinstance(disk_data, dict)

    # The ID comes from the request, so it may name a connection of another group
    config_file = OAuth2ConnectionsConfigFile()
    connections = config_file.load_for_reading()
    if disk_data["ident"] not in connections or not (
        user.may("wato.edit_all_passwords")
        or disk_data["ident"] in config_file.filter_editable_entries(connections, user)
    ):
        raise ValidationError(
            message=_("The OAuth2 connection does not exist or you may not edit it."),
            field_name="data",
        )

    _validate_unique_title(disk_data["title"], exclude_ident=disk_data["ident"])

    owned_by = None
    match disk_data.get("editable_by"):
        case ("administrators", None):
            owned_by = None
        case ("contact_group", group_name):
            owned_by = group_name
        case _:
            raise ValidationError(
                message=_("Invalid value for 'owned_by'."),
                field_name="data",
            )

    save_tokens_to_passwordstore(
        acting_user=user,
        ident=disk_data["ident"],
        title=disk_data["title"],
        client_secret=extract_password_store_entry(user, disk_data["client_secret"]),
        access_token=extract_password_store_entry(user, disk_data["access_token"]),
        refresh_token=extract_password_store_entry(user, disk_data["refresh_token"]),
        owned_by=owned_by,
        shared_with=disk_data.get("shared_with", []),
        pprint_value=pprint_value,
        pending_changes=pending_changes,
    )

    return update_reference(
        ident=disk_data["ident"],
        title=disk_data["title"],
        client_id=disk_data["client_id"],
        tenant_id=disk_data["tenant_id"],
        authority=disk_data["authority"],
        sites=disk_data["sites"],
        connector_type=connector_type,
        proxy=disk_data.get("proxy"),
        pprint_value=pprint_value,
        pending_changes=pending_changes,
    )


def save_oauth2_connection_and_passwords_from_slidein_schema(
    data: RawFrontendData,
    connector_type: OAuth2ConnectorType,
    *,
    pprint_value: bool,
    pending_changes: PendingChanges,
) -> tuple[str, OAuth2Connection]:
    form_spec = OAuth2ConnectionSetup(connector_type=connector_type)
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))

    validation_errors = visitor.validate(data)
    process_validation_messages(validation_errors)

    disk_data = visitor.to_disk(data)
    assert isinstance(disk_data, dict)

    if disk_data["ident"] in load_oauth2_connections():
        raise ValidationError(
            message=_("This ID is already in use."),
            field_name="data",
        )
    # The secrets are saved as passwords named after the connection, which must not replace
    # existing passwords, including those the user may not use
    if any(
        password_id_in_use(f"{disk_data['ident']}_{entry}")
        for entry in ("client_secret", "access_token", "refresh_token")
    ):
        raise ValidationError(
            message=_("This ID is already in use."),
            field_name="data",
        )

    _validate_unique_title(disk_data["title"])

    owned_by = None
    match disk_data.get("editable_by"):
        case ("administrators", None):
            owned_by = None
        case ("contact_group", group_name):
            owned_by = group_name
        case _:
            raise ValidationError(message=_("Invalid value for 'owned_by'."), field_name="data")

    save_tokens_to_passwordstore(
        acting_user=user,
        ident=disk_data["ident"],
        title=disk_data["title"],
        client_secret=extract_password_store_entry(user, disk_data["client_secret"]),
        access_token=extract_password_store_entry(user, disk_data["access_token"]),
        refresh_token=extract_password_store_entry(user, disk_data["refresh_token"]),
        owned_by=owned_by,
        shared_with=disk_data.get("shared_with", []),
        pprint_value=pprint_value,
        pending_changes=pending_changes,
    )

    return save_new_reference_to_config_file(
        ident=disk_data["ident"],
        title=disk_data["title"],
        client_id=disk_data["client_id"],
        tenant_id=disk_data["tenant_id"],
        authority=disk_data["authority"],
        sites=disk_data["sites"],
        connector_type=connector_type,
        proxy=disk_data.get("proxy"),
        pprint_value=pprint_value,
        pending_changes=pending_changes,
    )


class OAuth2ConnectionData(NamedTuple):
    description: str
    data: Mapping[str, object]


def get_oauth2_connection(
    oauth2_connection_id: str,
) -> OAuth2ConnectionData:
    usable_oauth2_connections = load_usable_oauth2_connections(user)
    oauth2_connections = load_oauth2_connections()
    if oauth2_connection_id not in oauth2_connections:
        raise KeyError(f"OAuth2 connection with ident '{oauth2_connection_id}' does not exist")

    if oauth2_connection_id not in usable_oauth2_connections:
        raise KeyError(
            f"OAuth2 connection with ident '{oauth2_connection_id}' is not shared with the current user. "
        )

    connection = usable_oauth2_connections[oauth2_connection_id]
    client_secret = load_passwords(user)[connection["client_secret"][2][0]]
    editable_by = client_secret["owned_by"]
    form_spec = OAuth2ConnectionSetup(connector_type=connection["connector_type"])
    visitor = get_visitor(form_spec, VisitorOptions(migrate_values=True, mask_values=False))
    _, values = visitor.to_vue(
        RawDiskData(
            {k: v for k, v in connection.items() if k != "connector_type"}
            | {
                "editable_by": ("contact_group", editable_by)
                if editable_by
                else ("administrators", None),
                "shared_with": client_secret["shared_with"],
            }
        )
    )
    assert isinstance(values, Mapping)
    return OAuth2ConnectionData(
        description=connection["title"],
        data={**values, "ident": oauth2_connection_id},
    )
