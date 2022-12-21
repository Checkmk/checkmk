#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any

from pydantic import BaseModel

from cmk.gui.i18n import _
from cmk.gui.plugins.userdb.utils import UserConnector, UserConnectorRegistry
from cmk.gui.userdb.saml2.interface import Interface, InterfaceConfig

# TODO (lisa): introduce enums
SAML2_CONNECTOR_TYPE = "saml2"


class ConnectorConfig(BaseModel):
    type: str
    version: str
    id: str
    description: str
    comment: str
    docu_url: str
    disabled: bool
    interface_config: InterfaceConfig


class Connector(UserConnector):
    def __init__(self, raw_config: dict[str, Any]) -> None:
        super().__init__(raw_config)
        self.__config = ConnectorConfig(**self._config)
        self.__interface = Interface(self.__config.interface_config)

    @property
    def interface(self) -> Interface:
        return self.__interface

    @classmethod
    def type(cls) -> str:
        return SAML2_CONNECTOR_TYPE

    @property
    def id(self) -> str:
        return self.__config.id

    @classmethod
    def title(cls) -> str:
        return _("SAML2.0 Integration")

    @classmethod
    def short_title(cls) -> str:
        return _("SAML 2.0")

    def is_enabled(self) -> bool:
        return not self.__config.disabled

    def identity_provider_url(self) -> str:
        return self.__config.interface_config.idp_metadata_endpoint


def register(user_connector_registry: UserConnectorRegistry) -> None:
    user_connector_registry.register(Connector)
