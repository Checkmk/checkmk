#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Users"""
import datetime as dt
import json
import time
from typing import Any, Dict, Literal, Mapping, Optional, Sequence, Tuple, TypedDict, Union

from cmk.utils.type_defs import UserId

import cmk.gui.plugins.userdb.htpasswd as htpasswd
from cmk.gui import userdb
from cmk.gui.exceptions import MKUserError
from cmk.gui.http import Response
from cmk.gui.plugins.openapi.endpoints.utils import complement_customer, update_customer_info
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    request_schemas,
    response_schemas,
)
from cmk.gui.plugins.openapi.restful_objects.parameters import USERNAME
from cmk.gui.plugins.openapi.utils import problem, ProblemException
from cmk.gui.type_defs import UserSpec
from cmk.gui.watolib.users import delete_users, edit_users

TIMESTAMP_RANGE = Tuple[float, float]


class ApiInterfaceAttributes(TypedDict, total=False):
    interface_theme: Literal["default", "dark", "light"]
    sidebar_position: Literal["left", "right"]
    navigation_bar_icons: Literal["show", "hide"]
    mega_menu_icons: Literal["topic", "entry"]
    show_mode: Literal["default", "default_show_less", "default_show_more", "enforce_show_more"]


class InternalInterfaceAttributes(TypedDict, total=False):
    ui_theme: Optional[Literal["modern-dark", "facelift"]]
    ui_sidebar_position: Optional[Literal["left"]]
    nav_hide_icons_title: Optional[Literal["hide"]]
    icons_per_item: Optional[Literal["entry"]]
    show_mode: Optional[Literal["default_show_less", "default_show_more", "enforce_show_more"]]


@Endpoint(
    constructors.object_href("user_config", "{username}"),
    "cmk/show",
    method="get",
    path_params=[USERNAME],
    etag="output",
    response_schema=response_schemas.UserObject,
)
def show_user(params):
    """Show an user"""
    username = params["username"]
    try:
        return serve_user(username)
    except KeyError:
        return problem(
            404,
            f"User '{username}' is not known.",
            "The user you asked for is not known. Please check for eventual misspellings.",
        )


@Endpoint(
    constructors.collection_href("user_config"),
    ".../collection",
    method="get",
    response_schema=response_schemas.UserCollection,
)
def list_users(params):
    """Show all users"""
    users = []
    for user_id, attrs in userdb.load_users(False).items():
        user_attributes = _internal_to_api_format(attrs)
        users.append(serialize_user(user_id, complement_customer(user_attributes)))

    return constructors.serve_json(
        constructors.collection_object(domain_type="user_config", value=users)
    )


@Endpoint(
    constructors.collection_href("user_config"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=request_schemas.CreateUser,
    response_schema=response_schemas.UserObject,
)
def create_user(params):
    """Create a user"""
    api_attrs = params["body"]
    username = api_attrs["username"]

    # The interface options must be set for a new user but we restrict the setting through the API
    internal_attrs: Dict[str, Any] = {
        "start_url": None,
        "force_authuser": False,
    }

    internal_attrs = _api_to_internal_format(internal_attrs, api_attrs, new_user=True)
    edit_users(
        {
            username: {
                "attributes": internal_attrs,
                "is_new_user": True,
            }
        }
    )
    return serve_user(username)


@Endpoint(
    constructors.object_href("user_config", "{username}"),
    ".../delete",
    method="delete",
    path_params=[USERNAME],
    output_empty=True,
)
def delete_user(params):
    """Delete a user"""
    username = params["username"]
    try:
        delete_users([username])
    except MKUserError:
        return problem(
            status=404,
            title=f'User "{username}" is not known.',
            detail="The user to delete does not exist. Please check for eventual misspellings.",
        )
    return Response(status=204)


@Endpoint(
    constructors.object_href("user_config", "{username}"),
    ".../update",
    method="put",
    path_params=[USERNAME],
    etag="both",
    request_schema=request_schemas.UpdateUser,
    response_schema=response_schemas.UserObject,
)
def edit_user(params):
    """Edit an user"""
    # last_pw_change & serial must be changed manually if edit happens
    username = params["username"]
    api_attrs = params["body"]
    internal_attrs = _api_to_internal_format(_load_user(username), api_attrs)

    if "password" in internal_attrs:
        # increase serial if password is there (regardless if there is a password change or not)
        # if password is remove, old serial remains
        internal_attrs["serial"] = internal_attrs.get("serial", 0) + 1

    edit_users(
        {
            username: {
                "attributes": internal_attrs,
                "is_new_user": False,
            }
        }
    )
    return serve_user(username)


def serve_user(user_id):
    response = Response()
    user_attributes_internal = _load_user(user_id)
    user_attributes = _internal_to_api_format(user_attributes_internal)
    response.set_data(json.dumps(serialize_user(user_id, complement_customer(user_attributes))))
    response.set_content_type("application/json")
    response.headers.add("ETag", constructors.etag_of_dict(user_attributes).to_header())
    return response


def serialize_user(user_id, attributes):
    return constructors.domain_object(
        domain_type="user_config",
        identifier=user_id,
        title=attributes["fullname"],
        extensions=_filter_keys(attributes, response_schemas.UserAttributes._declared_fields),
    )


def _api_to_internal_format(internal_attrs, api_configurations, new_user=False):
    for attr, value in api_configurations.items():
        if attr in (
            "username",
            "customer",
            "contact_options",
            "auth_option",
            "idle_timeout",
            "disable_notifications",
            "interface_options",
        ):
            continue
        internal_attrs[attr] = value

    if "customer" in api_configurations:
        internal_attrs = update_customer_info(
            internal_attrs, api_configurations["customer"], remove_provider=True
        )

    internal_attrs.update(
        _interface_options_to_internal_format(api_configurations.get("interface_options", {}))
    )
    internal_attrs.update(
        _contact_options_to_internal_format(
            api_configurations.get("contact_options"), internal_attrs.get("email")
        )
    )
    internal_attrs = _update_auth_options(
        internal_attrs, api_configurations["auth_option"], new_user=new_user
    )
    internal_attrs = _update_notification_options(
        internal_attrs, api_configurations.get("disable_notifications")
    )
    internal_attrs = _update_idle_options(internal_attrs, api_configurations.get("idle_timeout"))
    return internal_attrs


def _internal_to_api_format(internal_attrs: UserSpec) -> dict[str, Any]:
    api_attrs: dict[str, Any] = {}
    api_attrs.update(_idle_options_to_api_format(internal_attrs))
    api_attrs.update(_auth_options_to_api_format(internal_attrs))
    api_attrs.update(_notification_options_to_api_format(internal_attrs))
    interface_options = _interface_options_to_api_format(
        {  # type: ignore
            k: v
            for k, v in internal_attrs.items()
            if k
            in [
                "ui_theme",
                "ui_sidebar_position",
                "nav_hide_icons_title",
                "icons_per_item",
                "show_mode",
            ]
        }
    )
    if interface_options:
        api_attrs["interface_options"] = interface_options

    if "email" in internal_attrs:
        api_attrs.update(_contact_options_to_api_format(internal_attrs))

    if "locked" in internal_attrs:
        api_attrs["disable_login"] = internal_attrs["locked"]

    if "alias" in internal_attrs:
        api_attrs["fullname"] = internal_attrs["alias"]

    if "pager" in internal_attrs:
        api_attrs["pager_address"] = internal_attrs["pager"]

    if "enforce_pw_change" in internal_attrs:
        api_attrs["enforce_password_change"] = internal_attrs["enforce_pw_change"]

    api_attrs.update(
        {
            k: v
            for k, v in internal_attrs.items()
            if k
            in (
                "roles",
                "contactgroups",
                "language",
                "customer",
            )
        }
    )
    return api_attrs


def _idle_options_to_api_format(internal_attributes: UserSpec) -> dict[str, dict[str, Any]]:
    if "idle_timeout" in internal_attributes:
        idle_option = internal_attributes["idle_timeout"]
        if idle_option:
            idle_details = {"option": "individual", "duration": idle_option["duration"]}
        else:  # False
            idle_details = {"option": "disable"}
    else:
        idle_details = {"option": "global"}

    return {"idle_timeout": idle_details}


def _auth_options_to_api_format(internal_attributes: UserSpec) -> dict[str, dict[str, str]]:
    if "automation_secret" in internal_attributes:
        return {
            "auth_option": {
                "auth_type": "automation",
            }
        }

    if "password" in internal_attributes:
        return {"auth_option": {"auth_type": "password"}}

    return {"auth_option": {}}


def _contact_options_to_api_format(internal_attributes):
    return {
        "contact_options": {
            "email": internal_attributes["email"],
            "fallback_contact": internal_attributes.get("fallback_contact", False),
        }
    }


def _notification_options_to_api_format(internal_attributes):
    internal_notification_options = internal_attributes.get("disable_notifications")
    if not internal_notification_options:
        return {"disable_notifications": {}}

    options = {}
    if "timerange" in internal_notification_options:
        timerange = internal_notification_options["timerange"]
        options.update({"timerange": {"start_time": timerange[0], "end_time": timerange[1]}})

    if "disable" in internal_notification_options:
        options["disable"] = internal_notification_options["disable"]

    return {"disable_notifications": options}


ContactOptions = TypedDict(
    "ContactOptions",
    {
        "email": str,
        "fallback_contact": bool,
    },
    total=False,
)


def _contact_options_to_internal_format(
    contact_options: ContactOptions, current_email: Optional[str] = None
):
    updated_details: Dict[str, Union[str, bool]] = {}
    if not contact_options:
        return updated_details

    if "email" in contact_options:
        current_email = contact_options["email"]
        updated_details["email"] = current_email

    if "fallback_contact" in contact_options:
        fallback = contact_options["fallback_contact"]
        if fallback:
            if not current_email:
                raise ProblemException(
                    status=400,
                    title="Fallback contact option requires email",
                    detail="Fallback contact option requires configuration of a mail for the user",
                )
            fallback_option = True
        else:
            fallback_option = False
        updated_details["fallback_contact"] = fallback_option

    return updated_details


AuthOptions = TypedDict(
    "AuthOptions",
    {
        "auth_type": Literal["remove", "automation", "password"],
        "password": str,
        "secret": str,
        "enforce_password_change": bool,
    },
    total=False,
)


def _update_auth_options(internal_attrs, auth_options: AuthOptions, new_user=False):
    if not auth_options:
        return internal_attrs

    if auth_options.get("auth_type") == "remove":
        internal_attrs.pop("automation_secret", None)
        internal_attrs.pop("password", None)
    else:
        internal_auth_attrs = _auth_options_to_internal_format(auth_options, new_user)
        if internal_auth_attrs:
            if "automation_secret" not in internal_auth_attrs:  # new password
                internal_attrs.pop("automation_secret", None)
            # Note: changing from password to automation secret leaves enforce_pw_change
            internal_attrs.update(internal_auth_attrs)

            if internal_auth_attrs.get("enforce_password_change"):
                internal_attrs["serial"] = 1
    return internal_attrs


def _auth_options_to_internal_format(
    auth_details: AuthOptions, new_user: bool = False
) -> Dict[str, Union[int, str, bool]]:
    """Format the authentication information to be Checkmk compatible

    Args:
        auth_details:
            user provided authentication details

    Returns:
        formatted authentication details for Checkmk user_attrs

    Example:
    >>> _auth_options_to_internal_format({"auth_type": "automation", "secret": "TNBJCkwane3$cfn0XLf6p6a"})  # doctest:+ELLIPSIS
    {'automation_secret': 'TNBJCkwane3$cfn0XLf6p6a', 'password': ...}

    >>> _auth_options_to_internal_format({"auth_type": "password", "password": "password"})  # doctest:+ELLIPSIS
    {'password': ..., 'last_pw_change': ...}
    """
    internal_options: Dict[str, Union[str, bool, int]] = {}
    if not auth_details:
        return internal_options

    if auth_details["auth_type"] == "automation":
        secret = auth_details["secret"]
        internal_options["automation_secret"] = secret
        internal_options["password"] = htpasswd.hash_password(secret)
    else:  # password
        if new_user or "password" in auth_details:
            internal_options["password"] = htpasswd.hash_password(auth_details["password"])
            internal_options["last_pw_change"] = int(time.time())

        if "enforce_password_change" in auth_details:
            internal_options["enforce_pw_change"] = auth_details["enforce_password_change"]

    return internal_options


IdleDetails = TypedDict(
    "IdleDetails",
    {
        "option": Literal["disable", "individual", "global"],
        "duration": int,
    },
    total=False,
)


def _update_idle_options(internal_attrs, idle_details: IdleDetails):
    if not idle_details:
        return internal_attrs

    idle_option = idle_details["option"]
    if idle_option == "disable":
        internal_attrs["idle_timeout"] = False
    elif idle_option == "individual":
        internal_attrs["idle_timeout"] = idle_details["duration"]
    else:  # global configuration, only for update
        internal_attrs.pop("idle_timeout", None)
    return internal_attrs


def _interface_options_to_internal_format(
    api_interface_options: ApiInterfaceAttributes,
) -> InternalInterfaceAttributes:
    internal_inteface_options = InternalInterfaceAttributes()
    if theme := api_interface_options.get("interface_theme"):
        internal_inteface_options["ui_theme"] = {
            "default": None,
            "dark": "modern-dark",
            "light": "facelift",
        }[theme]
    if sidebar_position := api_interface_options.get("sidebar_position"):
        internal_inteface_options["ui_sidebar_position"] = {"right": None, "left": "left"}[
            sidebar_position
        ]
    if show_icon_titles := api_interface_options.get("navigation_bar_icons"):
        internal_inteface_options["nav_hide_icons_title"] = {"show": None, "hide": "hide"}[
            show_icon_titles
        ]
    if mega_menu_icons := api_interface_options.get("mega_menu_icons"):
        internal_inteface_options["icons_per_item"] = {"topic": None, "entry": "entry"}[
            mega_menu_icons
        ]
    if show_mode := api_interface_options.get("show_mode"):
        internal_inteface_options["show_mode"] = {
            "default": None,
            "default_show_less": "default_show_less",
            "default_show_more": "default_show_more",
            "enforce_show_more": "enforce_show_more",
        }[show_mode]
    return internal_inteface_options


def _interface_options_to_api_format(
    internal_interface_options: InternalInterfaceAttributes,
) -> ApiInterfaceAttributes:
    attributes = ApiInterfaceAttributes()
    if "ui_sidebar_position" not in internal_interface_options:
        attributes["sidebar_position"] = "right"
    else:
        attributes["sidebar_position"] = "left"

    if "nav_hide_icons_title" in internal_interface_options:
        attributes["navigation_bar_icons"] = (
            "show" if internal_interface_options["nav_hide_icons_title"] is None else "hide"
        )

    if "icons_per_item" in internal_interface_options:
        attributes["mega_menu_icons"] = (
            "topic" if internal_interface_options["icons_per_item"] is None else "entry"
        )

    if "show_mode" in internal_interface_options:
        attributes["show_mode"] = (
            "default"
            if internal_interface_options["show_mode"] is None
            else internal_interface_options["show_mode"]
        )

    if "ui_theme" not in internal_interface_options:
        attributes["interface_theme"] = "default"
    else:
        attributes["interface_theme"] = {"modern-dark": "dark", "facelift": "light"}[
            internal_interface_options["ui_theme"]  # type: ignore
        ]
    return attributes


def _load_user(username: UserId) -> UserSpec:
    """return UserSpec for username

    CAUTION: the UserSpec contains sensitive data like password hashes"""

    # TODO: verify additional edge cases
    return userdb.load_users(lock=False)[username]


TimeRange = TypedDict(
    "TimeRange",
    {
        "start_time": dt.datetime,
        "end_time": dt.datetime,
    },
)

NotificationDetails = TypedDict(
    "NotificationDetails",
    {
        "timerange": TimeRange,
        "disable": bool,
    },
    total=False,
)


def _update_notification_options(internal_attrs, notification_options: NotificationDetails):
    internal_attrs["disable_notifications"] = _notification_options_to_internal_format(
        internal_attrs.get("disable_notifications", {}), notification_options
    )
    return internal_attrs


def _notification_options_to_internal_format(
    notification_internal: Dict[str, Union[bool, TIMESTAMP_RANGE]],
    notification_api_details: NotificationDetails,
) -> Dict[str, Union[bool, TIMESTAMP_RANGE]]:
    """Format the disable notifications information to be Checkmk compatible

    Args:
        disable_notification_details:
            user provided disable notifications details

    Returns:
        formatted disable notifications details for Checkmk user_attrs

    Example:
        >>> _notification_options_to_internal_format(
        ... {},
        ... {"timerange":{
        ... 'start_time': dt.datetime.strptime("2020-01-01T13:00:00Z", "%Y-%m-%dT%H:%M:%SZ"),
        ... 'end_time': dt.datetime.strptime("2020-01-01T14:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        ... }})
        {'timerange': (1577883600.0, 1577887200.0)}
    """
    if not notification_api_details:
        return notification_internal

    if "timerange" in notification_api_details:
        notification_internal["timerange"] = _time_stamp_range(
            notification_api_details["timerange"]
        )

    if "disable" in notification_api_details:
        if notification_api_details["disable"]:
            notification_internal["disable"] = True
        else:
            notification_internal.pop("disable", None)

    return notification_internal


def _time_stamp_range(datetime_range: TimeRange) -> TIMESTAMP_RANGE:
    def timestamp(date_time):
        return dt.datetime.timestamp(date_time.replace(tzinfo=dt.timezone.utc))

    return timestamp(datetime_range["start_time"]), timestamp(datetime_range["end_time"])


def _filter_keys(
    dict_: Dict[str, Any], included_keys: Union[Sequence[str], Mapping[str, Any]]
) -> Dict[str, Any]:
    return {key: value for key, value in dict_.items() if key in included_keys}
