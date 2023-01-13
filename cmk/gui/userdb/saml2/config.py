#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from pydantic import BaseModel


class Certificate(BaseModel):
    private: Path
    public: Path


class UserAttributeNames(BaseModel):
    user_id: str
    alias: str | None
    email: str | None
    contactgroups: str | None


class InterfaceConfig(BaseModel):
    connection_timeout: tuple[int, int]
    checkmk_server_url: str
    idp_metadata_endpoint: str
    user_attributes: UserAttributeNames
    signature_certificate: Certificate


class ConnectorConfig(BaseModel):
    type: str
    version: str
    id: str
    name: str
    description: str
    comment: str
    docu_url: str
    disabled: bool
    interface_config: InterfaceConfig
