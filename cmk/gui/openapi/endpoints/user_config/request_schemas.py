#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping
from typing import Any

import marshmallow
from marshmallow_oneofschema import OneOfSchema

from cmk.gui import fields as gui_fields
from cmk.gui.exceptions import MKInternalError
from cmk.gui.fields.definitions import GroupField, Username, UserRoleID
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.userdb import all_user_attributes
from cmk.gui.utils.temperate_unit import TemperatureUnit

from cmk import fields

AUTH_PASSWORD = fields.String(
    required=False,
    description="The password for login",
    example="password",
    minLength=1,
)

AUTH_SECRET = fields.String(
    required=False,
    description="For accounts used by automation processes (such as fetching data from views "
    "for further procession). This is the automation secret",
    example="DEYQEQQPYCFFBYH@AVMC",
)
AUTH_SECRET_STORE = fields.Boolean(
    required=False,
    description="If set to True, the secret will be stored unhashed in order to reuse it in rules.",
    example=False,
    load_default=False,
)

AUTH_CREATE_TYPE = fields.String(
    required=False,
    description="The authentication type",
    enum=["automation", "password"],
    example="password",
)

AUTH_UPDATE_TYPE = fields.String(
    required=True,
    description="The authentication type",
    enum=["automation", "password", "remove"],
    example="password",
)


class AuthSecret(BaseSchema):
    auth_type = AUTH_CREATE_TYPE
    secret = AUTH_SECRET
    store_automation_secret = AUTH_SECRET_STORE


class AuthPassword(BaseSchema):
    auth_type = AUTH_CREATE_TYPE
    password = AUTH_PASSWORD
    enforce_password_change = fields.Boolean(
        required=False,
        description="If set to True, the user will be forced to change his password on the next "
        "login or access. Defaults to False",
        example=False,
        load_default=False,
    )


class AuthUpdateSecret(BaseSchema):
    auth_type = AUTH_UPDATE_TYPE
    secret = AUTH_SECRET
    store_automation_secret = AUTH_SECRET_STORE


class AuthUpdatePassword(BaseSchema):
    auth_type = AUTH_UPDATE_TYPE
    password = AUTH_PASSWORD
    enforce_password_change = fields.Boolean(
        required=False,
        description="If set to True, the user will be forced to change his password on the next "
        "login or access",
        example=False,
    )


class AuthUpdateRemove(BaseSchema):
    auth_type = AUTH_UPDATE_TYPE


class AuthOption(OneOfSchema):
    type_field = "auth_type"
    type_field_remove = False
    type_schemas = {
        "password": AuthPassword,
        "automation": AuthSecret,
    }


class AuthUpdateOption(OneOfSchema):
    type_field = "auth_type"
    type_field_remove = False
    type_schemas = {
        "password": AuthUpdatePassword,
        "automation": AuthUpdateSecret,
        "remove": AuthUpdateRemove,
    }


class IdleOption(BaseSchema):
    option = fields.String(
        required=True,
        description="Specify if the idle timeout should use the global configuration, be disabled "
        "or use an individual duration",
        enum=["global", "disable", "individual"],
        example=False,
    )
    duration = fields.Integer(
        required=False,
        description="The duration in seconds of the individual idle timeout if individual is "
        "selected as idle timeout option.",
        example=60,
        load_default=3600,
    )


class UserContactOption(BaseSchema):
    email = fields.String(
        required=True,
        description="The mail address of the user. Required if the user is a monitoring"
        "contact and receives notifications via mail.",
        example="user@example.com",
    )
    # User cannot enable fallback contact if no email is specified
    fallback_contact = fields.Boolean(
        description="In case none of your notification rules handles a certain event a notification "
        "will be sent to the specified email",
        required=False,
        load_default=False,
        example=False,
    )


class DisableNotificationCustomTimeRange(BaseSchema):
    # TODO: gui_fields.Dict validation also for Timperiods
    start_time = fields.DateTime(
        format="iso8601",
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The start datetime of the time period. The format has to conform to the ISO 8601 profile",
    )
    end_time = fields.DateTime(
        required=True,
        example="2017-07-21T17:32:28Z",
        description="The end datetime of the time period. The format has to conform to the ISO 8601 profile",
        format="iso8601",
    )


class DisabledNotifications(BaseSchema):
    disable = fields.Boolean(
        required=False,
        description="Option if all notifications should be temporarily disabled",
        example=False,
    )
    timerange = fields.Nested(
        DisableNotificationCustomTimeRange,
        description="A custom timerange during which notifications are disabled",
        required=False,
        example={
            "start_time": "2017-07-21T17:32:28Z",
            "end_time": "2017-07-21T18:32:28Z",
        },
    )


class UserInterfaceAttributes(BaseSchema):
    interface_theme = fields.String(
        required=False,
        description="The theme of the interface",
        enum=["default", "dark", "light"],
        load_default="default",
    )
    sidebar_position = fields.String(
        required=False,
        description="The position of the sidebar",
        enum=["left", "right"],
        load_default="right",
    )
    navigation_bar_icons = fields.String(
        required=False,
        description="This option decides if icons in the navigation bar should show/hide the "
        "respective titles",
        enum=["hide", "show"],
        load_default="hide",
    )
    mega_menu_icons = fields.String(
        required=False,
        description="This option decides if colored icon should be shown foe every entry in the "
        "mega menus or alternatively only for the headlines (the 'topics')",
        enum=["topic", "entry"],
        load_default="topic",
    )
    show_mode = fields.String(
        required=False,
        description="This option decides what show mode should be used for unvisited menus."
        " Alternatively, this option can also be used to enforce show more removing the three dots "
        "for all menus.",
        enum=["default", "default_show_less", "default_show_more", "enforce_show_more"],
        load_default="default",
    )


class CustomUserAttributes(BaseSchema):
    class Meta:
        ordered = True
        unknown = marshmallow.INCLUDE

    @marshmallow.post_load(pass_original=True)
    def validate_custom_attributes(
        self,
        result_data: dict[str, Any],
        original_data: MutableMapping[str, Any],
        **_unused_args: Any,
    ) -> dict[str, Any]:
        for field in self.fields:
            original_data.pop(field, None)

        for name, value in original_data.items():
            attribute = dict(all_user_attributes()).get(name)
            if attribute is None:
                raise marshmallow.ValidationError(f"Unknown Attribute: {name!r}")
            if not attribute.is_custom():
                raise MKInternalError(
                    f"A non custom attribute is not in the CreateUser Schema: {name!r}"
                )
            valuespec = attribute().valuespec()
            valuespec.validate_value(value, "")
            result_data[name] = value
        return result_data


class CreateUser(CustomUserAttributes):
    username = Username(
        required=True,
        should_exist=False,
        description="An unique username for the user",
        example="cmkuser",
    )
    fullname = fields.String(
        required=True,
        description="The alias or full name of the user",
        example="Mathias Kettner",
        attribute="alias",
    )
    customer = gui_fields.customer_field(
        required=False,
        should_exist=True,
        allow_global=True,
        description="By specifying a customer, you configure on which sites the user object will be available. "
        "'global' will make the object available on all sites.",
    )
    auth_option = fields.Nested(
        AuthOption,
        required=False,
        description="Authentication option for the user",
        example={"auth_type": "password", "password": "password"},
        load_default=dict,
    )
    disable_login = fields.Boolean(
        required=False,
        load_default=False,
        description="The user can be blocked from login but will remain part of the site. "
        "The disabling does not affect notification and alerts.",
        example=False,
        attribute="locked",
    )
    contact_options = fields.Nested(
        UserContactOption,
        required=False,
        description="Contact settings for the user",
        load_default=lambda: {"email": "", "fallback_contact": False},
        example={"email": "user@example.com"},
    )
    pager_address = fields.String(
        required=False,
        description="",
        example="",
        load_default="",
        attribute="pager",
    )
    idle_timeout = fields.Nested(
        IdleOption,
        required=False,
        description="Idle timeout for the user. Per default, the global configuration is used.",
        example={"option": "global"},
    )
    roles = fields.List(
        UserRoleID(
            description="An existing user role",
            required=True,
            example="user",
            presence="should_exist",
        ),
        required=False,
        load_default=list,
        description="The list of assigned roles to the user",
        example=["user"],
    )
    authorized_sites = fields.List(
        gui_fields.SiteField(allow_all_value=True),
        description="The names of the sites the user is authorized to handle.",
        example=["heute"],
        required=False,
        load_default=["all"],
    )
    contactgroups = fields.List(
        GroupField(
            group_type="contact",
            example="all",
            required=True,
            should_exist=True,
        ),
        required=False,
        load_default=list,
        description="Assign the user to one or multiple contact groups. If no contact group is "
        "specified then no monitoring contact will be created for the user."
        "",
        example=["all"],
    )
    disable_notifications = fields.Nested(
        DisabledNotifications,
        required=False,
        load_default=dict,
        example={"disable": False},
        description="",
    )
    # default language is not setting a key in dict
    language = fields.String(
        required=False,
        description="Configure the language to be used by the user in the user interface. Omitting "
        "this will configure the default language.",
        example="en",
        enum=["de", "en", "ro"],
    )
    temperature_unit = fields.String(
        required=False,
        description="Configure the temperature unit used for graphs and perfometers. Omitting this "
        "field will configure the default temperature unit.",
        example="celsius",
        enum=[
            "default",
            *(unit.value for unit in TemperatureUnit),
        ],
    )
    interface_options = fields.Nested(
        UserInterfaceAttributes,
        required=False,
        load_default={
            "interface_theme": "default",
            "sidebar_position": "right",
            "navigation_bar_icons": "hide",
            "mega_menu_icons": "topic",
            "show_mode": "default",
        },
        example={"interface_theme": "dark"},
        description="",
    )


class UserInterfaceUpdateAttributes(BaseSchema):
    interface_theme = fields.String(
        required=False,
        description="The theme of the interface",
        enum=["default", "dark", "light"],
    )
    sidebar_position = fields.String(
        required=False,
        description="The position of the sidebar",
        enum=["left", "right"],
    )
    navigation_bar_icons = fields.String(
        required=False,
        description="This option decides if icons in the navigation bar should show/hide the "
        "respective titles",
        enum=["hide", "show"],
    )
    mega_menu_icons = fields.String(
        required=False,
        description="This option decides if colored icon should be shown foe every entry in the "
        "mega menus or alternatively only for the headlines (the 'topics')",
        enum=["topic", "entry"],
    )
    show_mode = fields.String(
        required=False,
        description="This option decides what show mode should be used for unvisited menus."
        " Alternatively, this option can also be used to enforce show more removing the three dots "
        "for all menus.",
        enum=["default", "default_show_less", "default_show_more", "enforce_show_more"],
    )


class UpdateUser(CustomUserAttributes):
    fullname = fields.String(
        required=False,
        description="The alias or full name of the user",
        example="Mathias Kettner",
        attribute="alias",
    )
    customer = gui_fields.customer_field(
        required=False,
        should_exist=True,
    )
    auth_option = fields.Nested(
        AuthUpdateOption,
        required=False,
        description="Authentication option for the user",
        example={"auth_type": "password", "password": "password"},
        load_default=dict,
    )
    disable_login = fields.Boolean(
        required=False,
        description="The user can be blocked from login but will remain part of the site. "
        "The disabling does not affect notification and alerts.",
        example=False,
        attribute="locked",
    )
    contact_options = fields.Nested(
        UserContactOption,
        required=False,
        description="Contact settings for the user",
        example={"email": "user@example.com"},
    )
    pager_address = fields.String(
        required=False,
        description="",
        example="",
        attribute="pager",
    )
    idle_timeout = fields.Nested(
        IdleOption,
        required=False,
        description="Idle timeout for the user",
        example={},
    )
    roles = fields.List(
        UserRoleID(
            description="An existing user role",
            required=True,
            example="user",
            presence="should_exist",
        ),
        required=False,
        description="The list of assigned roles to the user",
        example=["user"],
    )
    authorized_sites = fields.List(
        gui_fields.SiteField(allow_all_value=True),
        description="The names of the sites the user is authorized to handle. Specifying 'all' "
        "will grant the user access to all sites.",
        example=["heute"],
        required=False,
    )
    contactgroups = fields.List(
        GroupField(
            group_type="contact",
            required=True,
            example="all",
            should_exist=True,
        ),
        required=False,
        description="Assign the user to one or multiple contact groups. If no contact group is "
        "specified then no monitoring contact will be created for the user."
        "",
        example=["all"],
    )
    disable_notifications = fields.Nested(
        DisabledNotifications,
        required=False,
        example={"disabled": False},
        description="",
    )
    # default language is not setting a key in dict
    language = fields.String(
        required=False,
        description="Configure the language to be used by the user in the user interface. Omitting "
        "this will configure the default language",
        example="en",
        enum=["de", "en", "ro"],
    )
    temperature_unit = fields.String(
        required=False,
        description="Configure the temperature unit used for graphs and perfometers.",
        example="celsius",
        enum=[
            "default",
            *(unit.value for unit in TemperatureUnit),
        ],
    )
    interface_options = fields.Nested(
        UserInterfaceUpdateAttributes,
        required=False,
        example={"interface_theme": "dark"},
        description="",
    )
