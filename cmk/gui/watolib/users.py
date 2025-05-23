#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import cast, Literal, TypeAlias

from livestatus import SiteConfigurations

from cmk.ccc.plugin_registry import Registry
from cmk.ccc.site import SiteId
from cmk.ccc.user import UserId
from cmk.ccc.version import Edition, edition

from cmk.utils import paths
from cmk.utils.log.security_event import log_security_event
from cmk.utils.object_diff import make_diff_text

from cmk.gui import hooks, site_config, userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.type_defs import AnnotatedUserId, UserContactDetails, UserObject, Users, UserSpec
from cmk.gui.userdb import add_internal_attributes, get_user_attributes
from cmk.gui.userdb._connections import get_connection
from cmk.gui.utils.security_log_events import UserManagementEvent
from cmk.gui.valuespec import Age, Alternative, EmailAddress, FixedValue, UserID
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.objref import ObjectRef, ObjectRefType
from cmk.gui.watolib.simple_config_file import ConfigFileRegistry, WatoSingleConfigFile
from cmk.gui.watolib.user_scripts import (
    declare_notification_plugin_permissions,
    user_script_choices,
    user_script_title,
)
from cmk.gui.watolib.utils import multisite_dir, wato_root_dir

from cmk.crypto.password import Password, PasswordPolicy

_UserAssociatedSitesFn: TypeAlias = Callable[[UserSpec], Sequence[SiteId] | None]

_AffectedSites: TypeAlias = set[SiteId] | Literal["all"]


def default_sites(_user: UserSpec) -> Sequence[SiteId] | None:
    """The default implementation to get sites associated with user.

    Which sites are associated to a user is edition-specific."""
    return _user.get("authorized_sites")


def _update_affected_sites(
    affected_sites: _AffectedSites,
    user_sites: Sequence[SiteId] | None,
) -> _AffectedSites:
    if affected_sites == "all":
        return "all"

    if user_sites is None:
        return "all"

    return affected_sites | set(user_sites)


def delete_users(users_to_delete: Sequence[UserId], sites: _UserAssociatedSitesFn) -> None:
    user.need_permission("wato.users")
    user.need_permission("wato.edit")
    if user.id in users_to_delete:
        raise MKUserError(None, _("You cannot delete your own account!"))

    all_users = userdb.load_users(lock=True)

    deleted_users = []
    affected_sites: _AffectedSites = set()
    for entry in users_to_delete:
        if entry in all_users:  # Silently ignore not existing users
            deleted_users.append(entry)
            affected_sites = _update_affected_sites(affected_sites, sites(all_users[entry]))
            connection_id = all_users[entry].get("connector", None)
            connection = get_connection(connection_id)
            log_security_event(
                UserManagementEvent(
                    event="user deleted",
                    affected_user=entry,
                    acting_user=user.id,
                    connector=connection.type() if connection else None,
                    connection_id=connection_id,
                )
            )
            del all_users[entry]
        else:
            raise MKUserError(None, _("Unknown user: %s") % entry)

    if deleted_users:
        for user_id in deleted_users:
            log_audit(
                action="edit-user",
                message="Deleted user: %s" % user_id,
                user_id=user.id,
                use_git=active_config.wato_use_git,
                object_ref=make_user_object_ref(user_id),
            )
        add_change(
            action_name="edit-users",
            text=_l("Deleted user: %s") % ", ".join(deleted_users),
            user_id=user.id,
            sites=None if affected_sites == "all" else list(affected_sites),
            use_git=active_config.wato_use_git,
        )
        userdb.save_users(all_users, datetime.now())


def edit_users(changed_users: UserObject, sites: _UserAssociatedSitesFn) -> None:
    user.need_permission("wato.users")
    user.need_permission("wato.edit")
    all_users = userdb.load_users(lock=True)
    new_users_info = []
    modified_users_info = []
    affected_sites: _AffectedSites = set()
    for user_id, settings in changed_users.items():
        user_attrs: UserSpec = settings.get("attributes", {})
        is_new_user = settings.get("is_new_user", True)
        _validate_user_attributes(all_users, user_id, user_attrs, is_new_user=is_new_user)

        affected_sites = _update_affected_sites(affected_sites, sites(user_attrs))
        if is_new_user:
            new_users_info.append(user_id)
            add_internal_attributes(user_attrs)
        else:
            modified_users_info.append(user_id)
            old_user_attrs = all_users[user_id]
            affected_sites = _update_affected_sites(affected_sites, sites(old_user_attrs))

        old_object = make_user_audit_log_object(all_users.get(user_id, {}))
        log_audit(
            action="edit-user",
            message=(
                "Created new user: %s" % user_id if is_new_user else "Modified user: %s" % user_id
            ),
            user_id=user.id,
            use_git=active_config.wato_use_git,
            diff_text=make_diff_text(old_object, make_user_audit_log_object(user_attrs)),
            object_ref=make_user_object_ref(user_id),
        )
        connection_id = user_attrs.get("connector", None)
        connection = get_connection(connection_id)

        log_security_event(
            UserManagementEvent(
                event="user created" if is_new_user else "user modified",
                affected_user=user_id,
                acting_user=user.id,
                connector=connection.type() if connection else None,
                connection_id=connection_id,
            )
        )

        all_users[user_id] = user_attrs

    if new_users_info:
        add_change(
            action_name="edit-users",
            text=_l("Created new users: %s") % ", ".join(new_users_info),
            user_id=user.id,
            sites=None if affected_sites == "all" else list(affected_sites),
            use_git=active_config.wato_use_git,
        )
    if modified_users_info:
        add_change(
            action_name="edit-users",
            text=_l("Modified users: %s") % ", ".join(modified_users_info),
            user_id=user.id,
            sites=None if affected_sites == "all" else list(affected_sites),
            use_git=active_config.wato_use_git,
        )
        hooks.call("users-changed", modified_users_info)

    userdb.save_users(all_users, datetime.now())


def remove_custom_attribute_from_all_users(
    custom_attribute_name: str, sites: _UserAssociatedSitesFn
) -> None:
    edit_users(
        {
            user_id: {
                "attributes": cast(
                    UserSpec,
                    {k: v for k, v in settings.items() if k != custom_attribute_name},
                ),
                "is_new_user": False,
            }
            for user_id, settings in userdb.load_users(lock=True).items()
        },
        sites,
    )


def make_user_audit_log_object(attributes: UserSpec) -> UserSpec:
    """The resulting object is used for building object diffs"""
    obj = attributes.copy()

    # Password hashes should not be logged
    obj.pop("password", None)
    obj.pop("automation_secret", None)

    # Skip internal attributes
    obj.pop("user_scheme_serial", None)

    # Skip default values (that will not be persisted)
    if obj.get("start_url") is None:
        obj.pop("start_url", None)
    if obj.get("ui_sidebar_position") is None:
        obj.pop("ui_sidebar_position", None)
    if obj.get("ui_theme") is None:
        obj.pop("ui_theme", None)

    return obj


def make_user_object_ref(user_id: UserId) -> ObjectRef:
    return ObjectRef(ObjectRefType.User, str(user_id))


def _validate_user_attributes(
    all_users: Users,
    user_id: UserId,
    user_attrs: UserSpec,
    is_new_user: bool = True,
) -> None:
    # Check user_id
    if is_new_user:
        if user_id in all_users:
            raise MKUserError("user_id", _("This username is already being used by another user."))
        vs_user_id = UserID(allow_empty=False)
        vs_user_id.validate_value(user_id, "user_id")
    elif user_id not in all_users:
        raise MKUserError(None, _("The user you are trying to edit does not exist."))

    # Full name
    alias = user_attrs.get("alias")
    if not alias:
        raise MKUserError(
            "alias", _("Please specify a full name or descriptive alias for the user.")
        )

    # Locking
    locked = user_attrs["locked"]
    if user_id == user.id and locked:
        raise MKUserError("locked", _("You cannot lock your own account!"))

    # Automation Secret
    # Note: if a password is used it is verified before this; we only know the hash here
    if "automation_secret" in user_attrs:
        secret = user_attrs["automation_secret"]
        if len(secret) < 10:
            raise MKUserError(
                "_auth_secret", _("Please enter an automation secret of at least 10 characters.")
            )

    # Email
    email = user_attrs.get("email")
    if "email" in user_attrs and email is not None:
        vs_email = EmailAddress()
        vs_email.validate_value(email, "email")

    # Idle timeout
    idle_timeout = user_attrs.get("idle_timeout")
    vs_user_idle_timeout = get_vs_user_idle_timeout()
    vs_user_idle_timeout.validate_value(idle_timeout, "idle_timeout")

    fallback_contact = user_attrs.get("fallback_contact")
    if fallback_contact and not email:
        raise MKUserError(
            "email",
            _(
                "You have enabled the fallback notifications but missed to configure an "
                "email address. You need to configure your mail address in order "
                "to be able to receive fallback notifications."
            ),
        )

    # Custom user attributes
    for name, attr in get_user_attributes():
        value = user_attrs.get(name)
        attr.valuespec().validate_value(value, "ua_" + name)


def get_vs_user_idle_timeout():
    return Alternative(
        title=_("Session idle timeout"),
        elements=[
            FixedValue(
                value=None,
                title=_("Use the global configuration"),
                totext="",
            ),
            FixedValue(
                value=False,
                title=_("Disable the login timeout"),
                totext="",
            ),
            vs_idle_timeout_duration(),
        ],
        orientation="horizontal",
    )


def vs_idle_timeout_duration() -> Age:
    return Age(
        title=_("Set an individual idle timeout"),
        display=["minutes", "hours", "days"],
        minvalue=60,
        help=_(
            "Normally a user login session is valid until the password is changed, the "
            "browser is closed or the user is locked. By enabling this option, you "
            "can apply a time limit to login sessions which is applied when the user "
            "stops interacting with the GUI for a given amount of time. When a user "
            "exceeds the configured maximum idle time, the user will be logged "
            "out and redirected to the login screen to renew the login session. "
            "This setting can be overridden in each individual user's profile.",
        ),
        default_value=5400,
    )


def notification_script_title(name):
    return user_script_title("notifications", name)


def notification_script_choices() -> list[tuple[str, str]]:
    # Ensure the required dynamic permissions are registered
    declare_notification_plugin_permissions()

    choices: list[tuple[str, str]] = []
    for choice in user_script_choices("notifications"):
        notification_plugin_name, _notification_plugin_title = choice
        if user.may("notification_plugin.%s" % notification_plugin_name):
            choices.append(choice)
    return choices


def verify_password_policy(password: Password, varname: str = "password") -> None:
    min_len = active_config.password_policy.get("min_length")
    num_groups = active_config.password_policy.get("num_groups")

    result = password.verify_policy(PasswordPolicy(min_len, num_groups))
    if result == PasswordPolicy.Result.TooShort:
        raise MKUserError(
            varname,
            _("The given password is too short. It must have at least %d characters.") % min_len,
        )
    if result == PasswordPolicy.Result.TooSimple:
        raise MKUserError(
            varname,
            _(
                "The password does not use enough character groups. You need to "
                "set a password which uses at least %d of them."
            )
            % num_groups,
        )


class UsersConfigFile(WatoSingleConfigFile[Users]):
    """Handles reading and writing users.mk file"""

    def __init__(self) -> None:
        super().__init__(
            config_file_path=multisite_dir() / "users.mk",
            config_variable="multisite_users",
            spec_class=Users,
        )


class ContactsConfigFile(WatoSingleConfigFile[dict[AnnotatedUserId, UserContactDetails]]):
    """Handles reading and writing contacts.mk file"""

    def __init__(self) -> None:
        super().__init__(
            config_file_path=wato_root_dir() / "contacts.mk",
            config_variable="contacts",
            spec_class=dict[AnnotatedUserId, UserContactDetails],
        )


@dataclass(frozen=True, kw_only=True)
class UserFeatures:
    edition: Edition
    sites: _UserAssociatedSitesFn


class UserFeaturesRegistry(Registry[UserFeatures]):
    def plugin_name(self, instance: UserFeatures) -> str:
        return str(instance.edition)

    def features(self) -> UserFeatures:
        return self[str(edition(paths.omd_root))]


user_features_registry = UserFeaturesRegistry()


def get_enabled_remote_sites_for_logged_in_user(logged_in_user: LoggedInUser) -> SiteConfigurations:
    all_enabled_slave_sites = site_config.wato_slave_sites()
    if (
        site_ids_for_user := user_features_registry.features().sites(logged_in_user.attributes)
    ) is None:
        return all_enabled_slave_sites

    return SiteConfigurations(
        {
            site_id: site_config
            for site_id, site_config in all_enabled_slave_sites.items()
            if site_id in site_ids_for_user
        }
    )


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(UsersConfigFile())
    config_file_registry.register(ContactsConfigFile())
