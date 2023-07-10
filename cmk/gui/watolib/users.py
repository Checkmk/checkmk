#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from datetime import datetime
from typing import cast

import cmk.utils.version as cmk_version
from cmk.utils.crypto.password import Password, PasswordPolicy
from cmk.utils.object_diff import make_diff_text
from cmk.utils.user import UserId

import cmk.gui.userdb as userdb
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.plugins.userdb.utils import add_internal_attributes
from cmk.gui.type_defs import UserObject, Users, UserSpec
from cmk.gui.valuespec import Age, Alternative, EmailAddress, FixedValue, UserID
from cmk.gui.watolib.audit_log import log_audit
from cmk.gui.watolib.changes import add_change
from cmk.gui.watolib.objref import ObjectRef, ObjectRefType
from cmk.gui.watolib.user_scripts import (
    declare_notification_plugin_permissions,
    user_script_choices,
    user_script_title,
)

if not cmk_version.is_raw_edition():
    from cmk.gui.cee.plugins.watolib.dcd import (  # pylint: disable=no-name-in-module
        ConfigDomainDCD,
        used_dcd_rest_api_user,
    )

    def _add_dcd_change(affected_user: str) -> None:
        add_change(
            "edit-dcd-user",
            _l("User %s of DCD connection was modified") % affected_user,
            domains=[ConfigDomainDCD],
        )

else:
    # Stub needed for non enterprise edition
    def used_dcd_rest_api_user() -> str | None:
        return None

    def _add_dcd_change(affected_user: str) -> None:
        return None


def delete_users(users_to_delete: Sequence[UserId]) -> None:
    user.need_permission("wato.users")
    user.need_permission("wato.edit")
    if user.id in users_to_delete:
        raise MKUserError(None, _("You cannot delete your own account!"))

    all_users = userdb.load_users(lock=True)

    deleted_users = []
    for entry in users_to_delete:
        if entry in all_users:  # Silently ignore not existing users
            deleted_users.append(entry)
            del all_users[entry]
        else:
            raise MKUserError(None, _("Unknown user: %s") % entry)

    if deleted_users:
        for user_id in deleted_users:
            log_audit(
                "edit-user",
                "Deleted user: %s" % user_id,
                object_ref=make_user_object_ref(user_id),
            )
        add_change("edit-users", _l("Deleted user: %s") % ", ".join(deleted_users))
        userdb.save_users(all_users, datetime.now())


def edit_users(changed_users: UserObject) -> None:
    if user:
        user.need_permission("wato.users")
        user.need_permission("wato.edit")
    all_users = userdb.load_users(lock=True)
    new_users_info = []
    modified_users_info = []
    for user_id, settings in changed_users.items():
        user_attrs = settings.get("attributes", {})
        is_new_user = settings.get("is_new_user", True)
        _validate_user_attributes(all_users, user_id, user_attrs, is_new_user=is_new_user)

        if is_new_user:
            new_users_info.append(user_id)
        else:
            modified_users_info.append(user_id)

        if is_new_user:
            add_internal_attributes(user_attrs)

        old_object = make_user_audit_log_object(all_users.get(user_id, {}))
        log_audit(
            action="edit-user",
            message=(
                "Created new user: %s" % user_id if is_new_user else "Modified user: %s" % user_id
            ),
            diff_text=make_diff_text(old_object, make_user_audit_log_object(user_attrs)),
            object_ref=make_user_object_ref(user_id),
        )

        all_users[user_id] = user_attrs

    if new_users_info:
        add_change(
            "edit-users",
            _l("Created new users: %s") % ", ".join(new_users_info),
        )
    if modified_users_info:
        add_change(
            "edit-users",
            _l("Modified users: %s") % ", ".join(modified_users_info),
        )
        if (
            affected_user := used_dcd_rest_api_user()
        ) is not None and affected_user in modified_users_info:
            _add_dcd_change(affected_user)

    userdb.save_users(all_users, datetime.now())


def remove_custom_attribute_from_all_users(custom_attribute_name: str) -> None:
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
        }
    )


def make_user_audit_log_object(attributes: UserSpec) -> UserSpec:
    """The resulting object is used for building object diffs"""
    obj = attributes.copy()

    # Password hashes should not be logged
    obj.pop("password", None)

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


def _validate_user_attributes(  # pylint: disable=too-many-branches
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
    else:
        if user_id not in all_users:
            raise MKUserError(None, _("The user you are trying to edit does not exist."))

    # Full name
    alias = user_attrs.get("alias")
    if not alias:
        raise MKUserError(
            "alias", _("Please specify a full name or descriptive alias for the user.")
        )

    # Locking
    locked = user_attrs.get("locked")
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
    for name, attr in userdb.get_user_attributes():
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
        default_value=5400,
    )


def notification_script_title(name):
    return user_script_title("notifications", name)


def notification_script_choices():
    # Ensure the required dynamic permissions are registered
    declare_notification_plugin_permissions()

    choices = []
    for choice in user_script_choices("notifications") + [(None, _("ASCII Email (legacy)"))]:
        notificaton_plugin_name, _notification_plugin_title = choice
        if user.may("notification_plugin.%s" % notificaton_plugin_name):
            choices.append(choice)
    return choices


def verify_password_policy(password: Password) -> None:
    min_len = active_config.password_policy.get("min_length")
    num_groups = active_config.password_policy.get("num_groups")

    result = password.verify_policy(PasswordPolicy(min_len, num_groups))
    if result == PasswordPolicy.Result.TooShort:
        raise MKUserError(
            "password",
            _("The given password is too short. It must have at least %d characters.") % min_len,
        )
    if result == PasswordPolicy.Result.TooSimple:
        raise MKUserError(
            "password",
            _(
                "The password does not use enough character groups. You need to "
                "set a password which uses at least %d of them."
            )
            % num_groups,
        )
