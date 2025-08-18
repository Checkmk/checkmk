#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

from cmk.ccc.site import SiteId
from cmk.ccc.version import Edition
from cmk.gui.fields.utils import edition_field_description
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import (
    SiteIdConverter,
    TypedPlainValidator,
)
from cmk.gui.openapi.framework.model.restrict_editions import RestrictEditions

from .common import SiteConnectionBaseModel
from .config_example import default_config_example


@api_model
class BasicSettingsBaseModel:
    alias: str = api_field(
        description="The alias of the site.",
        example="Site Alias",
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


@api_model
class BasicSettingsEditModel(BasicSettingsBaseModel):
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_exist),
    ] = api_field(
        description="The site ID.",
        example="prod",
    )


@api_model
class SiteConnectionEdit(SiteConnectionBaseModel):
    basic_settings: BasicSettingsEditModel = api_field(
        description="The basic connection attributes",
    )


@api_model
class SiteConnectionEditModel:
    site_config: SiteConnectionEdit = api_field(
        description="A site's connection.",
        example=default_config_example(),
    )


@api_model
class BasicSettingsCreateModel(BasicSettingsBaseModel):
    site_id: Annotated[
        SiteId,
        TypedPlainValidator(str, SiteIdConverter.should_not_exist),
    ] = api_field(
        description="The site ID for the new connection.",
        example="prod",
    )


@api_model
class SiteConnectionCreate(SiteConnectionBaseModel):
    basic_settings: BasicSettingsCreateModel = api_field(
        description="The basic connection attributes",
    )


@api_model
class SiteConnectionCreateModel:
    site_config: SiteConnectionCreate = api_field(
        description="A site's connection.",
        example=default_config_example(),
    )
