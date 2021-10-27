#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Users"""
import datetime as dt
import json
import time
from typing import Any, Dict, Literal, Optional, Tuple, TypedDict, Union

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
from cmk.gui.watolib.users import delete_users, edit_users

TIMESTAMP_RANGE = Tuple[float, float]


@Endpoint(
    constructors.object_href("user_config", "{username}"),
    "cmk/show",
    method="get",
    path_params=[USERNAME],
    etag="output",
    response_schema=response_schemas.DomainObject,
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
    response_schema=response_schemas.DomainObjectCollection,
)
def list_users(params):
    """Show all users"""
    user_collection = {
        "id": "user",
        "domainType": "user_config",
        "value": [
            constructors.collection_item(
                domain_type="user_config",
                title=attrs["alias"],
                identifier=user_id,
            )
            for user_id, attrs in userdb.load_users(False).items()
        ],
        "links": [constructors.link_rel("self", constructors.collection_href("user_config"))],
    }
    return constructors.serve_json(user_collection)


@Endpoint(
    constructors.collection_href("user_config"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=request_schemas.CreateUser,
    response_schema=response_schemas.DomainObject,
)
def create_user(params):
    """Create a user"""
    api_attrs = params["body"]
    username = api_attrs["username"]

    # The interface options must be set for a new user but we restrict the setting through the API
    internal_attrs: Dict[str, Any] = {
        "ui_theme": None,
        "ui_sidebar_position": None,
        "nav_hide_icons_title": None,
        "icons_per_item": None,
        "show_mode": None,
        "start_url": None,
        "force_authuser": False,
        "enforce_pw_change": False,
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
            404,
            f'User "{username}" is not known.',
            "The user to delete does not exist. Please check for eventual misspellings.",
        )
    return Response(status=204)


@Endpoint(
    constructors.object_href("user_config", "{username}"),
    ".../update",
    method="put",
    path_params=[USERNAME],
    etag="both",
    request_schema=request_schemas.UpdateUser,
    response_schema=response_schemas.DomainObject,
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
        extensions={
            "attributes": attributes,
        },
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
        ):
            continue
        internal_attrs[attr] = value

    if "customer" in api_configurations:
        internal_attrs = update_customer_info(
            internal_attrs, api_configurations["customer"], remove_provider=True
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


def _internal_to_api_format(internal_attrs):
    api_attrs = {}
    api_attrs.update(_idle_options_to_api_format(internal_attrs))
    api_attrs.update(_auth_options_to_api_format(internal_attrs))
    api_attrs.update(_contact_options_to_api_format(internal_attrs))
    api_attrs.update(_notification_options_to_api_format(internal_attrs))

    if "locked" in internal_attrs:
        api_attrs["disable_login"] = internal_attrs["locked"]

    if "alias" in internal_attrs:
        api_attrs["fullname"] = internal_attrs["alias"]

    if "pager" in internal_attrs:
        api_attrs["pager_address"] = internal_attrs["pager"]

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


def _idle_options_to_api_format(internal_attributes):
    if "idle_timeout" in internal_attributes:
        idle_option = internal_attributes["idle_timeout"]
        if idle_option:
            idle_details = {"option": "individual", "duration": idle_option["duration"]}
        else:  # False
            idle_details = {"option": "disable"}
    else:
        idle_details = {"option": "global"}

    return {"idle_timeout": idle_details}


def _auth_options_to_api_format(internal_attributes):
    if "automation_secret" in internal_attributes:
        return {
            "auth_option": {
                "auth_type": "automation",
                "secret": internal_attributes["automation_secret"],
            }
        }

    if "password" in internal_attributes:
        return {
            "auth_option": {"auth_type": "password", "password": internal_attributes["password"]}
        }

    return {"auth_option": {}}


def _contact_options_to_api_format(internal_attributes):
    return {
        "contact_options": {
            "email": internal_attributes["email"],
            "fallback_contact": internal_attributes["fallback_contact"],
        }
    }


def _notification_options_to_api_format(internal_attributes):
    internal_notification_options = internal_attributes.get("disable_notifications")
    if not internal_notification_options:
        return {"disable_notifications": {}}

    def _datetime_range(timestamp):
        return dt.datetime.fromtimestamp(timestamp, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    options = {}
    if "timerange" in internal_notification_options:
        timerange = internal_notification_options["timerange"]
        options.update(
            {
                "timerange": {
                    "start_time": _datetime_range(timerange[0]),
                    "end_time": _datetime_range(timerange[1]),
                }
            }
        )

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
        internal_auth_attrs = _auth_options_to_internal_format(
            auth_options, enforce_pw_change=new_user
        )
        if internal_auth_attrs:
            if "automation_secret" not in internal_auth_attrs:  # new password
                internal_attrs.pop("automation_secret", None)
            # Note: changing from password to automation secret leaves enforce_pw_change
            internal_attrs.update(internal_auth_attrs)

            if new_user:
                internal_attrs["serial"] = 1
    return internal_attrs


def _auth_options_to_internal_format(
    auth_details: AuthOptions, enforce_pw_change: bool = False
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

    >>> _auth_options_to_internal_format({"auth_type": "password", "password": "password"}, enforce_pw_change=True)  # doctest:+ELLIPSIS
    {'password': ..., 'last_pw_change': ..., 'enforce_pw_change': True}
    """
    auth_options: Dict[str, Union[str, bool, int]] = {}
    if not auth_details:
        return auth_options

    if auth_details["auth_type"] == "automation":
        secret = auth_details["secret"]
        auth_options["automation_secret"] = secret
        auth_options["password"] = htpasswd.hash_password(secret)
    else:  # password
        auth_options["password"] = htpasswd.hash_password(auth_details["password"])
        auth_options["last_pw_change"] = int(time.time())

        # this can be configured in WATO but we enforce this here
        if enforce_pw_change:
            auth_options["enforce_pw_change"] = True

    return auth_options


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


def _load_user(username):
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
