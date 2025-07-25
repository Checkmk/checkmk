#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Annotated, Self

from annotated_types import MinLen
from pydantic import AfterValidator, model_validator

from cmk.ccc.version import Edition
from cmk.gui.fields.utils import edition_field_description
from cmk.gui.openapi.framework.model import api_field, ApiOmitted
from cmk.gui.openapi.framework.model.converter import PasswordConverter
from cmk.gui.openapi.framework.model.restrict_editions import RestrictEditions
from cmk.utils.password_store import Password


@dataclass(kw_only=True, slots=True)
class CreatePassword:
    ident: Annotated[
        str,
        AfterValidator(PasswordConverter.is_valid_id),
        AfterValidator(PasswordConverter.not_exists),
    ] = api_field(
        example="pass",
        description="The unique identifier for the password",
    )
    title: str = api_field(
        example="Kubernetes login",
        description="The name of your password for easy recognition.",
    )
    comment: str = api_field(
        example="Kommentar",
        description="An optional comment to explain the purpose of this password.",
        default="",
    )
    documentation_url: str = api_field(
        alias="docu_url",
        example="localhost",
        description="An optional URL pointing to documentation or any other page. You can use either global URLs (beginning with http://), absolute local urls (beginning with /) or relative URLs (that are relative to check_mk/).",
        default="",
    )
    password: Annotated[str, MinLen(1)] = api_field(
        example="password",
        description="The password string",
    )
    # TODO: DEPRECATED(17274) - remove in 2.5
    owned_by: str | ApiOmitted = api_field(
        example="admin",
        description="Deprecated - use `editable_by` instead. Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        alias="owner",
        default_factory=ApiOmitted,
        additional_metadata={"deprecated": True},
    )
    editable_by: str | ApiOmitted = api_field(
        example="admin",
        description="Each password is owned by a group of users which are able to edit, delete and use existing passwords. By default, the admin group is the owner of a password.",
        default_factory=ApiOmitted,
    )
    shared_with: list[str] | ApiOmitted = api_field(
        example=["all"],
        description="Each password is owned by a group of users which are able to edit, delete and use existing passwords.",
        alias="shared",
        default_factory=ApiOmitted,
    )
    customer: Annotated[
        str | ApiOmitted,
        RestrictEditions(supported_editions={Edition.CME}, required_if_supported=True),
    ] = api_field(
        example="provider",
        description=edition_field_description(
            "By specifying a customer, you configure on which sites the user object will be "
            "available. 'global' will make the object available on all sites.",
            supported_editions={Edition.CME},
            field_required=True,
        ),
        default_factory=ApiOmitted,
    )

    @model_validator(mode="after")
    def validate_mutually_exclusive_fields(self) -> Self:
        if not isinstance(self.owned_by, ApiOmitted) and not isinstance(
            self.editable_by, ApiOmitted
        ):
            raise ValueError(
                "Only one of the fields 'owned_by' or 'editable_by' is allowed, but multiple were provided."
            )
        return self

    def to_internal(self) -> Password:
        if isinstance(self.editable_by, str):
            owned_by = self.editable_by
        elif isinstance(self.owned_by, str):
            owned_by = self.owned_by
        else:
            owned_by = "admin"
        password = Password(
            title=self.title,
            comment=self.comment,
            docu_url=self.documentation_url,
            password=self.password,
            owned_by=owned_by,
            shared_with=self.shared_with if isinstance(self.shared_with, list) else [],
        )
        if isinstance(self.customer, str):
            password["customer"] = self.customer
        return password
