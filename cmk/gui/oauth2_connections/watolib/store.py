#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict

from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(OAuth2ConnectionsConfigFile())


class OAuth2Connection(TypedDict):
    title: str
    client_secret_reference: str
    access_token_reference: str
    refresh_token_reference: str
    client_id: str
    tenant_id: str


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
    pprint_value: bool,
) -> None:
    oauth2_connections_config_file = OAuth2ConnectionsConfigFile()
    entries = oauth2_connections_config_file.load_for_modification()
    entries[ident] = details
    oauth2_connections_config_file.save(entries, pprint_value)
