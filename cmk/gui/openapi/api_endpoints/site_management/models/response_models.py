#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Annotated, Literal, Self

from livestatus import SiteConfiguration

import cmk.ccc.version as cmk_version
from cmk.ccc.version import Edition
from cmk.gui.fields.utils import edition_field_description
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.framework.model.restrict_editions import RestrictEditions
from cmk.gui.site_config import site_is_local
from cmk.utils import paths

from .common import (
    ConnectionModel,
    SiteConnectionBaseModel,
    StatusConnectionModel,
    UserSyncAllModel,
    UserSyncDisabledModel,
    UserSyncWithLdapModel,
)
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
        RestrictEditions(supported_editions={Edition.ULTIMATEMT}, required_if_supported=True),
    ] = api_field(
        example="provider",
        description=edition_field_description(
            "By specifying a customer, you configure on which sites the user object will be "
            "available. 'global' will make the object available on all sites.",
            supported_editions={Edition.ULTIMATEMT},
            field_required=True,
        ),
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, site_configuration: SiteConfiguration) -> Self:
        model = cls(
            site_id=site_configuration["id"],
            alias=site_configuration["alias"],
        )
        if cmk_version.edition(paths.omd_root) is cmk_version.Edition.ULTIMATEMT:
            model.customer = site_configuration.get("customer", "global")
        return model


@api_model
class SiteConnectionExtensionsModel(SiteConnectionBaseModel):
    basic_settings: BasicSettingsModel = api_field(
        description="The basic settings of the site connection.",
    )
    logged_in: bool | ApiOmitted = api_field(
        description="If a remote site is currently logged in, this will be True, "
        "if not it will be False. For the main site, nothing is returned.",
        example=True,
        default_factory=ApiOmitted,
    )

    @classmethod
    def from_internal(cls, site_configuration: SiteConfiguration) -> Self:
        def _configuration_connection_from_internal(
            site_configuration: SiteConfiguration,
        ) -> ConnectionModel:
            def _user_sync_from_internal(
                user_sync: Literal["all"] | tuple[Literal["list"], list[str]] | None,
            ) -> UserSyncWithLdapModel | UserSyncAllModel | UserSyncDisabledModel:
                if user_sync == "all":
                    return UserSyncAllModel(sync_with_ldap_connections="all")

                if isinstance(user_sync, tuple) and user_sync[0] == "list":
                    return UserSyncWithLdapModel(
                        sync_with_ldap_connections="ldap",
                        ldap_connections=user_sync[1],
                    )
                return UserSyncDisabledModel(sync_with_ldap_connections="disabled")

            return ConnectionModel(
                enable_replication=False if site_configuration.get("replication") is None else True,
                url_of_remote_site=site_configuration["multisiteurl"],
                disable_remote_configuration=site_configuration["disable_wato"],
                ignore_tls_errors=site_configuration["insecure"],
                direct_login_to_web_gui_allowed=site_configuration["user_login"],
                user_sync=_user_sync_from_internal(user_sync=site_configuration["user_sync"]),
                replicate_event_console=site_configuration["replicate_ec"],
                replicate_extensions=site_configuration["replicate_mkps"],
                message_broker_port=site_configuration["message_broker_port"],
                is_trusted=site_configuration["is_trusted"],
            )

        return cls(
            basic_settings=BasicSettingsModel.from_internal(site_configuration),
            status_connection=StatusConnectionModel.from_internal(site_configuration),
            configuration_connection=_configuration_connection_from_internal(site_configuration),
            logged_in=bool(site_configuration.get("secret"))
            if not site_is_local(site_configuration)
            else ApiOmitted(),
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

    @classmethod
    def from_internal(cls, site_configuration: SiteConfiguration) -> Self:
        return cls(
            domainType="site_connection",
            id=site_configuration["id"],
            title=site_configuration["alias"],
            extensions=SiteConnectionExtensionsModel.from_internal(site_configuration),
            links=generate_links(
                domain_type="site_connection",
                identifier=site_configuration["id"],
                deletable=not (site_configuration["socket"] == ("local", None)),
            ),
        )
