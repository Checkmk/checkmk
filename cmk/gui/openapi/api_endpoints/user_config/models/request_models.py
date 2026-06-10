#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from collections.abc import Mapping
from typing import Annotated, Any, Literal, Self

from annotated_types import MinLen
from pydantic import AfterValidator, Discriminator, model_validator

from cmk.ccc.version import Edition
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKInternalError
from cmk.gui.fields.utils import edition_field_description
from cmk.gui.openapi.endpoints.utils import mutually_exclusive_fields
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.converter import (
    GroupConverter,
    SiteIdConverter,
    TypedPlainValidator,
    UserRoleIdConverter,
)
from cmk.gui.openapi.framework.model.dynamic_fields import WithDynamicFields
from cmk.gui.openapi.framework.model.restrict_editions import after_validator_for_customer_field
from cmk.gui.userdb import all_user_attributes

from .._utils import (
    AuthOptions,
    ContactOptions,
    IdleDetails,
    NotificationDetails,
    username_should_not_exist,
)

_CUSTOMER_DESCRIPTION = edition_field_description(
    "By specifying a customer, you configure on which sites the user object will be available. "
    "'global' will make the object available on all sites.",
    supported_editions={Edition.ULTIMATEMT},
)


def _validate_authorized_site(value: str) -> str:
    if value == "all":
        return value
    SiteIdConverter.should_exist(value)
    return value


_AnnotatedAuthorizedSite = Annotated[str, AfterValidator(_validate_authorized_site)]


def _validate_custom_user_attributes(dynamic_fields: Mapping[str, object]) -> None:
    db_user_attributes = dict(all_user_attributes(active_config.wato_user_attrs))
    for name, value in dynamic_fields.items():
        attribute = db_user_attributes.get(name)
        if attribute is None:
            raise ValueError(f"Unknown Attribute: {name!r}")
        if not attribute.is_custom():
            raise MKInternalError(
                f"A non custom attribute is not in the CreateUser Schema: {name!r}"
            )
        attribute().valuespec().validate_value(value, "")


# --- Authentication options (discriminated on auth_type) -------------------------------------


@api_model
class AuthPasswordModel:
    auth_type: Literal["password"] = api_field(description="The authentication type")
    password: Annotated[str, MinLen(1)] | None = api_field(
        description="The password for login",
        example="password",
        default=None,
    )
    enforce_password_change: bool = api_field(
        description="If set to True, the user will be forced to change his password on the next "
        "login or access. Defaults to False",
        example=False,
        default=False,
    )

    def to_internal_dict(self) -> AuthOptions:
        details: AuthOptions = {"auth_type": self.auth_type}
        if self.password is not None:
            details["password"] = self.password
        details["enforce_password_change"] = self.enforce_password_change
        return details


@api_model
class AuthSecretModel:
    auth_type: Literal["automation"] = api_field(description="The authentication type")
    secret: str | None = api_field(
        description="For accounts used by automation processes (such as fetching data from views "
        "for further procession). This is the automation secret",
        example="DEYQEQQPYCFFBYH@AVMC",
        default=None,
    )
    store_automation_secret: bool = api_field(
        description="If set to True, the secret will be stored unhashed in order to reuse it in "
        "rules.",
        example=False,
        default=False,
    )

    def to_internal_dict(self) -> AuthOptions:
        details: AuthOptions = {"auth_type": self.auth_type}
        if self.secret is not None:
            details["secret"] = self.secret
        details["store_automation_secret"] = self.store_automation_secret
        return details


@api_model
class AuthUpdatePasswordModel:
    auth_type: Literal["password"] = api_field(description="The authentication type")
    password: Annotated[str, MinLen(1)] | None = api_field(
        description="The password for login",
        example="password",
        default=None,
    )
    enforce_password_change: bool | None = api_field(
        description="If set to True, the user will be forced to change his password on the next "
        "login or access",
        example=False,
        default=None,
    )

    def to_internal_dict(self) -> AuthOptions:
        details: AuthOptions = {"auth_type": self.auth_type}
        if self.password is not None:
            details["password"] = self.password
        if self.enforce_password_change is not None:
            details["enforce_password_change"] = self.enforce_password_change
        return details


@api_model
class AuthUpdateSecretModel:
    auth_type: Literal["automation"] = api_field(description="The authentication type")
    secret: str | None = api_field(
        description="For accounts used by automation processes (such as fetching data from views "
        "for further procession). This is the automation secret",
        example="DEYQEQQPYCFFBYH@AVMC",
        default=None,
    )
    store_automation_secret: bool = api_field(
        description="If set to True, the secret will be stored unhashed in order to reuse it in "
        "rules.",
        example=False,
        default=False,
    )

    def to_internal_dict(self) -> AuthOptions:
        details: AuthOptions = {"auth_type": self.auth_type}
        if self.secret is not None:
            details["secret"] = self.secret
        details["store_automation_secret"] = self.store_automation_secret
        return details


@api_model
class AuthUpdateRemoveModel:
    auth_type: Literal["remove"] = api_field(description="The authentication type")

    def to_internal_dict(self) -> AuthOptions:
        return {"auth_type": self.auth_type}


type _CreateAuthOption = Annotated[AuthPasswordModel | AuthSecretModel, Discriminator("auth_type")]
type _UpdateAuthOption = Annotated[
    AuthUpdatePasswordModel | AuthUpdateSecretModel | AuthUpdateRemoveModel,
    Discriminator("auth_type"),
]


# --- Contact / idle / notification options ---------------------------------------------------


@api_model
class ContactOptionsModel:
    email: str = api_field(
        description="The mail address of the user. Required if the user is a monitoringcontact and "
        "receives notifications via mail.",
        example="user@example.com",
    )
    fallback_contact: bool = api_field(
        description="In case none of your notification rules handles a certain event a notification "
        "will be sent to the specified email",
        example=False,
        default=False,
    )

    def to_internal_dict(self) -> ContactOptions:
        return {"email": self.email, "fallback_contact": self.fallback_contact}


@api_model
class IdleOptionModel:
    option: Literal["global", "disable", "individual"] = api_field(
        description="Specify if the idle timeout should use the global configuration, be disabled "
        "or use an individual duration",
    )
    duration: int = api_field(
        description="The duration in seconds of the individual idle timeout if individual is "
        "selected as idle timeout option.",
        example=60,
        default=3600,
    )

    def to_internal_dict(self) -> IdleDetails:
        return {"option": self.option, "duration": self.duration}


@api_model
class NotificationTimeRangeModel:
    start_time: dt.datetime = api_field(
        description="The start datetime of the time period. The format has to conform to the ISO "
        "8601 profile",
        example="2017-07-21T17:32:28Z",
    )
    end_time: dt.datetime = api_field(
        description="The end datetime of the time period. The format has to conform to the ISO 8601 "
        "profile",
        example="2017-07-21T17:32:28Z",
    )


@api_model
class DisabledNotificationsModel:
    disable: bool | None = api_field(
        description="Option if all notifications should be temporarily disabled",
        example=False,
        default=None,
    )
    timerange: NotificationTimeRangeModel | None = api_field(
        description="A custom timerange during which notifications are disabled",
        example={
            "start_time": "2017-07-21T17:32:28Z",
            "end_time": "2017-07-21T18:32:28Z",
        },
        default=None,
    )

    def to_internal_dict(self) -> NotificationDetails:
        details: NotificationDetails = {}
        if self.disable is not None:
            details["disable"] = self.disable
        if self.timerange is not None:
            details["timerange"] = {
                "start_time": self.timerange.start_time,
                "end_time": self.timerange.end_time,
            }
        return details


# --- Interface options -----------------------------------------------------------------------

type _InterfaceTheme = Literal["default", "dark", "light"]
type _SidebarPosition = Literal["left", "right"]
type _NavigationBarIcons = Literal["hide", "show"]
type _MenuIcons = Literal["topic", "entry"]
type _ShowMode = Literal["default", "default_show_less", "default_show_more", "enforce_show_more"]
type _ContextualHelpIcon = Literal["show_icon", "hide_icon"]
type _NavbarChangesAction = Literal["slideout_ask", "slideout", "full_page"]

_INTERFACE_KEYS = (
    "interface_theme",
    "sidebar_position",
    "navigation_bar_icons",
    "mega_menu_icons",
    "main_menu_icons",
    "show_mode",
    "contextual_help_icon",
    "navbar_changes_action",
)


def _reconcile_menu_icons(data: Any) -> Any:
    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    if isinstance(data, dict):
        params = {key: value for key, value in data.items() if value is not None}
        if params:
            data = dict(data)
            data["main_menu_icons"] = mutually_exclusive_fields(
                str, params, "mega_menu_icons", "main_menu_icons", default="topic"
            )
    return data


@api_model
class CreateUserInterfaceModel:
    interface_theme: _InterfaceTheme = api_field(
        description="The theme of the interface", default="default"
    )
    sidebar_position: _SidebarPosition = api_field(
        description="The position of the sidebar", default="right"
    )
    navigation_bar_icons: _NavigationBarIcons = api_field(
        description="This option decides if icons in the navigation bar should show/hide the "
        "respective titles",
        default="hide",
    )
    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    mega_menu_icons: _MenuIcons = api_field(
        description="Deprecated - use `main_menu_icons` instead.",
        deprecated=True,
        default="topic",
    )
    main_menu_icons: _MenuIcons = api_field(
        description="This option decides if colored icon should be shown for every entry in the "
        "main menus or alternatively only for the headlines (the 'topics')",
        default="topic",
    )
    show_mode: _ShowMode = api_field(
        description="This option decides what show mode should be used for unvisited menus."
        " Alternatively, this option can also be used to enforce show more removing the three dots "
        "for all menus.",
        default="default",
    )
    contextual_help_icon: _ContextualHelpIcon = api_field(
        description="Whether or not to show the contextual icon in the UI for this user.",
        example="show_icon",
        default="show_icon",
    )
    navbar_changes_action: _NavbarChangesAction = api_field(
        description="The view mode for activating changes. Either the quick activation slideout or "
        "the full page view.",
        example="slideout",
        default="slideout_ask",
    )

    @model_validator(mode="before")
    @classmethod
    def _handle_menu_icons_fields(cls, data: Any) -> Any:
        return _reconcile_menu_icons(data)

    def to_internal_dict(self) -> dict[str, Any]:
        return {key: getattr(self, key) for key in _INTERFACE_KEYS}


@api_model
class UpdateUserInterfaceModel:
    interface_theme: _InterfaceTheme | None = api_field(
        description="The theme of the interface", default=None
    )
    sidebar_position: _SidebarPosition | None = api_field(
        description="The position of the sidebar", default=None
    )
    navigation_bar_icons: _NavigationBarIcons | None = api_field(
        description="This option decides if icons in the navigation bar should show/hide the "
        "respective titles",
        default=None,
    )
    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    mega_menu_icons: _MenuIcons | None = api_field(
        description="Deprecated - use `main_menu_icons` instead.",
        deprecated=True,
        default=None,
    )
    main_menu_icons: _MenuIcons | None = api_field(
        description="This option decides if colored icon should be shown for every entry in the "
        "main menus or alternatively only for the headlines (the 'topics')",
        default=None,
    )
    show_mode: _ShowMode | None = api_field(
        description="This option decides what show mode should be used for unvisited menus."
        " Alternatively, this option can also be used to enforce show more removing the three dots "
        "for all menus.",
        default=None,
    )
    contextual_help_icon: _ContextualHelpIcon | None = api_field(
        description="Whether or not to show the contextual icon in the UI for this user.",
        example="show_icon",
        default=None,
    )
    navbar_changes_action: _NavbarChangesAction | None = api_field(
        description="The view mode for activating changes. Either the quick activation slideout or "
        "the full page view.",
        example="slideout",
        default=None,
    )

    @model_validator(mode="before")
    @classmethod
    def _handle_menu_icons_fields(cls, data: Any) -> Any:
        return _reconcile_menu_icons(data)

    def to_internal_dict(self) -> dict[str, Any]:
        details: dict[str, Any] = {}
        for key in _INTERFACE_KEYS:
            value = getattr(self, key)
            if value is not None:
                details[key] = value
        return details


def _default_create_interface() -> CreateUserInterfaceModel:
    # The legacy ``load_default`` for the whole ``interface_options`` object used
    # ``navbar_changes_action="slideout"`` (whereas the per-field default is "slideout_ask").
    return CreateUserInterfaceModel(navbar_changes_action="slideout")


# --- User roles / contact groups -------------------------------------------------------------

_AnnotatedUserRole = Annotated[str, TypedPlainValidator(str, UserRoleIdConverter().should_exist)]
_AnnotatedContactGroup = Annotated[
    str, TypedPlainValidator(str, GroupConverter(group_type="contact").exists)
]


# --- Request body models ---------------------------------------------------------------------


@api_model
class CreateUserModel(WithDynamicFields):
    username: Annotated[str, AfterValidator(username_should_not_exist)] = api_field(
        description="An unique username for the user",
        example="cmkuser",
    )
    fullname: str = api_field(
        description="The alias or full name of the user",
        example="Mathias Kettner",
    )
    customer: str | ApiOmitted = api_field(
        description=_CUSTOMER_DESCRIPTION,
        example="provider",
        default_factory=ApiOmitted,
    )
    auth_option: _CreateAuthOption | None = api_field(
        description="Authentication option for the user",
        example={"auth_type": "password", "password": "password"},
        default=None,
    )
    disable_login: bool = api_field(
        description="The user can be blocked from login but will remain part of the site. The "
        "disabling does not affect notification and alerts.",
        example=False,
        default=False,
    )
    contact_options: ContactOptionsModel = api_field(
        description="Contact settings for the user",
        example={"email": "user@example.com"},
        default_factory=lambda: ContactOptionsModel(email="", fallback_contact=False),
    )
    pager_address: str = api_field(description="", example="", default="")
    idle_timeout: IdleOptionModel | None = api_field(
        description="Idle timeout for the user. Per default, the global configuration is used.",
        example={"option": "global"},
        default=None,
    )
    roles: list[_AnnotatedUserRole] = api_field(
        description="The list of assigned roles to the user",
        example=["user"],
        default_factory=list,
    )
    authorized_sites: list[_AnnotatedAuthorizedSite] = api_field(
        description="The names of the sites the user is authorized to handle.",
        example=["mysite"],
        default_factory=lambda: ["all"],
    )
    contactgroups: list[_AnnotatedContactGroup] = api_field(
        description="Assign the user to one or multiple contact groups. If no contact group is "
        "specified then no monitoring contact will be created for the user.",
        example=["all"],
        default_factory=list,
    )
    disable_notifications: DisabledNotificationsModel = api_field(
        description="",
        example={"disable": False},
        default_factory=DisabledNotificationsModel,
    )
    language: Literal["de", "en", "ro"] | None = api_field(
        description="Configure the language to be used by the user in the user interface. Omitting "
        "this will configure the default language.",
        example="en",
        default=None,
    )
    temperature_unit: Literal["default", "celsius", "fahrenheit"] | None = api_field(
        description="Configure the temperature unit used for graphs and perfometers. Omitting this "
        "field will configure the default temperature unit.",
        example="celsius",
        default=None,
    )
    interface_options: CreateUserInterfaceModel = api_field(
        description="",
        example={"interface_theme": "dark"},
        default_factory=_default_create_interface,
    )
    start_url: str = api_field(
        description="The URL that the user should be redirected to after login. There is a "
        "'default_start_url', a 'welcome_page', and any other will be treated as a custom URL",
        example="default_start_url",
        default="default_start_url",
    )
    dynamic_fields: Mapping[str, object] = api_field(
        description="Custom user attributes. The property name must be a defined custom user "
        "attribute.",
    )

    @model_validator(mode="after")
    def _validate(self) -> Self:
        after_validator_for_customer_field(customer=self.customer)
        _validate_custom_user_attributes(self.dynamic_fields)
        return self

    def to_internal_dict(self) -> dict[str, Any]:
        api_attrs: dict[str, Any] = {
            "alias": self.fullname,
            "auth_option": self.auth_option.to_internal_dict()
            if self.auth_option is not None
            else {},
            "locked": self.disable_login,
            "contact_options": self.contact_options.to_internal_dict(),
            "pager": self.pager_address,
            "roles": list(self.roles),
            "authorized_sites": list(self.authorized_sites),
            "contactgroups": list(self.contactgroups),
            "disable_notifications": self.disable_notifications.to_internal_dict(),
            "interface_options": self.interface_options.to_internal_dict(),
            "start_url": self.start_url,
        }
        if not isinstance(self.customer, ApiOmitted):
            api_attrs["customer"] = None if self.customer == "global" else self.customer
        if self.idle_timeout is not None:
            api_attrs["idle_timeout"] = self.idle_timeout.to_internal_dict()
        if self.language is not None:
            api_attrs["language"] = self.language
        if self.temperature_unit is not None:
            api_attrs["temperature_unit"] = self.temperature_unit
        api_attrs.update(self.dynamic_fields)
        return api_attrs


@api_model
class UpdateUserModel(WithDynamicFields):
    fullname: str | None = api_field(
        description="The alias or full name of the user",
        example="Mathias Kettner",
        default=None,
    )
    customer: str | ApiOmitted = api_field(
        description=_CUSTOMER_DESCRIPTION,
        example="provider",
        default_factory=ApiOmitted,
    )
    auth_option: _UpdateAuthOption | None = api_field(
        description="Authentication option for the user",
        example={"auth_type": "password", "password": "password"},
        default=None,
    )
    disable_login: bool | None = api_field(
        description="The user can be blocked from login but will remain part of the site. The "
        "disabling does not affect notification and alerts.",
        example=False,
        default=None,
    )
    contact_options: ContactOptionsModel | None = api_field(
        description="Contact settings for the user",
        example={"email": "user@example.com"},
        default=None,
    )
    pager_address: str | None = api_field(description="", example="", default=None)
    idle_timeout: IdleOptionModel | None = api_field(
        description="Idle timeout for the user",
        example={},
        default=None,
    )
    roles: list[_AnnotatedUserRole] | None = api_field(
        description="The list of assigned roles to the user",
        example=["user"],
        default=None,
    )
    authorized_sites: list[_AnnotatedAuthorizedSite] | None = api_field(
        description="The names of the sites the user is authorized to handle. Specifying 'all' "
        "will grant the user access to all sites.",
        example=["mysite"],
        default=None,
    )
    contactgroups: list[_AnnotatedContactGroup] | None = api_field(
        description="Assign the user to one or multiple contact groups. If no contact group is "
        "specified then no monitoring contact will be created for the user.",
        example=["all"],
        default=None,
    )
    disable_notifications: DisabledNotificationsModel | None = api_field(
        description="Temporarily disable notifications for this user, optionally for a custom "
        "timerange.",
        example={"disable": False},
        default=None,
    )
    language: Literal["de", "en", "ro"] | None = api_field(
        description="Configure the language to be used by the user in the user interface. Omitting "
        "this will configure the default language",
        example="en",
        default=None,
    )
    temperature_unit: Literal["default", "celsius", "fahrenheit"] | None = api_field(
        description="Configure the temperature unit used for graphs and perfometers.",
        example="celsius",
        default=None,
    )
    interface_options: UpdateUserInterfaceModel | None = api_field(
        description="",
        example={"interface_theme": "dark"},
        default=None,
    )
    start_url: str | None = api_field(
        description="The URL that the user should be redirected to after login. There is a "
        "'default_start_url', a 'welcome_page', and any other will be treated as a custom URL",
        example="default_start_url",
        default=None,
    )
    dynamic_fields: Mapping[str, object] = api_field(
        description="Custom user attributes. The property name must be a defined custom user "
        "attribute.",
    )

    @model_validator(mode="after")
    def _validate(self) -> Self:
        after_validator_for_customer_field(customer=self.customer)
        _validate_custom_user_attributes(self.dynamic_fields)
        return self

    def to_internal_dict(self) -> dict[str, Any]:
        api_attrs: dict[str, Any] = {}
        if self.fullname is not None:
            api_attrs["alias"] = self.fullname
        if not isinstance(self.customer, ApiOmitted):
            api_attrs["customer"] = None if self.customer == "global" else self.customer
        api_attrs["auth_option"] = (
            self.auth_option.to_internal_dict() if self.auth_option is not None else {}
        )
        if self.disable_login is not None:
            api_attrs["locked"] = self.disable_login
        if self.contact_options is not None:
            api_attrs["contact_options"] = self.contact_options.to_internal_dict()
        if self.pager_address is not None:
            api_attrs["pager"] = self.pager_address
        if self.idle_timeout is not None:
            api_attrs["idle_timeout"] = self.idle_timeout.to_internal_dict()
        if self.roles is not None:
            api_attrs["roles"] = list(self.roles)
        if self.authorized_sites is not None:
            api_attrs["authorized_sites"] = list(self.authorized_sites)
        if self.contactgroups is not None:
            api_attrs["contactgroups"] = list(self.contactgroups)
        if self.disable_notifications is not None:
            api_attrs["disable_notifications"] = self.disable_notifications.to_internal_dict()
        if self.language is not None:
            api_attrs["language"] = self.language
        if self.temperature_unit is not None:
            api_attrs["temperature_unit"] = self.temperature_unit
        if self.interface_options is not None:
            api_attrs["interface_options"] = self.interface_options.to_internal_dict()
        if self.start_url is not None:
            api_attrs["start_url"] = self.start_url
        api_attrs.update(self.dynamic_fields)
        return api_attrs


@api_model
class UserDismissWarningModel:
    warning: Literal[
        "notification_fallback",
        "immediate_slideout_change",
        "changes-info",
        "agent_slideout",
    ] = api_field(
        description="The warning to be dismissed.",
        example="notification_fallback",
    )
