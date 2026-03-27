#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Generator, Sequence
from contextlib import contextmanager
from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Any, Literal, Self

from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.crypto.password_hashing import PasswordHash
from cmk.gui.type_defs import LastLoginInfo, SessionId, SessionInfo, TwoFactorCredentials, UserSpec
from cmk.utils.notify_types import DisabledNotificationsOptions, EventRule
from cmk.utils.object_diff import make_diff_text

from ._user_attribute import UserAttribute
from .store import load_users, update_user


class UserNotFoundError(KeyError): ...


class UserAlreadyExistsError(KeyError): ...


class _MissingValueSentinel:
    """
    Some attributes carry a special meaning by being absent vs. being set to None in the UserSpec
    dict. Try to get rid of them step by step; for now we use this to distinguish between absent and
    None.
    """


MISSING = _MissingValueSentinel()

type ShowModeType = Literal["default_show_less", "default_show_more", "enforce_show_more"]


class CustomAttributes:
    attributes: dict[str, object]

    def __init__(self, attribute_specs: dict[str, UserAttribute]) -> None:
        self.configured_custom_user_attributes = attribute_specs
        self.attributes = {}

    def __getitem__(self, name: str) -> object:
        return self.attributes[name]

    def __setitem__(self, name: str, value: object) -> None:
        self.configured_custom_user_attributes[name].valuespec().validate_value(value, "ua_" + name)
        self.attributes[name] = value

    def __repr__(self) -> str:
        # TODO: is this well behaved with the diff?
        return f"{self.attributes}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CustomAttributes):
            return NotImplemented
        return self.attributes == other.attributes


@dataclass
class UserData:
    """Represents user data stored on disk.

    This class is WIP with CMK-16814; do not use it yet.
    """

    user_scheme_serial: int

    user_id: UserId
    alias: str  # aka "Full name"

    connection_id: str | None  # None means "local user"

    contactgroups: list[str]
    authorized_sites: list[SiteId] | Literal["all"] | _MissingValueSentinel
    force_authuser: bool | _MissingValueSentinel  # I'm not sure if missing has special meaning here

    roles: list[str]

    # secrets and passwords; TODO extract
    #
    session_info: dict[SessionId, SessionInfo]
    is_automation_user: bool
    store_automation_secret: bool
    automation_secret: str | None
    password_hash: PasswordHash | None
    two_factor_credentials: TwoFactorCredentials | None  # TODO: newly optional
    locked: bool
    enforce_pw_change: bool
    idle_timeout: None | Literal[False] | int  # None means "use global default", False "no timeout"
    last_login: LastLoginInfo | None

    # MISSING is a clutch here; userdb._save_user_profiles will secretly fill in the current time if
    # it saves a UserSpec with no last_pw_change set. This handling should happen here instead.
    last_pw_change: int | _MissingValueSentinel

    ldap_pw_last_changed: str | None  # On attribute sync, this is added, then removed.
    num_failed_logins: int
    serial: int

    customer: str | None | _MissingValueSentinel

    # notifications; TODO extract
    #
    email: str | None
    # Note: UserSpec also had "mail", but I could not find any usage of it.
    pager: str  # surely this is optional
    fallback_contact: bool
    # Note: none of these was marked as NotRequired in UserSpec, but I have some doubts
    host_notification_options: str | None  # newly optional
    notification_method: Any  # TODO: Improve this
    notification_period: str | None  # newly optional
    notification_rules: list[EventRule]
    notifications_enabled: bool | None
    service_notification_options: str | None  # newly optional
    # Note: disable_notifications is a mess; In UserContactDetails it is NotRequired, in UserSpec it
    # is. There's a type called DisableNotificationsAttribute which is almost the same and it is
    # unclear which one is correct. From testing I think "Attribute", but typing says differently.
    disable_notifications: DisabledNotificationsOptions | _MissingValueSentinel

    # UI; TODO extract
    #
    start_url: str | None
    language: str | None
    show_mode: ShowModeType | None | _MissingValueSentinel
    nav_hide_icons_title: Literal["hide"] | None | _MissingValueSentinel
    icons_per_item: Literal["entry"] | None | _MissingValueSentinel
    ui_sidebar_position: Literal["left"] | None  # I think None means right, which is the default?
    navbar_changes_action: Literal["slideout", "full_page"] | None
    ui_theme: Literal["modern-dark", "facelift"] | None
    # contextual_help_icon: NotRequired[Literal["hide_icon"] | None]

    temperature_unit: Literal["celsius", "fahrenheit"] | None  # None means default
    created_on_version: str | None
    custom_user_attributes: CustomAttributes

    def __post_init__(self) -> None:
        if self.alias == "":
            raise ValueError("alias must not be empty")

    def to_userspec(self) -> UserSpec:
        spec = UserSpec(
            alias=self.alias,
            contactgroups=self.contactgroups,
            enforce_pw_change=self.enforce_pw_change,
            fallback_contact=self.fallback_contact,
            is_automation_user=self.is_automation_user,
            locked=self.locked,
            num_failed_logins=self.num_failed_logins,
            pager=self.pager,
            roles=self.roles,
            serial=self.serial,
            session_info=self.session_info,
            store_automation_secret=self.store_automation_secret,
            user_id=self.user_id,
            user_scheme_serial=self.user_scheme_serial,
        )

        # Fields that were optional in UserSpec and that are still optional in UserData.
        # None for these fields in the UserSpec simply means "not configured", and we can safely
        # omit them here.
        # Format: (userspec_key, value)
        for key, value in [
            # secrets and credentials
            ("automation_secret", self.automation_secret),
            ("connector", self.connection_id),
            ("password", self.password_hash),
            ("email", self.email),
            ("language", self.language),
            ("ldap_pw_last_changed", self.ldap_pw_last_changed),
            ("two_factor_credentials", self.two_factor_credentials),
            # notification fields
            ("host_notification_options", self.host_notification_options),
            ("notification_period", self.notification_period),
            ("service_notification_options", self.service_notification_options),
            ("notifications_enabled", self.notifications_enabled),
            ("notification_method", self.notification_method),
            # user state
            ("last_login", self.last_login),
            # UI
            ("temperature_unit", self.temperature_unit),
            ("ui_sidebar_position", self.ui_sidebar_position),
            ("navbar_changes_action", self.navbar_changes_action),
            ("ui_theme", self.ui_theme),
            ("start_url", self.start_url),
            ("idle_timeout", self.idle_timeout),
            ("created_on_version", self.created_on_version),
        ]:
            if value is not None:
                spec[key] = value  # type: ignore[literal-required]

        # Empty list (falsey) needs special treatment.
        if self.notification_rules:
            spec["notification_rules"] = self.notification_rules

        # Fields that can explicitly be set to None in UserSpec and None carries a special meaning that is
        # different from "not configured" / "absent". If we find them to be None in UserData.from_userspec
        # we use the sentinel to ensure we can set them to None again here.
        for key, value in [
            ("customer", self.customer),
            ("disable_notifications", self.disable_notifications),
            ("force_authuser", self.force_authuser),
            ("last_pw_change", self.last_pw_change),
            ("show_mode", self.show_mode),
            ("nav_hide_icons_title", self.nav_hide_icons_title),
            ("icons_per_item", self.icons_per_item),
        ]:
            if not isinstance(value, _MissingValueSentinel):
                spec[key] = value  # type: ignore[literal-required]

        # authorized_sites needs a value transformation
        if not isinstance(self.authorized_sites, _MissingValueSentinel):
            spec["authorized_sites"] = (
                None if self.authorized_sites == "all" else self.authorized_sites
            )

        # Custom user attributes not already handled as explicit dataclass fields
        explicit_fields = {f.name for f in fields(self)}
        for name in self.custom_user_attributes.attributes:
            if name not in explicit_fields:
                spec[name] = self.custom_user_attributes[name]  # type: ignore[literal-required]

        return spec

    @staticmethod
    def _read_authorized_sites(
        authorized_sites: Sequence[SiteId] | None | _MissingValueSentinel,
    ) -> list[SiteId] | Literal["all"] | _MissingValueSentinel:
        if isinstance(authorized_sites, _MissingValueSentinel):
            return MISSING
        if authorized_sites is None:
            return "all"
        return list(authorized_sites)

    @classmethod
    def from_userspec(
        cls,
        user_id: UserId,
        userspec: UserSpec,
        user_attribute_specs: Sequence[tuple[str, UserAttribute]],
    ) -> Self:
        attrs = CustomAttributes(dict(user_attribute_specs))
        for name, _ in user_attribute_specs:
            attrs[name] = userspec.get(name)

        return cls(
            alias=userspec["alias"],
            authorized_sites=cls._read_authorized_sites(userspec.get("authorized_sites", MISSING)),
            automation_secret=userspec.get("automation_secret"),
            connection_id=userspec.get("connector"),
            contactgroups=userspec.get("contactgroups", []),
            custom_user_attributes=attrs,
            customer=userspec.get("customer", MISSING),
            disable_notifications=userspec.get("disable_notifications", MISSING),
            email=userspec.get("email"),
            enforce_pw_change=userspec.get("enforce_pw_change", False) or False,
            fallback_contact=userspec.get("fallback_contact", False) or False,
            force_authuser=userspec.get("force_authuser", MISSING),
            host_notification_options=userspec.get("host_notification_options"),
            icons_per_item=userspec.get("icons_per_item", MISSING),
            idle_timeout=userspec.get("idle_timeout"),
            is_automation_user=userspec.get("is_automation_user", False),
            language=userspec.get("language"),
            last_login=userspec.get("last_login"),
            last_pw_change=userspec.get("last_pw_change", MISSING),
            ldap_pw_last_changed=userspec.get("ldap_pw_last_changed"),
            locked=userspec.get("locked", False),
            nav_hide_icons_title=userspec.get("nav_hide_icons_title", MISSING),
            notification_method=userspec.get("notification_method"),
            notification_period=userspec.get("notification_period"),
            notification_rules=userspec.get("notification_rules", []),
            notifications_enabled=userspec.get("notifications_enabled"),
            num_failed_logins=userspec.get("num_failed_logins", 0),
            pager=userspec.get("pager", ""),
            password_hash=userspec.get("password"),
            roles=userspec.get("roles", []),
            serial=userspec.get("serial", 0),
            service_notification_options=userspec.get("service_notification_options"),
            session_info=userspec.get("session_info", {}),
            show_mode=userspec.get("show_mode", MISSING),
            start_url=userspec.get("start_url"),
            store_automation_secret=userspec.get("store_automation_secret", False),
            temperature_unit=userspec.get("temperature_unit"),
            two_factor_credentials=userspec.get("two_factor_credentials"),
            ui_sidebar_position=userspec.get("ui_sidebar_position"),
            navbar_changes_action=userspec.get("navbar_changes_action"),
            ui_theme=userspec.get("ui_theme"),
            created_on_version=userspec.get("created_on_version"),
            user_id=user_id,
            # if we want to keep user_scheme_serial around, don't do this...
            # we'd have to require it, at least the unit tests almost never set it
            user_scheme_serial=userspec.get("user_scheme_serial", 1),
        )

    def diff_text(self, other: Self) -> str:
        """Diff to another userdata object. `other` is the new one."""
        return make_diff_text(asdict(self), asdict(other))

    def update_from(self, other: Self) -> str:
        """Update self from another userdata object."""
        diff = self.diff_text(other)
        for field in fields(other):
            setattr(self, field.name, getattr(other, field.name))
        return diff

    def update_from_userspec(
        self,
        userspec: UserSpec,
        user_attribute_specs: Sequence[tuple[str, UserAttribute]],
    ) -> str:
        """Update self from a userspec."""
        other = self.from_userspec(self.user_id, userspec, user_attribute_specs)
        return self.update_from(other)


class UserDB:
    def __init__(self, custom_user_attributes: Sequence[tuple[str, UserAttribute]]):
        self.custom_user_attributes = custom_user_attributes

    @contextmanager
    def get_user_for_editing(
        self,
        user_id: UserId,
    ) -> Generator[UserData]:
        """
        Load a single user and return it for editing.
        The user object is saved automatically when the context is exited.
        """
        users: dict[UserId, UserSpec] = load_users(lock=True)
        if user_id not in users:
            raise UserNotFoundError(f"User {user_id} not found")

        user = UserData.from_userspec(user_id, users[user_id], self.custom_user_attributes)
        yield user

        users[user_id] = UserData.to_userspec(user)
        update_user(user_id, users, self.custom_user_attributes, datetime.now())

    def add_user(self, user: UserData) -> None:
        """Add a new user to the user database."""
        if user.user_id == "":  # reserved for UserId.builtin()
            raise ValueError("UserId cannot be empty")

        users: dict[UserId, UserSpec] = load_users(lock=True)
        if user.user_id in users:
            raise UserAlreadyExistsError(f"User {user.user_id} already exists")

        users[user.user_id] = UserData.to_userspec(user)
        update_user(user.user_id, users, self.custom_user_attributes, datetime.now())
