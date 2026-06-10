#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared helpers for the user_config endpoints.

The conversion functions between the public API format and the Checkmk internal ``UserSpec``
format are ported from the legacy marshmallow endpoint module. They operate on plain dictionaries
that mirror the data the marshmallow schemas used to produce/consume.
"""

import datetime as dt
import time
from collections.abc import Mapping
from typing import Any, Literal, NotRequired, TypedDict

from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId
from cmk.crypto.password import Password, PasswordPolicy
from cmk.gui.exceptions import MKUserError
from cmk.gui.logged_in import user
from cmk.gui.openapi.api_endpoints.user_config.models.response_models import (
    AuthOptionOutputModel,
    ConcreteDisabledNotificationsModel,
    ConcreteUserContactOptionModel,
    ConcreteUserInterfaceAttributesModel,
    DateTimeRangeModel,
    UserAttributesModel,
    UserIdleOptionModel,
    UserObject,
)
from cmk.gui.openapi.endpoints.utils import complement_customer, update_customer_info
from cmk.gui.openapi.framework import ApiContext, ETag
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.type_defs import UserSpec
from cmk.gui.user_sites import activation_sites
from cmk.gui.userdb import (
    ConnectorType,
    htpasswd,
    load_connection_config,
    load_users,
)
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.audit_log import make_audit_log_change_hook
from cmk.gui.watolib.custom_attributes import load_custom_attrs_from_mk_file
from cmk.gui.watolib.pending_changes import (
    index_update_change_hook,
    PendingChanges,
    PendingChangesStore,
)
from cmk.gui.watolib.users import verify_password_policy

TIMESTAMP_RANGE = tuple[float, float]

PERMISSIONS = permissions.Perm("wato.users")

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        PERMISSIONS,
    ]
)


def username_should_exist(value: str) -> UserId:
    user.need_permission("wato.users")
    try:
        user_id = UserId(value)
    except ValueError:
        raise ValueError(f"Username {value!r} is not a valid checkmk username")
    if user_id not in load_users(lock=False):
        raise ValueError(f"Username missing: {value!r}")
    return user_id


def username_should_not_exist(value: str) -> UserId:
    user.need_permission("wato.users")
    try:
        user_id = UserId(value)
    except ValueError:
        raise ValueError(f"Username {value!r} is not a valid checkmk username")
    if user_id in load_users(lock=False):
        raise ValueError(f"Username {value!r} already exists")
    return user_id


def load_user(username: UserId) -> UserSpec:
    """Return the UserSpec for username.

    CAUTION: the UserSpec contains sensitive data like password hashes."""
    return load_users(lock=False)[username]


def user_etag(user_spec: UserSpec) -> ETag:
    return ETag(dict(user_spec))


def make_pending_changes(api_context: ApiContext) -> PendingChanges:
    return PendingChanges(
        activation_sites=activation_sites(api_context.config.sites),
        local_site=omd_site(),
        acting_user=api_context.user_id,
        store=PendingChangesStore(),
        hooks=(
            make_audit_log_change_hook(use_git=api_context.config.wato_use_git),
            index_update_change_hook,
        ),
    )


# ---------------------------------------------------------------------------------------------
# Internal TypedDicts (ported from the legacy module)
# ---------------------------------------------------------------------------------------------


class ApiInterfaceAttributes(TypedDict, total=False):
    interface_theme: Literal["default", "dark", "light"]
    sidebar_position: Literal["left", "right"]
    navigation_bar_icons: Literal["show", "hide"]
    main_menu_icons: Literal["topic", "entry"]
    mega_menu_icons: Literal["topic", "entry"]  # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    show_mode: Literal["default", "default_show_less", "default_show_more", "enforce_show_more"]
    contextual_help_icon: Literal["show_icon", "hide_icon"]
    navbar_changes_action: Literal["full_page", "slideout", "slideout_ask"]


class InternalInterfaceAttributes(TypedDict, total=False):
    ui_theme: Literal["modern-dark", "facelift"] | None
    ui_sidebar_position: Literal["left"] | None
    nav_hide_icons_title: Literal["hide"] | None
    icons_per_item: Literal["entry"] | None
    show_mode: Literal["default_show_less", "default_show_more", "enforce_show_more"] | None
    contextual_help_icon: Literal["hide_icon"] | None
    navbar_changes_action: Literal["full_page", "slideout"] | None


class APIAuthOption(TypedDict):
    # Every key is optional: each of the _auth_options_to_api_format branches sets only a subset.
    # TODO: this should be adapted with the introduction of an enum
    auth_type: NotRequired[Literal["automation", "password", "saml2", "ldap"]]
    store_automation_secret: NotRequired[bool]
    enforce_password_change: NotRequired[bool]


class ContactOptions(TypedDict, total=False):
    email: str
    fallback_contact: bool


class AuthOptions(TypedDict, total=False):
    auth_type: Literal["remove", "automation", "password"]
    password: str
    secret: str
    store_automation_secret: bool
    enforce_password_change: bool


class IdleDetails(TypedDict, total=False):
    option: Literal["disable", "individual", "global"]
    duration: int


class TimeRange(TypedDict):
    start_time: dt.datetime
    end_time: dt.datetime


class NotificationDetails(TypedDict, total=False):
    timerange: TimeRange
    disable: bool


# ---------------------------------------------------------------------------------------------
# API -> internal conversion
# ---------------------------------------------------------------------------------------------


def api_to_internal_format(
    internal_attrs: dict[str, Any],
    api_configurations: Mapping[str, Any],
    password_policy: PasswordPolicy,
    new_user: bool = False,
) -> dict[str, Any]:
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
    attrs = _update_auth_options(
        attrs, api_configurations["auth_option"], password_policy, new_user=new_user
    )
    attrs = _update_notification_options(attrs, api_configurations.get("disable_notifications"))
    attrs = _update_idle_options(attrs, api_configurations.get("idle_timeout"))

    if temperature_unit := api_configurations.get("temperature_unit"):
        attrs = _api_temperature_format_to_internal_format(attrs, temperature_unit)

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


def _contact_options_to_internal_format(
    contact_options: ContactOptions | None, current_email: str | None = None
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
                raise MKUserError(
                    None,
                    "Fallback contact option requires configuration of a mail for the user",
                )
            fallback_option = True
        else:
            fallback_option = False
        updated_details["fallback_contact"] = fallback_option

    return updated_details


def _update_auth_options(
    internal_attrs: dict[str, Any],
    auth_options: AuthOptions,
    password_policy: PasswordPolicy,
    new_user: bool = False,
) -> dict[str, Any]:
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
        internal_auth_attrs = _auth_options_to_internal_format(auth_options, password_policy)
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
    auth_details: AuthOptions, password_policy: PasswordPolicy
) -> dict[str, int | str | bool]:
    """Convert authentication information received via REST API to the Checkmk internal format"""
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
            verify_password_policy(password, "password", password_policy)
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


def _update_idle_options(
    internal_attrs: dict[str, Any], idle_details: IdleDetails | None
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
    internal_interface_options = InternalInterfaceAttributes()
    if theme := api_interface_options.get("interface_theme"):
        internal_interface_options["ui_theme"] = {
            "default": None,
            "dark": "modern-dark",
            "light": "facelift",
        }[theme]
    if sidebar_position := api_interface_options.get("sidebar_position"):
        internal_interface_options["ui_sidebar_position"] = {
            "right": None,
            "left": "left",
        }[sidebar_position]
    if show_icon_titles := api_interface_options.get("navigation_bar_icons"):
        internal_interface_options["nav_hide_icons_title"] = {
            "show": None,
            "hide": "hide",
        }[show_icon_titles]

    # TODO: DEPRECATED(18295) remove "mega_menu_icons"
    icons_per_item = api_interface_options.get("main_menu_icons", None)
    if icons_per_item is None:
        icons_per_item = api_interface_options.get("mega_menu_icons", None)
    if icons_per_item is not None:
        internal_interface_options["icons_per_item"] = {"topic": None, "entry": "entry"}[
            icons_per_item
        ]

    if show_mode := api_interface_options.get("show_mode"):
        internal_interface_options["show_mode"] = {
            "default": None,
            "default_show_less": "default_show_less",
            "default_show_more": "default_show_more",
            "enforce_show_more": "enforce_show_more",
        }[show_mode]

    if help_icon := api_interface_options.get("contextual_help_icon"):
        internal_interface_options["contextual_help_icon"] = (
            None if help_icon == "show_icon" else "hide_icon"
        )

    match api_interface_options.get("navbar_changes_action"):
        case "full_page":
            internal_interface_options["navbar_changes_action"] = "full_page"
        case "slideout":
            internal_interface_options["navbar_changes_action"] = "slideout"
        case "slideout_ask":
            internal_interface_options["navbar_changes_action"] = None
        case _:
            ...

    return internal_interface_options


def _update_notification_options(
    internal_attrs: dict[str, Any], notification_options: NotificationDetails | None
) -> dict[str, Any]:
    internal_attrs["disable_notifications"] = _notification_options_to_internal_format(
        internal_attrs.get("disable_notifications", {}), notification_options
    )
    return internal_attrs


def _notification_options_to_internal_format(
    notification_internal: dict[str, bool | TIMESTAMP_RANGE],
    notification_api_details: NotificationDetails | None,
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
    def timestamp(date_time: dt.datetime) -> float:
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


def identify_modified_attrs(initial_attrs: UserSpec, new_attrs: dict[str, Any]) -> set[str]:
    initial: dict[str, Any] = dict(initial_attrs)
    modified_attrs = set()
    for key in set(initial.keys()) | set(new_attrs.keys()):
        if initial.get(key) != new_attrs.get(key):
            modified_attrs.add(key)
    return modified_attrs


# ---------------------------------------------------------------------------------------------
# internal -> API conversion
# ---------------------------------------------------------------------------------------------


def _internal_to_api_format(internal_attrs: UserSpec) -> dict[str, Any]:
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
    if "navbar_changes_action" in internal_attrs:
        iia["navbar_changes_action"] = internal_attrs["navbar_changes_action"]
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


def _contact_options_to_api_format(internal_attributes: UserSpec) -> dict[str, Any]:
    return {
        "contact_options": {
            "email": internal_attributes["email"],
            "fallback_contact": internal_attributes.get("fallback_contact", False),
        }
    }


def _notification_options_to_api_format(internal_attributes: UserSpec) -> dict[str, Any]:
    internal_notification_options: Mapping[str, Any] = (
        internal_attributes.get("disable_notifications") or {}
    )
    if not internal_notification_options:
        return {"disable_notifications": {}}

    options: dict[str, Any] = {}
    if "timerange" in internal_notification_options:
        timerange = internal_notification_options["timerange"]
        options.update({"timerange": {"start_time": timerange[0], "end_time": timerange[1]}})

    if "disable" in internal_notification_options:
        options["disable"] = internal_notification_options["disable"]

    return {"disable_notifications": options}


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
        # TODO: DEPRECATED(18295) remove "mega_menu_icons"
        attributes["mega_menu_icons"] = (
            "topic" if internal_interface_options["icons_per_item"] is None else "entry"
        )
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

    match internal_interface_options.get("navbar_changes_action"):
        case "full_page":
            attributes["navbar_changes_action"] = "full_page"
        case "slideout":
            attributes["navbar_changes_action"] = "slideout"
        case _:
            attributes["navbar_changes_action"] = "slideout_ask"

    return attributes


def _internal_temperature_format_to_api_format(internal_temperature: str | None) -> str:
    """
    >>> _internal_temperature_format_to_api_format('celsius')
    'celsius'
    >>> _internal_temperature_format_to_api_format(None)
    'default'
    """
    return "default" if not internal_temperature else internal_temperature


# ---------------------------------------------------------------------------------------------
# Response serialization
# ---------------------------------------------------------------------------------------------

_RESPONSE_FIXED_KEYS = frozenset(
    {
        "fullname",
        "customer",
        "disable_login",
        "contact_options",
        "idle_timeout",
        "roles",
        "authorized_sites",
        "contactgroups",
        "pager_address",
        "disable_notifications",
        "language",
        "temperature_unit",
        "auth_option",
        "interface_options",
        "start_url",
    }
)


def _timestamp_to_datetime(timestamp: float) -> dt.datetime:
    return dt.datetime.fromtimestamp(timestamp, tz=dt.UTC)


def _build_contact_options(
    value: Mapping[str, Any] | None,
) -> ConcreteUserContactOptionModel | ApiOmitted:
    if not value:
        return ApiOmitted()
    return ConcreteUserContactOptionModel(
        email=value["email"],
        fallback_contact=value.get("fallback_contact", ApiOmitted()),
    )


def _build_idle_option(value: Mapping[str, Any] | None) -> UserIdleOptionModel | ApiOmitted:
    if not value:
        return ApiOmitted()
    return UserIdleOptionModel(
        option=value["option"],
        duration=value.get("duration", ApiOmitted()),
    )


def _build_disabled_notifications(
    value: Mapping[str, Any] | None,
) -> ConcreteDisabledNotificationsModel | ApiOmitted:
    if value is None:
        return ApiOmitted()
    timerange: DateTimeRangeModel | ApiOmitted = ApiOmitted()
    if "timerange" in value:
        timerange = DateTimeRangeModel(
            start_time=_timestamp_to_datetime(value["timerange"]["start_time"]),
            end_time=_timestamp_to_datetime(value["timerange"]["end_time"]),
        )
    return ConcreteDisabledNotificationsModel(
        disable=value.get("disable", ApiOmitted()),
        timerange=timerange,
    )


def _build_auth_option(value: Mapping[str, Any] | None) -> AuthOptionOutputModel | ApiOmitted:
    if value is None:
        return ApiOmitted()
    return AuthOptionOutputModel(
        auth_type=value.get("auth_type", ApiOmitted()),
        store_automation_secret=value.get("store_automation_secret", ApiOmitted()),
        enforce_password_change=value.get("enforce_password_change", ApiOmitted()),
    )


def _build_interface_options(
    value: Mapping[str, Any] | None,
) -> ConcreteUserInterfaceAttributesModel | ApiOmitted:
    if not value:
        return ApiOmitted()
    return ConcreteUserInterfaceAttributesModel(
        interface_theme=value.get("interface_theme", ApiOmitted()),
        sidebar_position=value.get("sidebar_position", ApiOmitted()),
        navigation_bar_icons=value.get("navigation_bar_icons", ApiOmitted()),
        mega_menu_icons=value.get("mega_menu_icons", ApiOmitted()),
        main_menu_icons=value.get("main_menu_icons", ApiOmitted()),
        show_mode=value.get("show_mode", ApiOmitted()),
        contextual_help_icon=value.get("contextual_help_icon", ApiOmitted()),
        navbar_changes_action=value.get("navbar_changes_action", ApiOmitted()),
    )


def serialize_user(user_id: UserId, user_spec: UserSpec) -> UserObject:
    api_attrs = complement_customer(_internal_to_api_format(user_spec))
    extensions = UserAttributesModel(
        fullname=api_attrs.get("fullname", ApiOmitted()),
        customer=api_attrs.get("customer", ApiOmitted()),
        disable_login=api_attrs.get("disable_login", ApiOmitted()),
        contact_options=_build_contact_options(api_attrs.get("contact_options")),
        idle_timeout=_build_idle_option(api_attrs.get("idle_timeout")),
        roles=api_attrs.get("roles", ApiOmitted()),
        authorized_sites=api_attrs.get("authorized_sites", ApiOmitted()),
        contactgroups=api_attrs.get("contactgroups", ApiOmitted()),
        pager_address=api_attrs.get("pager_address", ApiOmitted()),
        disable_notifications=_build_disabled_notifications(api_attrs.get("disable_notifications")),
        language=api_attrs.get("language", ApiOmitted()),
        temperature_unit=api_attrs.get("temperature_unit", ApiOmitted()),
        auth_option=_build_auth_option(api_attrs.get("auth_option")),
        interface_options=_build_interface_options(api_attrs.get("interface_options")),
        start_url=api_attrs.get("start_url", ApiOmitted()),
        dynamic_fields={
            key: value for key, value in api_attrs.items() if key not in _RESPONSE_FIXED_KEYS
        },
    )
    return UserObject(
        domainType="user_config",
        id=user_id,
        title=user_spec["alias"],
        extensions=extensions,
        links=generate_links("user_config", user_id),
    )
