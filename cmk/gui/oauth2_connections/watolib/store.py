#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal, TypeGuard

from cmk.ccc.site import omd_site, SiteId
from cmk.ccc.user import UserId
from cmk.gui.exceptions import MKUserError
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.config_domains import ConfigDomainCore
from cmk.gui.watolib.passwords import load_passwords, save_password
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir
from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_OAUTH
from cmk.utils.oauth2_connection import OAuth2Connection, OAuth2ConnectorType
from cmk.utils.password_store import Password


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(OAuth2ConnectionsConfigFile())


class OAuth2ConnectionsConfigFile(WatoSimpleConfigFile[OAuth2Connection]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=wato_root_dir() / "oauth2_connections.mk",
            config_variable="oauth2_connections",
            spec_class=OAuth2Connection,
        )


def save_oauth2_connection(
    ident: str,
    details: OAuth2Connection,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
    affected_sites: list[SiteId] | None = None,
) -> None:
    oauth2_connections_config_file = OAuth2ConnectionsConfigFile()
    entries = oauth2_connections_config_file.load_for_modification()
    entries[ident] = details
    add_change(
        action_name="add-oauth2-connection",
        text=f"Added the OAuth2 connection '{ident}'",
        user_id=user_id,
        domains=[ConfigDomainCore()],
        sites=affected_sites,
        use_git=use_git,
    )
    oauth2_connections_config_file.save(entries, pprint_value)


def load_oauth2_connections() -> dict[str, OAuth2Connection]:
    oauth2_connections_config_file = OAuth2ConnectionsConfigFile()
    return oauth2_connections_config_file.load_for_reading()


def update_oauth2_connection(
    ident: str,
    details: OAuth2Connection,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
    affected_sites: list[SiteId] | None = None,
) -> None:
    oauth2_connections_config_file = OAuth2ConnectionsConfigFile()
    entries = oauth2_connections_config_file.load_for_modification()
    if ident not in entries:
        raise KeyError(f"OAuth2 connection with ident '{ident}' does not exist")
    entries[ident] = details

    add_change(
        action_name="update-oauth2-connection",
        text=f"Updated the OAuth2 connection '{ident}'",
        user_id=user_id,
        domains=[ConfigDomainCore()],
        sites=affected_sites,
        use_git=use_git,
    )
    oauth2_connections_config_file.save(entries, pprint_value)


def delete_oauth2_connection(
    ident: str,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
    affected_sites: list[SiteId] | None = None,
) -> None:
    oauth2_connections_config_file = OAuth2ConnectionsConfigFile()
    entries = oauth2_connections_config_file.load_for_modification()
    if ident not in entries:
        raise KeyError(f"OAuth2 connection with ident '{ident}' does not exist")
    del entries[ident]
    add_change(
        action_name="deleted-oauth2-connection",
        text=f"Deleted the OAuth2 connection '{ident}'",
        user_id=user_id,
        domains=[ConfigDomainCore()],
        sites=affected_sites,
        use_git=use_git,
    )
    oauth2_connections_config_file.save(entries, pprint_value)


def is_locked_by_oauth2_connection(
    ident: GlobalIdent | None, *, check_reference_exists: bool = True
) -> TypeGuard[GlobalIdent]:
    if ident is None:
        return False

    if ident["program_id"] != PROGRAM_ID_OAUTH:
        return False

    if check_reference_exists and ident["instance_id"] not in load_oauth2_connections():
        return False

    return True


def save_tokens_to_passwordstore(
    *,
    ident: str,
    title: str,
    client_secret: str,
    access_token: str,
    refresh_token: str,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
) -> None:
    # TODO Think site_id should be in data above
    site_id = omd_site()
    password_entries = load_passwords()
    for pw_title, entry, password in [
        ("Client secret", "client_secret", client_secret),
        ("Access token", "access_token", access_token),
        ("Refresh token", "refresh_token", refresh_token),
    ]:
        password_ident = f"{ident}_{entry}"
        save_password(
            ident=password_ident,
            details=Password(
                title=pw_title,
                comment=title,
                docu_url="",
                password=password,
                owned_by=None,
                shared_with=[],
                locked_by=GlobalIdent(
                    site_id=site_id,
                    program_id=PROGRAM_ID_OAUTH,
                    instance_id=ident,
                ),
            ),
            new_password=password_ident not in password_entries,
            user_id=user_id,
            pprint_value=pprint_value,
            use_git=use_git,
        )


def update_reference(
    *,
    ident: str,
    title: str,
    client_id: str,
    tenant_id: str,
    authority: str,
    connector_type: OAuth2ConnectorType,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
) -> tuple[str, OAuth2Connection]:
    details = OAuth2Connection(
        title=title,
        access_token=("cmk_postprocessed", "stored_password", (f"{ident}_access_token", "")),
        client_id=client_id,
        client_secret=("cmk_postprocessed", "stored_password", (f"{ident}_client_secret", "")),
        refresh_token=("cmk_postprocessed", "stored_password", (f"{ident}_refresh_token", "")),
        tenant_id=tenant_id,
        authority=authority,
        connector_type=connector_type,
    )
    update_oauth2_connection(
        ident=ident,
        details=details,
        user_id=user_id,
        pprint_value=pprint_value,
        use_git=use_git,
    )
    return ident, details


def save_new_reference_to_config_file(
    *,
    ident: str,
    title: str,
    client_id: str,
    tenant_id: str,
    authority: str,
    connector_type: OAuth2ConnectorType,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
) -> tuple[str, OAuth2Connection]:
    details = OAuth2Connection(
        title=title,
        access_token=("cmk_postprocessed", "stored_password", (f"{ident}_access_token", "")),
        client_id=client_id,
        client_secret=("cmk_postprocessed", "stored_password", (f"{ident}_client_secret", "")),
        refresh_token=("cmk_postprocessed", "stored_password", (f"{ident}_refresh_token", "")),
        tenant_id=tenant_id,
        authority=authority,
        connector_type=connector_type,
    )
    save_oauth2_connection(
        ident=ident,
        details=details,
        user_id=user_id,
        pprint_value=pprint_value,
        use_git=use_git,
    )
    return ident, details


def extract_password_store_entry(
    value: tuple[
        Literal["cmk_postprocessed"],
        Literal["explicit_password", "stored_password"],
        tuple[str, str],
    ],
) -> str:
    match value:
        case ("cmk_postprocessed", "stored_password", (password_id, str())):
            password_entries = load_passwords()
            password_entry = password_entries[password_id]
            if not password_entry:
                raise MKUserError("client_secret", f"Password with ID '{password_id}' not found")
            return str(password_entry["password"])
        case ("cmk_postprocessed", "explicit_password", (_password_id, password)):
            return str(password)
        case _:
            raise MKUserError("client_secret", "Incorrect format for secret value")
