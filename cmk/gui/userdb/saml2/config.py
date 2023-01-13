#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from cmk.utils.paths import (
    saml2_custom_signature_private_keyfile,
    saml2_custom_signature_public_keyfile,
    saml2_signature_private_keyfile,
    saml2_signature_public_keyfile,
)


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


def _certificate_to_config(certificate: str | tuple[str, tuple[str, str]]) -> dict[str, Path]:
    if isinstance(certificate, str):
        return {
            "private": saml2_signature_private_keyfile,
            "public": saml2_signature_public_keyfile,
        }

    if not isinstance(certificate, tuple):
        raise ValueError(
            f"Expected str or tuple for signature_certificate, got {type(certificate).__name__}"
        )

    _, (private_key, cert) = certificate
    # The pysaml2 client expects certificates in an actual file
    saml2_custom_signature_public_keyfile.write_text(cert)
    saml2_custom_signature_private_keyfile.write_text(private_key)
    return {
        "private": saml2_custom_signature_private_keyfile,
        "public": saml2_custom_signature_public_keyfile,
    }


def valuespec_to_config(user_input: Mapping[str, Any]) -> ConnectorConfig:
    valuespec_config = copy.deepcopy(dict(user_input))

    interface_config = {
        k: valuespec_config.pop(k)
        for k in [
            "connection_timeout",
            "idp_metadata_endpoint",
            "checkmk_server_url",
        ]
    }
    interface_config["user_attributes"] = {
        k: v
        for k, v in [
            (k, valuespec_config.pop(k))
            for k in [
                "user_id",
                "alias",
                "email",
                "contactgroups",
            ]
        ]
        if v
    }
    interface_config["signature_certificate"] = _certificate_to_config(
        valuespec_config.pop("signature_certificate")
    )

    valuespec_config["interface_config"] = interface_config

    return ConnectorConfig(**valuespec_config)
