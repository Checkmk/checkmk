#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

import datetime as dt
from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
)
from cmk.gui.openapi.framework.model.dynamic_fields import WithDynamicFields


@api_model
class DateTimeRangeModel:
    start_time: dt.datetime = api_field(
        description="The start datetime of the time period. The format conforms to the ISO 8601 profile",
        example="2017-07-21T17:32:28+00:00",
    )
    end_time: dt.datetime | ApiOmitted = api_field(
        description="The end datetime of the time period. The format conforms to the ISO 8601 profile",
        example="2017-07-21T17:32:28+00:00",
        default_factory=ApiOmitted,
    )


@api_model
class ConcreteDisabledNotificationsModel:
    disable: bool | ApiOmitted = api_field(
        description="Option if all notifications should be temporarily disabled",
        default_factory=ApiOmitted,
    )
    timerange: DateTimeRangeModel | ApiOmitted = api_field(
        description="A custom timerange during which notifications are disabled",
        default_factory=ApiOmitted,
    )


@api_model
class ConcreteUserInterfaceAttributesModel:
    interface_theme: Literal["default", "dark", "light"] | ApiOmitted = api_field(
        description="The theme of the interface",
        example="default",
        default_factory=ApiOmitted,
    )
    sidebar_position: Literal["left", "right"] | ApiOmitted = api_field(
        description="The position of the sidebar",
        example="right",
        default_factory=ApiOmitted,
    )
    navigation_bar_icons: Literal["hide", "show"] | ApiOmitted = api_field(
        description="This option decides if icons in the navigation bar should show/hide the "
        "respective titles",
        example="hide",
        default_factory=ApiOmitted,
    )
    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    mega_menu_icons: Literal["topic", "entry"] | ApiOmitted = api_field(
        description="Deprecated - use `main_menu_icons` instead.",
        example="topic",
        deprecated=True,
        default_factory=ApiOmitted,
    )
    main_menu_icons: Literal["topic", "entry"] | ApiOmitted = api_field(
        description="This option decides if colored icon should be shown for every entry in the "
        "main menus or alternatively only for the headlines (the 'topics')",
        example="topic",
        default_factory=ApiOmitted,
    )
    show_mode: (
        Literal["default", "default_show_less", "default_show_more", "enforce_show_more"]
        | ApiOmitted
    ) = api_field(
        description="This option decides what show mode should be used for unvisited menus."
        " Alternatively, this option can also be used to enforce show more removing the three dots "
        "for all menus.",
        example="default",
        default_factory=ApiOmitted,
    )
    contextual_help_icon: Literal["show_icon", "hide_icon"] | ApiOmitted = api_field(
        description="Whether or not to show the contextual icon in the UI for this user.",
        example="show_icon",
        default_factory=ApiOmitted,
    )
    navbar_changes_action: Literal["slideout_ask", "slideout", "full_page"] | ApiOmitted = (
        api_field(
            description="The view mode for activating changes. Either the slideout or the full page view.",
            example="slideout",
            default_factory=ApiOmitted,
        )
    )


@api_model
class UserIdleOptionModel:
    option: Literal["global", "disable", "individual"] = api_field(
        description="This field indicates if the idle timeout uses the global configuration, is "
        "disabled or uses an individual duration",
    )
    duration: int | ApiOmitted = api_field(
        description="The duration in seconds of the individual idle timeout if individual is "
        "selected as idle timeout option.",
        example=3600,
        default_factory=ApiOmitted,
    )


@api_model
class ConcreteUserContactOptionModel:
    email: str = api_field(
        description="The mail address of the user.",
        example="user@example.com",
    )
    fallback_contact: bool | ApiOmitted = api_field(
        description="In case none of the notification rules handle a certain event a notification "
        "will be sent to the specified email",
        default_factory=ApiOmitted,
    )


@api_model
class AuthOptionOutputModel:
    auth_type: Literal["password", "automation", "saml2", "ldap"] | ApiOmitted = api_field(
        example="password",
        description="The authentication type",
        default_factory=ApiOmitted,
    )
    store_automation_secret: bool | ApiOmitted = api_field(
        description="If set to True, the secret is stored",
        example=False,
        default_factory=ApiOmitted,
    )
    enforce_password_change: bool | ApiOmitted = api_field(
        description="If set to True, the user will be forced to change his password on the next "
        "login or access. Defaults to False",
        example=False,
        default_factory=ApiOmitted,
    )


@api_model
class UserAttributesModel(WithDynamicFields):
    """The attributes of a user, including any custom (dynamic) attributes."""

    fullname: str | ApiOmitted = api_field(
        description="The alias or full name of the user.",
        default_factory=ApiOmitted,
    )
    customer: str | ApiOmitted = api_field(
        description="By specifying a customer, you configure on which sites the user object will be "
        "available. 'global' will make the object available on all sites.",
        example="provider",
        default_factory=ApiOmitted,
    )
    disable_login: bool | ApiOmitted = api_field(
        description="This field indicates if the user is allowed to login to the monitoring.",
        default_factory=ApiOmitted,
    )
    contact_options: ConcreteUserContactOptionModel | ApiOmitted = api_field(
        description="Contact settings for the user",
        default_factory=ApiOmitted,
    )
    idle_timeout: UserIdleOptionModel | ApiOmitted = api_field(
        description="Idle timeout for the user. Per default, the global configuration is used.",
        example={"option": "global"},
        default_factory=ApiOmitted,
    )
    roles: list[str] | ApiOmitted = api_field(
        description="The list of assigned roles to the user",
        default_factory=ApiOmitted,
    )
    authorized_sites: list[str] | ApiOmitted = api_field(
        description="The names of the sites that this user is authorized to handle",
        default_factory=ApiOmitted,
    )
    contactgroups: list[str] | ApiOmitted = api_field(
        description="The contact groups that this user is a member of",
        default_factory=ApiOmitted,
    )
    pager_address: str | ApiOmitted = api_field(
        description="The pager address of the user.",
        default_factory=ApiOmitted,
    )
    disable_notifications: ConcreteDisabledNotificationsModel | ApiOmitted = api_field(
        description="Whether notifications are temporarily disabled for this user, optionally for "
        "a custom timerange.",
        default_factory=ApiOmitted,
    )
    language: str | ApiOmitted = api_field(
        description="The language used by the user in the user interface",
        default_factory=ApiOmitted,
    )
    temperature_unit: str | ApiOmitted = api_field(
        description="The temperature unit used for graphs and perfometers.",
        default_factory=ApiOmitted,
    )
    auth_option: AuthOptionOutputModel | ApiOmitted = api_field(
        description="Enforce password change attribute for the user",
        example={"auth_type": "password", "enforce_password_change": False},
        default_factory=ApiOmitted,
    )
    interface_options: ConcreteUserInterfaceAttributesModel | ApiOmitted = api_field(
        description="The user interface options configured for this user, such as theme, sidebar "
        "position and navigation behavior.",
        default_factory=ApiOmitted,
    )
    start_url: str | ApiOmitted = api_field(
        description="The URL that the user should be redirected to after login. There is a "
        "'default_start_url', a 'welcome_page', and any other will be treated as a custom URL",
        example="welcome_page",
        default_factory=ApiOmitted,
    )
    dynamic_fields: dict[str, object] = api_field(
        description="Each custom user attribute, keyed by its name. The value type depends on the "
        "attribute's valuespec (for example string, boolean or integer).",
    )


@api_model
class UserObject(DomainObjectModel):
    domainType: Literal["user_config"] = api_field(
        description="The domain type of the object.",
    )
    extensions: UserAttributesModel = api_field(
        description="The attributes of the user",
    )


@api_model
class UserCollection(DomainObjectCollectionModel):
    domainType: Literal["user_config"] = api_field(
        description="The domain type of the objects in the collection.",
    )
    value: list[UserObject] = api_field(
        description="A list of user objects.",
    )
