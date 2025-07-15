#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Any

from marshmallow import fields as _fields
from marshmallow import post_load

from cmk.gui import fields as gui_fields
from cmk.gui.exceptions import MKUserError
from cmk.gui.fields.base import MultiNested, ValueTypedDictSchema
from cmk.gui.fields.definitions import ensure_string
from cmk.gui.fields.utils import BaseSchema
from cmk.gui.openapi.restful_objects.response_schemas import DomainObject, DomainObjectCollection
from cmk.gui.userdb import get_user_attributes

from cmk import fields
from cmk.fields import base

_logger = logging.getLogger(__name__)


class DateTimeRange(BaseSchema):
    start_time = gui_fields.Timestamp(
        required=True,
        example="2017-07-21T17:32:28+00:00",
        description="The start datetime of the time period. The format conforms to the ISO 8601 profile",
    )
    end_time = gui_fields.Timestamp(
        example="2017-07-21T17:32:28+00:00",
        description="The end datetime of the time period. The format conforms to the ISO 8601 profile",
        format="iso8601",
    )


class ConcreteDisabledNotifications(BaseSchema):
    disable = fields.Boolean(
        required=False,
        description="Option if all notifications should be temporarily disabled",
    )
    timerange = fields.Nested(
        DateTimeRange,
        description="A custom timerange during which notifications are disabled",
        required=False,
    )


class ConcreteUserInterfaceAttributes(BaseSchema):
    interface_theme = fields.String(
        required=False,
        description="The theme of the interface",
        enum=["default", "dark", "light"],
        example="default",
    )
    sidebar_position = fields.String(
        required=False,
        description="The position of the sidebar",
        enum=["left", "right"],
        example="right",
    )
    navigation_bar_icons = fields.String(
        required=False,
        description="This option decides if icons in the navigation bar should show/hide the "
        "respective titles",
        enum=["hide", "show"],
        example="hide",
    )
    main_menu_icons = fields.String(
        required=False,
        description="This option decides if colored icon should be shown foe every entry in the "
        "main menus or alternatively only for the headlines (the 'topics')",
        enum=["topic", "entry"],
        example="topic",
    )
    show_mode = fields.String(
        required=False,
        description="This option decides what show mode should be used for unvisited menus."
        " Alternatively, this option can also be used to enforce show more removing the three dots "
        "for all menus.",
        enum=["default", "default_show_less", "default_show_more", "enforce_show_more"],
        example="default",
    )
    contextual_help_icon = fields.String(
        required=False,
        enum=["show_icon", "hide_icon"],
        description="Whether or not to show the contextual icon in the UI for this user.",
        example="show_icon",
        load_default="show_icon",
    )


class UserIdleOption(BaseSchema):
    option = fields.String(
        required=True,
        description="This field indicates if the idle timeout uses the global configuration, is "
        "disabled or uses an individual duration",
        enum=["global", "disable", "individual"],
    )
    duration = fields.Integer(
        required=False,
        description="The duration in seconds of the individual idle timeout if individual is "
        "selected as idle timeout option.",
        example=3600,
    )


class ConcreteUserContactOption(BaseSchema):
    email = fields.String(
        required=True,
        description="The mail address of the user.",
        example="user@example.com",
    )
    fallback_contact = fields.Boolean(
        description="In case none of the notification rules handle a certain event a notification "
        "will be sent to the specified email",
        required=False,
    )


class AuthOptionOutput(BaseSchema):
    auth_type = fields.String(
        required=False,
        example="password",
        enum=["password", "automation", "saml2", "ldap"],
    )
    store_automation_secret = fields.Boolean(
        required=False,
        description="If set to True, the secret is stored",
        example=False,
    )
    enforce_password_change = fields.Boolean(
        required=False,
        description="If set to True, the user will be forced to change his password on the next "
        "login or access. Defaults to False",
        example=False,
    )


class BaseUserAttributes(BaseSchema):
    fullname = fields.String(required=True, description="The alias or full name of the user.")
    customer = gui_fields.customer_field(
        required=True,
        should_exist=True,
    )
    disable_login = fields.Boolean(
        required=False,
        description="This field indicates if the user is allowed to login to the monitoring.",
    )
    contact_options = fields.Nested(
        ConcreteUserContactOption,
        required=False,
        description="Contact settings for the user",
    )
    idle_timeout = fields.Nested(
        UserIdleOption,
        required=False,
        description="Idle timeout for the user. Per default, the global configuration is used.",
        example={"option": "global"},
    )
    roles = fields.List(
        fields.String(),
        description="The list of assigned roles to the user",
    )
    authorized_sites = fields.List(
        fields.String(),
        description="The names of the sites that this user is authorized to handle",
        required=False,
    )
    contactgroups = fields.List(
        fields.String(),
        description="The contact groups that this user is a member of",
        required=False,
    )
    pager_address = fields.String(
        required=False,
        description="",
    )
    disable_notifications = fields.Nested(
        ConcreteDisabledNotifications,
        required=False,
    )
    language = fields.String(
        required=False,
        description="The language used by the user in the user interface",
    )
    temperature_unit = fields.String(
        required=False,
        description="The temperature unit used for graphs and perfometers.",
    )
    auth_option = fields.Nested(
        AuthOptionOutput,
        required=False,
        description="Enforce password change attribute for the user",
        example={"auth_type": "password", "enforce_password_change": False},
    )
    interface_options = fields.Nested(
        ConcreteUserInterfaceAttributes,
        required=False,
    )
    start_url = fields.String(
        description="The URL that the user should be redirected to after login. There is a "
        "'default_start_url', a 'welcome_page', and any other will be treated as a custom URL",
        example="welcome_page",
    )


class CustomUserAttributes(ValueTypedDictSchema):
    class ValueTypedDict:
        value_type = ValueTypedDictSchema.wrap_field(
            base.String(
                description="Each tag is a mapping of string to string",
                validate=ensure_string,
            )
        )

    @post_load
    def _valid(self, user_attributes: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        # NOTE
        # If an attribute gets deleted AFTER it has already been set,
        # this would break here. We therefore can't validate outbound data as thoroughly
        # because our own data can be inherently inconsistent.

        # use the user_attribute_registry directly?
        db_user_attributes = dict(get_user_attributes())
        for name, value in user_attributes.items():
            try:
                attribute = db_user_attributes[name].valuespec()
            except KeyError:
                _logger.error("No such attribute: %s", name)
                return user_attributes

            try:
                attribute.validate_value(value, f"ua_{name}")
            except MKUserError as exc:
                _logger.error("Error validating %s: %s", name, str(exc))

        return user_attributes


def user_attributes_field(
    description: str | None = None, example: Any | None = None
) -> _fields.Field:
    """Build an Attribute Field

    Args:
        direction:
            If the data is *coming from* the user (inbound) or *going to* the user (outbound).

        description:
            A descriptive text of this field. Required.

        example:
            An example for the OpenAPI documentation. Required.
    """
    if description is None:
        # SPEC won't validate without description, though the error message is very obscure, so we
        # clarify this here by force.
        raise ValueError("description is necessary.")

    return MultiNested(
        [BaseUserAttributes, CustomUserAttributes],
        merged=True,  # to unify both models
        description=description,
        example=example,
        many=False,
        load_default=dict,
        required=False,
    )


class UserObject(DomainObject):
    domainType = fields.Constant(
        "user_config",
        description="The domain type of the object.",
    )
    extensions = user_attributes_field(
        description="The attributes of the user",
        example={"fullname": "John Doe"},
    )


class UserCollection(DomainObjectCollection):
    domainType = fields.Constant(
        "user_config",
        description="The domain type of the objects in the collection.",
    )
    value = fields.List(
        fields.Nested(UserObject),
        description="A list of user objects.",
    )
