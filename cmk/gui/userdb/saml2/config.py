#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NewType

from pydantic import BaseModel
from saml2 import BINDING_HTTP_POST
from saml2.xmldsig import (
    DIGEST_SHA512,
    SIG_ECDSA_SHA256,
    SIG_ECDSA_SHA384,
    SIG_ECDSA_SHA512,
    SIG_RSA_SHA256,
    SIG_RSA_SHA384,
    SIG_RSA_SHA512,
)

from cmk.utils.paths import saml2_signature_private_keyfile, saml2_signature_public_keyfile
from cmk.utils.site import url_prefix

Milliseconds = NewType("Milliseconds", int)


class Certificate(BaseModel):
    private: Path
    public: Path


class UserAttributeNames(BaseModel):
    user_id: str
    alias: str | None
    email: str | None
    contactgroups: str | None
    roles: str | None


class UserAttributeSettings(BaseModel):
    attribute_names: UserAttributeNames
    role_membership_mapping: Mapping[str, set[str]]


class SecuritySettings(BaseModel):
    allow_unknown_user_attributes: bool
    sign_authentication_requests: bool
    enforce_signed_responses: bool
    enforce_signed_assertions: bool
    signing_algortithm: str
    digest_algorithm: str
    allowed_algorithms: set[str]
    signature_certificate: Certificate


class ConnectivitySettings(BaseModel):
    timeout: tuple[int, int]
    checkmk_server_url: str
    idp_metadata_endpoint: str
    entity_id: str
    assertion_consumer_service_endpoint: str
    binding: str


class CacheSettings(BaseModel):
    redis_namespace: str
    authentication_request_id_expiry: Milliseconds


class InterfaceConfig(BaseModel):
    user_attributes: UserAttributeSettings
    security_settings: SecuritySettings
    connectivity_settings: ConnectivitySettings
    cache_settings: CacheSettings


class ConnectorConfig(BaseModel):
    type: str
    version: str
    id: str
    name: str
    description: str
    comment: str
    docu_url: str
    disabled: bool
    identity_provider_url: str
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


def _determine_certificate_paths(certificate: str | tuple[str, tuple[str, str]]) -> Certificate:
    type_ = determine_certificate_type(certificate)

    if type_ is CertificateType.BUILTIN:
        return Certificate(
            private=saml2_signature_private_keyfile, public=saml2_signature_public_keyfile
        )
    assert isinstance(certificate, tuple)
    _, (private_key, cert) = certificate
    return Certificate(private=Path(private_key), public=Path(cert))


def _role_attribute_name(
    roles_mapping: bool | tuple[bool, tuple[str, Mapping[str, Sequence[str]]]]
) -> str | None:
    if not roles_mapping:
        return None

    assert isinstance(roles_mapping, tuple)
    return roles_mapping[1][0]


def _role_membership_mapping(
    roles_mapping: bool | tuple[bool, tuple[str, Mapping[str, Sequence[str]]]]
) -> Mapping[str, set[str]]:
    if not roles_mapping:
        return {}

    assert isinstance(roles_mapping, tuple)
    return {k: set(v) for k, v in roles_mapping[1][1].items()}


def valuespec_to_config(user_input: Mapping[str, Any]) -> ConnectorConfig:
    idp_url = user_input["idp_metadata_endpoint"]
    checkmk_server_url = f"{user_input['checkmk_server_url']}{url_prefix()}check_mk"
    roles_mapping = user_input["role_membership_mapping"]

    interface_config = InterfaceConfig(
        connectivity_settings=ConnectivitySettings(
            timeout=user_input["connection_timeout"],
            idp_metadata_endpoint=user_input["idp_metadata_endpoint"],
            checkmk_server_url=checkmk_server_url,
            entity_id=f"{checkmk_server_url}/saml_metadata.py",
            assertion_consumer_service_endpoint=f"{checkmk_server_url}/saml_acs.py?acs",
            binding=BINDING_HTTP_POST,
        ),
        user_attributes=UserAttributeSettings(
            attribute_names=UserAttributeNames(
                user_id=user_input["user_id"],
                alias=user_input["alias"],
                email=user_input["email"],
                contactgroups=user_input["contactgroups"],
                roles=_role_attribute_name(roles_mapping),
            ),
            role_membership_mapping=_role_membership_mapping(roles_mapping),
        ),
        security_settings=SecuritySettings(
            allow_unknown_user_attributes=True,
            sign_authentication_requests=True,
            enforce_signed_responses=True,
            enforce_signed_assertions=True,
            signing_algortithm=SIG_RSA_SHA512,
            digest_algorithm=DIGEST_SHA512,  # this is referring to the digest alg the counterparty should use
            allowed_algorithms={
                SIG_ECDSA_SHA256,
                SIG_ECDSA_SHA384,
                SIG_ECDSA_SHA512,
                SIG_RSA_SHA256,
                SIG_RSA_SHA384,
                SIG_RSA_SHA512,
            },
            signature_certificate=_determine_certificate_paths(user_input["signature_certificate"]),
        ),
        cache_settings=CacheSettings(
            redis_namespace="saml2_authentication_requests",
            authentication_request_id_expiry=Milliseconds(5 * 60 * 1000),
        ),
    )
    return ConnectorConfig(
        type=user_input["type"],
        version=user_input["version"],
        id=user_input["id"],
        name=user_input["name"],
        description=user_input["description"],
        comment=user_input["comment"],
        docu_url=user_input["docu_url"],
        disabled=user_input["disabled"],
        identity_provider_url=idp_url,
        interface_config=interface_config,
    )
