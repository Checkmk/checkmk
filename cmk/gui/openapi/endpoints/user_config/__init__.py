#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Users"""

import datetime as dt
import time
from collections.abc import Mapping
from typing import Any, Literal, NotRequired, TypedDict

from cmk.ccc.user import UserId

from cmk.gui.exceptions import MKUserError
from cmk.gui.fields import Username
from cmk.gui.http import Response
from cmk.gui.logged_in import user
from cmk.gui.openapi.endpoints.user_config.request_schemas import (
    CreateUser,
    UpdateUser,
    UserDismissWarning,
)
from cmk.gui.openapi.endpoints.user_config.response_schemas import UserCollection, UserObject
from cmk.gui.openapi.endpoints.utils import complement_customer, update_customer_info
from cmk.gui.openapi.restful_objects import constructors, Endpoint
from cmk.gui.openapi.restful_objects.registry import EndpointRegistry
from cmk.gui.openapi.restful_objects.type_defs import DomainObject
from cmk.gui.openapi.utils import ProblemException, serve_json
from cmk.gui.type_defs import UserSpec
from cmk.gui.userdb import (
    ConnectorType,
    htpasswd,
    load_connection_config,
    load_users,
    locked_attributes,
)
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.custom_attributes import load_custom_attrs_from_mk_file
from cmk.gui.watolib.users import (
    delete_users,
    edit_users,
    user_features_registry,
    verify_password_policy,
)

from cmk.crypto.password import Password

TIMESTAMP_RANGE = tuple[float, float]

USERNAME = {
    "username": Username(
        required=True,
        should_exist=True,
        description="An unique username for the user",
        example="cmkuser",
    )
}


class ApiInterfaceAttributes(TypedDict, total=False):
    interface_theme: Literal["default", "dark", "light"]
    sidebar_position: Literal["left", "right"]
    navigation_bar_icons: Literal["show", "hide"]
    main_menu_icons: Literal["topic", "entry"]
    show_mode: Literal["default", "default_show_less", "default_show_more", "enforce_show_more"]
    contextual_help_icon: Literal["show_icon", "hide_icon"]


class InternalInterfaceAttributes(TypedDict, total=False):
    ui_theme: Literal["modern-dark", "facelift"] | None
    ui_sidebar_position: Literal["left"] | None
    nav_hide_icons_title: Literal["hide"] | None
    icons_per_item: Literal["entry"] | None
    show_mode: Literal["default_show_less", "default_show_more", "enforce_show_more"] | None
    contextual_help_icon: Literal["hide_icon"] | None


PERMISSIONS = permissions.Perm("wato.users")

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        PERMISSIONS,
    ]
)


@Endpoint(
    constructors.object_href("user_config", "{username}"),
    "cmk/show",
    method="get",
    path_params=[USERNAME],
    etag="output",
    response_schema=UserObject,
    permissions_required=PERMISSIONS,
)
def show_user(params: Mapping[str, Any]) -> Response:
    """Show a user"""
    user.need_permission("wato.users")
    username = params["username"]
    return serve_user(username)


@Endpoint(
    constructors.collection_href("user_config"),
    ".../collection",
    method="get",
    response_schema=UserCollection,
    permissions_required=PERMISSIONS,
)
def list_users(params: Mapping[str, Any]) -> Response:
    """Show all users"""
    user.need_permission("wato.users")
    users = [serialize_user(user_id, spec) for user_id, spec in load_users(False).items()]
    return serve_json(constructors.collection_object(domain_type="user_config", value=users))


@Endpoint(
    constructors.collection_href("user_config"),
    "cmk/create",
    method="post",
    etag="output",
    request_schema=CreateUser,
    response_schema=UserObject,
    permissions_required=permissions.AllPerm(
        [
            *RW_PERMISSIONS.perms,
            permissions.Optional(permissions.Perm("wato.groups")),
        ]
    ),
)
def create_user(params: Mapping[str, Any]) -> Response:
    """Create a user

    You can pass custom attributes you defined directly in the top level JSON object of the request.
    """
    api_attrs = params["body"]
    username = api_attrs["username"]

    # The interface options must be set for a new user, but we restrict the setting through the API
    internal_attrs: UserSpec = {"force_authuser": False}

    internal_attrs = _api_to_internal_format(internal_attrs, api_attrs, new_user=True)
    edit_users(
        {
            username: {
                "attributes": internal_attrs,
                "is_new_user": True,
            }
        },
        user_features_registry.features().sites,
    )
    return serve_user(username)


@Endpoint(
    constructors.object_href("user_config", "{username}"),
    ".../delete",
    method="delete",
    path_params=[USERNAME],
    output_empty=True,
    permissions_required=RW_PERMISSIONS,
)
def delete_user(params: Mapping[str, Any]) -> Response:
    """Delete a user"""
    username = params["username"]
    delete_users([username], user_features_registry.features().sites)
    return Response(status=204)


@Endpoint(
    constructors.object_href("user_config", "{username}"),
    ".../update",
    method="put",
    path_params=[USERNAME],
    etag="both",
    request_schema=UpdateUser,
    response_schema=UserObject,
    permissions_required=RW_PERMISSIONS,
    additional_status_codes=[403],
)
def edit_user(params: Mapping[str, Any]) -> Response:
    """Edit a user

    You can pass custom attributes you defined directly in the top level JSON object of the request.
    """
    # last_pw_change & serial must be changed manually if edit happens
    username = params["username"]
    api_attrs = params["body"]

    current_attrs = _load_user(username)
    constructors.require_etag(constructors.hash_of_dict(current_attrs))
    internal_attrs = _api_to_internal_format(current_attrs, api_attrs)

    if connector_id := internal_attrs.get("connector"):
        user_locked_attributes = set(locked_attributes(connector_id))
        if user_locked_attributes:
            modified_attrs = _identify_modified_attrs(current_attrs, internal_attrs)
            locked_changes = user_locked_attributes.intersection(modified_attrs)
            if locked_changes:
                raise ProblemException(
                    status=403,
                    title="Attempt to modify locked attributes set by connector",
                    detail=f"Request attempts to modify the following locked attributes: {', '.join(locked_changes)}",
                )

    edit_users(
        {
            username: {
                "attributes": internal_attrs,
                "is_new_user": False,
            }
        },
        user_features_registry.features().sites,
    )
    return serve_user(username)


@Endpoint(
    constructors.domain_type_action_href("user_config", "dismiss-warning"),
    ".../action",
    method="post",
    tag_group="Checkmk Internal",
    request_schema=UserDismissWarning,
    output_empty=True,
)
def dismiss_user_warning(params: Mapping[str, Any]) -> Response:
    """Save a warning dismissal for the current user."""
    warnings = user.dismissed_warnings or set()
    warnings.add(params["body"]["warning"])
    user.dismissed_warnings = warnings
    return Response(status=204)


def _identify_modified_attrs(initial_attrs: UserSpec, new_attrs: dict) -> set[str]:
    modified_attrs = set()
    all_keys = set(initial_attrs.keys()).union(new_attrs.keys())
    for key in all_keys:
        if initial_attrs.get(key) != new_attrs.get(key):
            modified_attrs.add(key)
    return modified_attrs


def serve_user(user_id):
    user_spec = _load_user(user_id)
    response = serve_json(serialize_user(user_id, user_spec))
    return constructors.response_with_etag_created_from_dict(response, user_spec)


def serialize_user(
    user_id: UserId,
    user_spec: UserSpec,
) -> DomainObject:
    return constructors.domain_object(
        domain_type="user_config",
        identifier=user_id,
        title=user_spec["alias"],
        extensions=complement_customer(_internal_to_api_format(user_spec)),
    )


def _api_to_internal_format(internal_attrs, api_configurations, new_user=False):
    attrs = internal_attrs.copy()
    for attr, value in api_configurations.items():
        if attr in (
            "username",
            "customer",
            "contact_options",
            "auth_option",
            "authorized_sites",
            "idle_timeout",
            "disable_notifications",
            "interface_options",
        ):
            continue
        attrs[attr] = value

    if "customer" in api_configurations:
        attrs = update_customer_info(attrs, api_configurations["customer"], remove_provider=True)

    if (authorized_sites := api_configurations.get("authorized_sites")) is not None:
        if authorized_sites and "all" not in authorized_sites:
            attrs["authorized_sites"] = authorized_sites
        # Update with all
        elif "all" in authorized_sites and "authorized_sites" in attrs:
            del attrs["authorized_sites"]

    attrs.update(
        _interface_options_to_internal_format(api_configurations.get("interface_options", {}))
    )
    attrs.update(
        _contact_options_to_internal_format(
            api_configurations.get("contact_options"), attrs.get("email")
        )
    )
    attrs = _update_auth_options(attrs, api_configurations["auth_option"], new_user=new_user)
    attrs = _update_notification_options(attrs, api_configurations.get("disable_notifications"))
    attrs = _update_idle_options(attrs, api_configurations.get("idle_timeout"))

    if temperature_unit := api_configurations.get("temperature_unit"):
        attrs = _api_temperature_format_to_internal_format(
            attrs,
            temperature_unit,
        )

    match start_url := api_configurations.get("start_url"):
        case "welcome_page":
            attrs["start_url"] = "welcome.py"
        case "default_start_url":
            attrs["start_url"] = None
        case str():
            attrs["start_url"] = start_url
        case _:
            ...  # do not modify start_url

    return attrs


def _internal_to_api_format(
    internal_attrs: UserSpec,
) -> dict[str, Any]:
    api_attrs: dict[str, Any] = {}
    api_attrs.update(_idle_options_to_api_format(internal_attrs))
    api_attrs["auth_option"] = _auth_options_to_api_format(internal_attrs)
    api_attrs.update(_notification_options_to_api_format(internal_attrs))

    iia = InternalInterfaceAttributes()
    if "ui_theme" in internal_attrs:
        iia["ui_theme"] = internal_attrs["ui_theme"]
    if "ui_sidebar_position" in internal_attrs:
        iia["ui_sidebar_position"] = internal_attrs["ui_sidebar_position"]
    if "nav_hide_icons_title" in internal_attrs:
        iia["nav_hide_icons_title"] = internal_attrs["nav_hide_icons_title"]
    if "icons_per_item" in internal_attrs:
        iia["icons_per_item"] = internal_attrs["icons_per_item"]
    if "show_mode" in internal_attrs:
        iia["show_mode"] = internal_attrs["show_mode"]
    if interface_options := _interface_options_to_api_format(iia):
        api_attrs["interface_options"] = interface_options

    if "email" in internal_attrs:
        api_attrs.update(_contact_options_to_api_format(internal_attrs))

    if "locked" in internal_attrs:
        api_attrs["disable_login"] = internal_attrs["locked"]

    if "alias" in internal_attrs:
        api_attrs["fullname"] = internal_attrs["alias"]

    if "pager" in internal_attrs:
        api_attrs["pager_address"] = internal_attrs["pager"]

    if "temperature_unit" in internal_attrs:
        api_attrs["temperature_unit"] = _internal_temperature_format_to_api_format(
            internal_attrs["temperature_unit"]
        )

    match start_url := internal_attrs.get("start_url"):
        case None:
            api_attrs["start_url"] = "default_start_url"
        case "welcome.py":
            api_attrs["start_url"] = "welcome_page"
        case _:
            api_attrs["start_url"] = start_url

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
    custom_attrs = load_custom_attrs_from_mk_file(lock=False)["user"]
    for attr in custom_attrs:
        if (name := attr["name"]) in internal_attrs:
            # monkeypatch a typed dict, what can go wrong
            api_attrs[name] = internal_attrs[name]  # type: ignore[literal-required]
    return api_attrs


def _idle_options_to_api_format(
    internal_attributes: UserSpec,
) -> dict[str, dict[str, Any]]:
    if "idle_timeout" in internal_attributes:
        idle_option = internal_attributes["idle_timeout"]
        if idle_option:
            idle_details = {"option": "individual", "duration": idle_option}
        else:  # False
            idle_details = {"option": "disable"}
    else:
        idle_details = {"option": "global"}

    return {"idle_timeout": idle_details}


class APIAuthOption(TypedDict, total=False):
    # TODO: this should be adapted with the introduction of an enum
    auth_type: Literal["automation", "password", "saml2", "ldap"]
    store_automation_secret: NotRequired[bool]
    enforce_password_change: bool


def _auth_options_to_api_format(internal_attributes: UserSpec) -> APIAuthOption:
    # TODO: the default ConnectorType.HTPASSWD is currently a bug #CMK-12723 but not wrong
    connector = internal_attributes.get("connector", ConnectorType.HTPASSWD)
    if connector == ConnectorType.HTPASSWD:
        if internal_attributes.get("is_automation_user", False):
            return APIAuthOption(
                auth_type="automation",
                store_automation_secret=internal_attributes.get("store_automation_secret", False),
            )
        elif "password" in internal_attributes:
            return APIAuthOption(
                auth_type="password",
                enforce_password_change=bool(internal_attributes.get("enforce_pw_change", False)),
            )

    for connection in load_connection_config():
        if connection["id"] == connector:
            return APIAuthOption(auth_type=connection["type"])

    # We probably should raise?
    return APIAuthOption()


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


class ContactOptions(TypedDict, total=False):
    email: str
    fallback_contact: bool


def _contact_options_to_internal_format(
    contact_options: ContactOptions, current_email: str | None = None
) -> dict[str, str | bool]:
    updated_details: dict[str, str | bool] = {}
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


class AuthOptions(TypedDict, total=False):
    auth_type: Literal["remove", "automation", "password"]
    password: str
    secret: str
    enforce_password_change: bool


def _update_auth_options(
    internal_attrs: dict[str, int | str | bool],
    auth_options: AuthOptions,
    new_user: bool = False,
) -> dict[str, int | str | bool]:
    """Update the internal attributes with the authentication options (used for create and update)

    Notes:
        * the REST API currently only allows creating users with htpasswd connector (not LDAP
        or SAML2)
            * the connector must also be set even if there is no authentication specified
    """
    if not auth_options:
        if new_user:
            internal_attrs["connector"] = ConnectorType.HTPASSWD
        return internal_attrs

    if auth_options.get("auth_type") == "remove":
        internal_attrs.pop("automation_secret", None)
        internal_attrs.pop("store_automation_secret", None)
        internal_attrs.pop("password", None)
        internal_attrs["is_automation_user"] = False
        internal_attrs["serial"] = 1
    else:
        internal_auth_attrs = _auth_options_to_internal_format(auth_options)
        if new_user and "password" not in internal_auth_attrs:
            # "password" (the password hash) is set for both automation users and regular users,
            # although automation users don't really use it yet (but they should, eventually).
            raise MKUserError(None, "No authentication details provided for new user")

        if internal_auth_attrs:
            if "automation_secret" not in internal_auth_attrs:  # new password
                internal_attrs.pop("automation_secret", None)
            # Note: Changing from password to automation secret leaves enforce_pw_change, although
            #       it will be ignored for automation users.
            internal_attrs.update(internal_auth_attrs)

            if internal_auth_attrs.get("enforce_password_change"):
                internal_attrs["serial"] = 1

            if "password" in auth_options or "secret" in auth_options:
                internal_attrs["serial"] = 1

        internal_attrs["connector"] = ConnectorType.HTPASSWD
    return internal_attrs


def _auth_options_to_internal_format(
    auth_details: AuthOptions,
) -> dict[str, int | str | bool]:
    """Format the authentication information to be Checkmk compatible

    Args:
        auth_details:
            user provided authentication details

    Returns:
        formatted authentication details for Checkmk user_attrs

    Examples:

    Setting a new automation secret:

        >>> _auth_options_to_internal_format(
        ...     {"auth_type": "automation", "secret": "TNBJCkwane3$cfn0XLf6p6a"}
        ... )  # doctest:+ELLIPSIS
        {'password': ..., 'automation_secret': 'TNBJCkwane3$cfn0XLf6p6a', 'store_automation_secret': False, 'is_automation_user': True, 'last_pw_change': ...}

    Enforcing password change without changing the password:

        >>> _auth_options_to_internal_format(
        ...     {"auth_type": "password", "enforce_password_change": True}
        ... )
        {'enforce_pw_change': True}

    Empty password is not allowed and passwords result in MKUserErrors:

        >>> _auth_options_to_internal_format(
        ...     {"auth_type": "password", "enforce_password_change": True, "password": ""}
        ... )
        Traceback (most recent call last):
        ...
        cmk.gui.exceptions.MKUserError: Password must not be empty

        >>> _auth_options_to_internal_format(
        ...     {"auth_type": "password", "enforce_password_change": True, "password": "\\0"}
        ... )
        Traceback (most recent call last):
        ...
        cmk.gui.exceptions.MKUserError: Password must not contain null bytes
    """
    internal_options: dict[str, str | bool | int] = {}
    if not auth_details:
        return internal_options

    auth_type = auth_details["auth_type"]
    assert auth_type in [
        "automation",
        "password",
    ]  # assuming remove was handled above...

    password_field: Literal["secret", "password"] = (
        "secret" if auth_type == "automation" else "password"
    )
    if password_field in auth_details:
        try:
            password = Password(auth_details[password_field])
        except ValueError as e:
            raise MKUserError(password_field, str(e))

        # Re-using the htpasswd wrapper for hash_password here, so we get MKUserErrors.
        internal_options["password"] = htpasswd.hash_password(password)

        if auth_type == "password":
            verify_password_policy(password)
            internal_options["is_automation_user"] = False

        if auth_type == "automation":
            internal_options["automation_secret"] = password.raw
            internal_options["store_automation_secret"] = bool(
                auth_details.get("store_automation_secret", False)
            )
            internal_options["is_automation_user"] = True

        # In contrast to enforce_pw_change, the maximum password age is enforced for automation
        # users as well. So set this for both kinds of users.
        internal_options["last_pw_change"] = int(time.time())

    if "enforce_password_change" in auth_details:
        # Note that enforce_pw_change cannot be set for automation users. We rely on the schema to
        # ensure that.
        internal_options["enforce_pw_change"] = auth_details["enforce_password_change"]

    return internal_options


class IdleDetails(TypedDict, total=False):
    option: Literal["disable", "individual", "global"]
    duration: int


def _update_idle_options(
    internal_attrs: dict[str, Any], idle_details: IdleDetails
) -> dict[str, Any]:
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
        internal_inteface_options["ui_sidebar_position"] = {
            "right": None,
            "left": "left",
        }[sidebar_position]
    if show_icon_titles := api_interface_options.get("navigation_bar_icons"):
        internal_inteface_options["nav_hide_icons_title"] = {
            "show": None,
            "hide": "hide",
        }[show_icon_titles]
    if main_menu_icons := api_interface_options.get("main_menu_icons"):
        internal_inteface_options["icons_per_item"] = {"topic": None, "entry": "entry"}[
            main_menu_icons
        ]
    if show_mode := api_interface_options.get("show_mode"):
        internal_inteface_options["show_mode"] = {
            "default": None,
            "default_show_less": "default_show_less",
            "default_show_more": "default_show_more",
            "enforce_show_more": "enforce_show_more",
        }[show_mode]

    if help_icon := api_interface_options.get("contextual_help_icon"):
        internal_inteface_options["contextual_help_icon"] = (
            None if help_icon == "show_icon" else "hide_icon"
        )

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
        attributes["main_menu_icons"] = (
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
    elif internal_interface_options["ui_theme"] == "modern-dark":
        attributes["interface_theme"] = "dark"
    elif internal_interface_options["ui_theme"] == "facelift":
        attributes["interface_theme"] = "light"
    else:
        # TODO: What should *really* be done in case of None?
        pass

    attributes["contextual_help_icon"] = (
        "show_icon"
        if internal_interface_options.get("contextual_help_icon") is None
        else "hide_icon"
    )

    return attributes


def _load_user(username: UserId) -> UserSpec:
    """return UserSpec for username

    CAUTION: the UserSpec contains sensitive data like password hashes"""

    # TODO: verify additional edge cases
    return load_users(lock=False)[username]


class TimeRange(TypedDict):
    start_time: dt.datetime
    end_time: dt.datetime


class NotificationDetails(TypedDict, total=False):
    timerange: TimeRange
    disable: bool


def _update_notification_options(
    internal_attrs: dict[str, Any], notification_options: NotificationDetails
) -> dict[str, Any]:
    internal_attrs["disable_notifications"] = _notification_options_to_internal_format(
        internal_attrs.get("disable_notifications", {}), notification_options
    )
    return internal_attrs


def _notification_options_to_internal_format(
    notification_internal: dict[str, bool | TIMESTAMP_RANGE],
    notification_api_details: NotificationDetails,
) -> dict[str, bool | TIMESTAMP_RANGE]:
    """Format disable notifications information to be Checkmk compatible

    Args:
        notification_api_details:
            user provided notifications details

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
        return dt.datetime.timestamp(date_time.replace(tzinfo=dt.UTC))

    return timestamp(datetime_range["start_time"]), timestamp(datetime_range["end_time"])


def _api_temperature_format_to_internal_format(
    internal_attrs: Mapping[str, object],
    temperature_unit: str,
) -> dict[str, object]:
    """
    >>> _api_temperature_format_to_internal_format({'a': 'b'}, 'default')
    {'a': 'b', 'temperature_unit': None}
    >>> _api_temperature_format_to_internal_format({'a': 'b'}, 'celsius')
    {'a': 'b', 'temperature_unit': 'celsius'}
    """
    return {
        **internal_attrs,
        "temperature_unit": None if temperature_unit == "default" else temperature_unit,
    }


def _internal_temperature_format_to_api_format(internal_temperature: str | None) -> str:
    """
    >>> _internal_temperature_format_to_api_format('celsius')
    'celsius'
    >>> _internal_temperature_format_to_api_format(None)
    'default'
    """
    return "default" if not internal_temperature else internal_temperature


def register(endpoint_registry: EndpointRegistry, *, ignore_duplicates: bool) -> None:
    endpoint_registry.register(show_user, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(list_users, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(create_user, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(delete_user, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(edit_user, ignore_duplicates=ignore_duplicates)
    endpoint_registry.register(dismiss_user_warning, ignore_duplicates=ignore_duplicates)
