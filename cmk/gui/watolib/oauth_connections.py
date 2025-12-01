#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import TypedDict

from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(OAuthConnectionsConfigFile())


class OAuthConnection(TypedDict):
    title: str
    client_secret_reference: str
    access_token_reference: str
    refresh_token_reference: str
    client_id: str
    tenant_id: str


class OAuthConnectionsConfigFile(WatoSimpleConfigFile[OAuthConnection]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=wato_root_dir() / "oauth_connections.mk",
            config_variable="oauth_connections",
            spec_class=OAuthConnection,
        )


def save_oauth_connection(
    ident: str,
    details: OAuthConnection,
    *,
    pprint_value: bool,
) -> None:
    oauth_connections_config_file = OAuthConnectionsConfigFile()
    entries = oauth_connections_config_file.load_for_modification()
    entries[ident] = details
    oauth_connections_config_file.save(entries, pprint_value)
