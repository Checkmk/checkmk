#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)


@api_model
class PasswordExtension:
    comment: str | ApiOmitted = api_field(
        example="Kommentar",
        description="An optional comment to explain the purpose of this password.",
        default_factory=ApiOmitted,
    )
    documentation_url: str | ApiOmitted = api_field(
        example="localhost",
        description="A URL pointing to documentation or any other page.",
        default_factory=ApiOmitted,
    )
    # TODO: DEPRECATED(17274) - remove in 2.5
    owned_by: str | ApiOmitted = api_field(
        example="admin",
        description="Deprecated - use `editable_by` instead. The owner of the password who is able to edit, delete and use existing passwords.",
        default_factory=ApiOmitted,
        deprecated=True,
    )
    editable_by: str | ApiOmitted = api_field(
        example="admin",
        description="The owner of the password who is able to edit, delete and use existing passwords.",
        default_factory=ApiOmitted,
    )
    shared_with: list[str] | ApiOmitted = api_field(
        example=["all"],
        serialization_alias="shared",
        description="Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        default_factory=ApiOmitted,
    )
    customer: str | ApiOmitted = api_field(
        example="provider",
        description="By specifying a customer, you configure on which sites the user object will be "
        "available. 'global' will make the object available on all sites.",
        default_factory=ApiOmitted,
    )


@api_model
class PasswordObject(DomainObjectModel):
    domainType: Literal["password"] = api_field(
        description="The type of the domain-object.",
    )
    extensions: PasswordExtension = api_field(
        description="All the attributes of the domain object.",
    )


@api_model
class PasswordCollection(DomainObjectCollectionModel):
    domainType: Literal["password"] = api_field(
        description="The domain type of the objects in the collection.",
    )
    value: list[PasswordObject] = api_field(
        description="A list of password objects.",
    )
