#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal, NewType, TypedDict

from pydantic import BaseModel

from cmk.utils.config_validation_layer.type_defs import Omitted, OMITTED_FIELD

# these need to be written to a .mk file, so a more complex type like Path will lead to problems
PrivateKeyPath = NewType("PrivateKeyPath", str)
PublicKeyPath = NewType("PublicKeyPath", str)


class ContactGroupMapping(TypedDict):
    attribute_match_value: str
    contact_group_ids: Sequence[str]


# TODO: This type is horrible, one can't even dispatch to the right alternative at runtime without
# looking at the *values*. This must be done differently, so dispatching can be done on the *types*
ContactGroupMappingSpec = (
    str | tuple[str, dict[str, str]] | tuple[str, dict[str, str | Sequence[ContactGroupMapping]]]
)
SerializedCertificateSpec = (
    Literal["builtin"] | tuple[Literal["custom"], tuple[PrivateKeyPath, PublicKeyPath]]
)
IDP_METADATA = tuple[Literal["url"], str] | tuple[Literal["xml"], str]
ROLE_MAPPING = Literal[False] | tuple[Literal[True], tuple[str, dict[str, list[str]]]]


class SAMLConnectionModel(BaseModel):
    type: Literal["saml2"]
    version: Literal["1.0.0"]
    owned_by_site: str
    customer: str | Omitted = OMITTED_FIELD
    id: str
    name: str
    description: str
    comment: str
    docu_url: str
    disabled: bool
    idp_metadata: IDP_METADATA
    checkmk_entity_id: str
    checkmk_metadata_endpoint: str
    checkmk_assertion_consumer_service_endpoint: str
    checkmk_server_url: str
    connection_timeout: tuple[int, int]  # connection timeout, read timeout
    signature_certificate: SerializedCertificateSpec
    encryption_certificate: SerializedCertificateSpec | Omitted = OMITTED_FIELD
    user_id_attribute_name: str
    user_alias_attribute_name: str
    email_attribute_name: str
    contactgroups_mapping: ContactGroupMappingSpec
    role_membership_mapping: ROLE_MAPPING
