#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from cmk.ccc.version import Edition
from cmk.gui.fields.utils import edition_field_description
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel
from cmk.gui.openapi.framework.model.restrict_editions import RestrictEditions

from .common import SiteConnectionBaseModel
from .config_example import default_config_example


@api_model
class BasicSettingsModel:
    site_id: str = api_field(
        description="The site id.",
        example="prod",
    )
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
class SiteConnectionExtensionsModel(SiteConnectionBaseModel):
    basic_settings: BasicSettingsModel = api_field(
        description="The basic settings of the site connection.",
    )


@api_model
class SiteConnectionModel(DomainObjectModel):
    domainType: Literal["site_connection"] = api_field(
        description="The domain type of the object.",
    )
    extensions: SiteConnectionExtensionsModel = api_field(
        description="The configuration attributes of a site.",
        example=default_config_example(),
    )
