#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Users"""
import json
import datetime as dt
from typing import Dict, Tuple, Union, Any
import time

from cmk.gui.http import Response
from cmk.gui.exceptions import MKUserError
from cmk.gui.plugins.openapi.restful_objects import (
    constructors,
    Endpoint,
    request_schemas,
    response_schemas,
)

import cmk.gui.userdb as userdb
import cmk.gui.plugins.userdb.htpasswd as htpasswd
from cmk.gui.plugins.openapi import fields
from cmk.gui.watolib.users import edit_users, delete_users
from cmk.gui.plugins.openapi.utils import problem

USERNAME = {
    'username': fields.String(
        description="The username to delete",
        example='user',
    )
}

TIMESTAMP_RANGE = Tuple[float, float]


@Endpoint(constructors.object_href('user_config', '{username}'),
          'cmk/show',
          method='get',
          path_params=[USERNAME],
          etag='output',
          response_schema=response_schemas.DomainObject)
def show_user(params):
    """Show an user"""
    username = params['username']
    try:
        return serve_user(username)
    except KeyError:
        return problem(
            404,
            f"User '{username}' is not known.",
            'The user you asked for is not known. Please check for eventual misspellings.',
        )


@Endpoint(constructors.collection_href('user_config'),
          'cmk/create',
          method='post',
          etag='output',
          request_schema=request_schemas.CreateUser,
          response_schema=response_schemas.DomainObject)
def create_user(params):
    """Create a user"""
    body = params['body']
    username = body['username']

    # The interface options must be set for a new user but we restrict the setting through the API
    user_attrs: Dict[str, Any] = {
        "ui_theme": None,
        "ui_sidebar_position": None,
        "nav_hide_icons_title": None,
        "icons_per_item": None,
        "show_mode": None,
        "start_url": None,
        "force_authuser": False,
        "enforce_pw_change": False,
    }

    for attr, value in body.items():
        if attr in (
                "username",
                "contact_options",
                "auth_option",
                "idle_options",
                "disable_notifications",
        ):
            continue
        user_attrs[attr] = value

    user_attrs.update(body["contact_options"])
    auth_details = _parse_auth_options(body["auth_option"], enforce_pw_change=True)
    if auth_details:
        user_attrs.update(auth_details)
        user_attrs["serial"] = 1
    user_attrs["disable_notifications"] = _parse_notification_options(body["disable_notifications"])

    if "idle_timeout" in body:
        idle_details = body["idle_timeout"]
        idle_option = idle_details["option"]
        if idle_option == "disable":
            user_attrs["idle_timeout"] = False
        elif idle_option == "individual":
            user_attrs["idle_timeout"] = idle_details["duration"]

    edit_users({username: {
        "attributes": user_attrs,
        "is_new_user": True,
    }})
    return serve_user(username)


@Endpoint(constructors.object_href('user_config', '{username}'),
          '.../delete',
          method='delete',
          path_params=[USERNAME],
          etag='input',
          output_empty=True)
def delete_user(params):
    """Delete a user"""
    username = params['username']
    try:
        delete_users([username])
    except MKUserError:
        return problem(
            404, f'User "{username}" is not known.',
            'The user to delete does not exist. Please check for eventual misspellings.')
    return Response(status=204)


@Endpoint(constructors.object_href('user_config', '{username}'),
          '.../update',
          method='put',
          path_params=[USERNAME],
          etag='both',
          request_schema=request_schemas.UpdateUser,
          response_schema=response_schemas.DomainObject)
def edit_user(params):
    """Edit an user"""
    # last_pw_change & serial must be changed manually if edit happens
    username = params['username']
    body = params['body']
    user_attrs = _load_user(username)

    for attr, value in body.items():
        if attr in (
                "contact_options",
                "auth_option",
                "idle_options",
                "disable_notifications",
        ):
            continue
        user_attrs[attr] = value

    auth_options = body['auth_option']
    if auth_options.get("auth_type") == "remove":
        user_attrs.pop("automation_secret", None)
        user_attrs.pop("password", None)
    else:
        updated_auth_options = _parse_auth_options(auth_options)
        if updated_auth_options:
            if "automation_secret" not in updated_auth_options:  # new password
                user_attrs.pop("automation_secret", None)
            # Note: changing from password to automation secret leaves enforce_pw_change
            user_attrs.update(updated_auth_options)

    if "password" in user_attrs:
        # increase serial if password is there (regardless if there is a password change or not)
        # if password is remove, old serial remains
        user_attrs["serial"] = user_attrs.get("serial", 0) + 1

    if "disable_notifications" in body:
        user_attrs.setdefault("disable_notifications",
                              {}).update(_parse_notification_options(body["disable_notifications"]))

    if "idle_timeout" in body:
        idle_options = body["idle_timeout"]
        idle_option = idle_options["option"]
        if idle_option == "disable":
            user_attrs["idle_timeout"] = False
        elif idle_option == "individual":
            user_attrs["idle_timeout"] = idle_options["duration"]
        else:  # global configuration
            user_attrs.pop("idle_timeout", None)

    edit_users({username: {
        "attributes": user_attrs,
        "is_new_user": False,
    }})
    return serve_user(username)


def serve_user(user_id):
    response = Response()
    user_attributes = user_config_attributes(user_id)
    response.set_data(json.dumps(serialize_user(user_id, user_attributes)))
    response.set_content_type('application/json')
    response.headers.add('ETag', constructors.etag_of_dict(user_attributes).to_header())
    return response


def serialize_user(user_id, attributes):
    return constructors.domain_object(
        domain_type='user_config',
        identifier=user_id,
        title=attributes["alias"],
        extensions={
            'attributes': attributes,
        },
    )


def user_config_attributes(user_id):
    return {
        k: v for k, v in _load_user(user_id).items() if k not in (
            "nav_hide_icons_title",
            "icons_per_item",
            "show_mode",
            "ui_theme",
            "ui_sidebar_position",
            "start_url",
            "force_authuser",
        )
    }


def _load_user(username):
    # TODO: verify additional edge cases
    return userdb.load_users(True)[username]


def _parse_auth_options(auth_details: Dict[str, Union[str, bool]],
                        enforce_pw_change: bool = False) -> Dict[str, Union[int, str, bool]]:
    """Format the authentication information to be Checkmk compatible

    Args:
        auth_details:
            user provided authentication details

    Returns:
        formatted authentication details for Checkmk user_attrs

    Example:
    >>> _parse_auth_options({"auth_type": "automation", "secret": "TNBJCkwane3$cfn0XLf6p6a"})  # doctest:+ELLIPSIS
    {'automation_secret': 'TNBJCkwane3$cfn0XLf6p6a', 'password': ...}

    >>> _parse_auth_options({"auth_type": "password", "password": "password"}, enforce_pw_change=True)  # doctest:+ELLIPSIS
    {'password': ..., 'last_pw_change': ..., 'enforce_pw_change': True}
    """
    auth_options: Dict[str, Union[str, bool, int]] = {}
    if auth_details:
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


def _parse_notification_options(
        disable_notification_details: Dict[str, Any]) -> Dict[str, Union[bool, TIMESTAMP_RANGE]]:
    """Format the disable notifications information to be Checkmk compatible

    Args:
        disable_notification_details:
            user provided disable notifications details

    Returns:
        formatted disable notifications details for Checkmk user_attrs

    Example:
        >>> _parse_notification_options(
        ... {"timerange":{
        ... 'start_time': dt.datetime.strptime("2020-01-01T13:00:00Z", "%Y-%m-%dT%H:%M:%SZ"),
        ... 'end_time': dt.datetime.strptime("2020-01-01T14:00:00Z", "%Y-%m-%dT%H:%M:%SZ")
        ... }})
        {'timerange': (1577883600.0, 1577887200.0)}
    """
    parsed_options: Dict[str, Union[bool, TIMESTAMP_RANGE]] = {}
    if "timerange" in disable_notification_details:
        parsed_options["timerange"] = _time_stamp_range(disable_notification_details["timerange"])
    if "disabled" in disable_notification_details:
        parsed_options["disabled"] = disable_notification_details["disabled"]
    return parsed_options


def _time_stamp_range(datetime_range: Dict[str, dt.datetime]) -> TIMESTAMP_RANGE:
    def timestamp(date_time):
        return dt.datetime.timestamp(date_time.replace(tzinfo=dt.timezone.utc))

    return timestamp(datetime_range["start_time"]), timestamp(datetime_range["end_time"])
