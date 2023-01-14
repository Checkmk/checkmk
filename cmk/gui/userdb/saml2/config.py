#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, NewType

from lxml import etree
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

from livestatus import SiteId

from cmk.utils.paths import (
    omd_root,
    saml2_attribute_mappings_dir,
    saml2_custom_cert_dir,
    saml2_signature_private_keyfile,
    saml2_signature_public_keyfile,
)
from cmk.utils.site import url_prefix

Milliseconds = NewType("Milliseconds", int)


class URL(str):
    ...


class XMLText(str):
    ...


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
    user_attribute_mappings_dir: Path


class ConnectivitySettings(BaseModel):
    timeout: tuple[int, int]
    idp_metadata: URL | XMLText
    entity_id: str
    assertion_consumer_service_endpoint: str
    binding: str
    verify_tls: bool


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
    owned_by_site: SiteId
    description: str
    comment: str
    docu_url: str
    disabled: bool
    identity_provider: str
    interface_config: InterfaceConfig


class CertificateType(enum.Enum):
    BUILTIN = "default"
    CUSTOM = "custom"


class ServiceProviderMetadata(BaseModel):
    entity_id: str
    metadata_endpoint: str
    assertion_consumer_service_endpoint: str


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
    return Certificate(
        # Needs to be put together here because OMD_ROOT will be different for each site in a
        # distributed monitoring set-up
        private=omd_root / private_key,
        public=omd_root / cert,
    )


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


def _decode_xml(text: bytes) -> XMLText:
    xml_tree = etree.ElementTree(etree.XML(text))
    return XMLText(text.decode(xml_tree.docinfo.encoding or "utf-8"))


def _idp_metadata(metadata: tuple[str, str] | tuple[str, tuple[str, str, bytes]]) -> XMLText | URL:
    """
    >>> _idp_metadata(("url", "http://bla/bli"))
    'http://bla/bli'
    >>> _idp_metadata(("text", "<metadata>...</metadata>"))
    '<metadata>...</metadata>'
    >>> _idp_metadata(("file", ("/path/to/myfile.xml", "text/xml", b"<metadata>...</metadata>")))
    '<metadata>...</metadata>'

    >>> isinstance(_idp_metadata(("url", "http://bla/bli")), URL)
    True
    >>> isinstance(_idp_metadata(("text", "<metadata>...</metadata>")), XMLText)
    True
    >>> isinstance(_idp_metadata(("file", ("/path/to/myfile.xml", "text/xml", b"<metadata>...</metadata>"))), XMLText)
    True
    """

    option_name, option = metadata
    match option_name:
        case "url":
            assert isinstance(option, str)
            return URL(option)
        case "text":
            assert isinstance(option, str)
            return XMLText(option)
        case "file":
            assert isinstance(option, tuple)
            _, _, file_content = option
            return _decode_xml(file_content)
        case _:
            raise ValueError(f"Unrecognised option for IDP metadata: {option_name}")


def checkmk_service_provider_metadata(
    checkmk_url: str, connection_id: str
) -> ServiceProviderMetadata:
    entity_id = f"{checkmk_url}/saml_metadata.py"
    return ServiceProviderMetadata(
        entity_id=entity_id,
        metadata_endpoint=f"{entity_id}?RelayState={connection_id}",
        assertion_consumer_service_endpoint=f"{checkmk_url}/saml_acs.py?acs",
    )


def checkmk_server_url(checkmk_url: str) -> str:
    return f"{checkmk_url}{url_prefix()}check_mk"


def valuespec_to_config(user_input: Mapping[str, Any]) -> ConnectorConfig:
    connection_id = user_input["id"]
    roles_mapping = user_input["role_membership_mapping"]

    interface_config = InterfaceConfig(
        connectivity_settings=ConnectivitySettings(
            timeout=user_input["connection_timeout"],
            idp_metadata=_idp_metadata(user_input["idp_metadata"]),
            entity_id=user_input["checkmk_entity_id"],
            assertion_consumer_service_endpoint=user_input[
                "checkmk_assertion_consumer_service_endpoint"
            ],
            binding=BINDING_HTTP_POST,
            verify_tls=True,
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
            user_attribute_mappings_dir=saml2_attribute_mappings_dir,
        ),
        cache_settings=CacheSettings(
            redis_namespace="saml2_authentication_requests",
            authentication_request_id_expiry=Milliseconds(5 * 60 * 1000),
        ),
    )

    name = user_input["name"]
    return ConnectorConfig(
        type=user_input["type"],
        version=user_input["version"],
        id=connection_id,
        name=name,
        owned_by_site=user_input["owned_by_site"],
        description=user_input["description"],
        comment=user_input["comment"],
        docu_url=user_input["docu_url"],
        disabled=user_input["disabled"],
        identity_provider=f"{name} ({connection_id})",
        interface_config=interface_config,
    )


def _remove_custom_files(cert_dir: Path) -> None:
    if not cert_dir.exists():
        return
    shutil.rmtree(cert_dir)


def write_certificate_files(
    certificate: str | tuple[str, tuple[str, str]], connection_id: str
) -> str | tuple[str, tuple[str, str]]:
    type_ = determine_certificate_type(certificate)

    cert_dir = saml2_custom_cert_dir / connection_id / "signature"

    if type_ is CertificateType.BUILTIN:
        # If the user switches from using custom certificates to builtin certificates, the custom
        # ones should be deleted
        _remove_custom_files(cert_dir)
        return type_.value

    assert isinstance(certificate, tuple)

    _, (private_key, cert) = certificate
    cert_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    private_keyfile = cert_dir / "private.pem"
    cert_file = cert_dir / "public.pem"

    private_keyfile.touch(mode=0o600)
    private_keyfile.write_text(private_key)

    cert_file.touch(mode=0o600)
    cert_file.write_text(cert)

    # Needs to be the relative path because OMD_ROOT will be different for each site in a
    # distributed monitoring set-up
    return type_.value, (
        str(private_keyfile.relative_to(omd_root)),
        str(cert_file.relative_to(omd_root)),
    )


def read_certificate_files(
    certificate: str | tuple[str, tuple[str, str]]
) -> str | tuple[str, tuple[str, str]]:
    type_ = determine_certificate_type(certificate)
    if type_ is CertificateType.BUILTIN:
        return type_.value

    assert isinstance(certificate, tuple)
    _, (private_keyfile_rel_path, cert_file_rel_path) = certificate

    private_key = omd_root / private_keyfile_rel_path
    cert = omd_root / cert_file_rel_path

    if not private_key.exists() or not cert.exists():
        return type_.value, ("", "")

    return type_.value, (private_key.read_text(), cert.read_text())
