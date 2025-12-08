#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict, TypeGuard

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir
from cmk.utils.global_ident_type import GlobalIdent, PROGRAM_ID_OAUTH


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(OAuth2ConnectionsConfigFile())


class OAuth2Connection(TypedDict):
    title: str
    client_secret_reference: str
    access_token_reference: str
    refresh_token_reference: str
    client_id: str
    tenant_id: str
    authority: str


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
        domains=[ConfigDomainGUI()],
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
        domains=[ConfigDomainGUI()],
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
        domains=[ConfigDomainGUI()],
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
