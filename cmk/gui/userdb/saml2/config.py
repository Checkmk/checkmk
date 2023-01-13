#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import enum
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from cmk.utils.paths import saml2_signature_private_keyfile, saml2_signature_public_keyfile


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


class CertificateType(enum.Enum):
    BUILTIN = "default"
    CUSTOM = "custom"


def determine_certificate_type(certificate: str | tuple[str, tuple[str, str]]) -> CertificateType:
    """
    >>> determine_certificate_type("default")
    <CertificateType.BUILTIN: 'default'>

    >>> determine_certificate_type(("custom", ("--BEGIN PRIVATE KEY--...", "--BEGIN CERTIFICATE--...")))
    <CertificateType.CUSTOM: 'custom'>
    """
    if isinstance(certificate, str):
        return CertificateType(certificate)
    return CertificateType(certificate[0])


def _determine_certificate_paths(
    certificate: str | tuple[str, tuple[str, str]]
) -> Mapping[str, Path]:
    type_ = determine_certificate_type(certificate)

    if type_ is CertificateType.BUILTIN:
        return {
            "private": saml2_signature_private_keyfile,
            "public": saml2_signature_public_keyfile,
        }

    assert isinstance(certificate, tuple)
    _, (private_key, cert) = certificate

    return {
        "private": Path(private_key),
        "public": Path(cert),
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

    interface_config["signature_certificate"] = _determine_certificate_paths(
        valuespec_config.pop("signature_certificate")
    )

    valuespec_config["interface_config"] = interface_config

    return ConnectorConfig(**valuespec_config)
