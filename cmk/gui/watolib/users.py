#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.mkeventd
import cmk.gui.userdb as userdb
import cmk.gui.watolib.global_settings as global_settings
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import config, user
from cmk.gui.i18n import _
from cmk.gui.plugins.userdb.utils import add_internal_attributes
from cmk.gui.type_defs import UserId
from cmk.gui.valuespec import (
    Age,
    Alternative,
    CascadingDropdown,
    Checkbox,
    Dictionary,
    DropdownChoice,
    EmailAddress,
    FixedValue,
    Foldable,
    Integer,
    ListChoice,
    ListOf,
    ListOfStrings,
    RegExp,
    TextInput,
    Tuple,
    UserID,
)
from cmk.gui.watolib.changes import add_change, log_audit, make_diff_text, ObjectRef, ObjectRefType
from cmk.gui.watolib.user_scripts import (
    declare_notification_plugin_permissions,
    user_script_choices,
    user_script_title,
)


def delete_users(users_to_delete):
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
                _("Deleted user: %s") % user_id,
                object_ref=make_user_object_ref(user_id),
            )
        add_change("edit-users", _("Deleted user: %s") % ", ".join(deleted_users))
        userdb.save_users(all_users)


def edit_users(changed_users):
    all_users = userdb.load_users(lock=True)
    new_users_info = []
    modified_users_info = []
    for user_id, settings in changed_users.items():
        user_attrs = settings.get("attributes")
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
                _("Created new user: %s") % user_id
                if is_new_user
                else _("Modified user: %s") % user_id
            ),
            diff_text=make_diff_text(old_object, make_user_audit_log_object(user_attrs)),
            object_ref=make_user_object_ref(user_id),
        )

        all_users[user_id] = user_attrs

    if new_users_info:
        add_change("edit-users", _("Created new users: %s") % ", ".join(new_users_info))
    if modified_users_info:
        add_change("edit-users", _("Modified users: %s") % ", ".join(modified_users_info))

    userdb.save_users(all_users)


def make_user_audit_log_object(attributes):
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


def _validate_user_attributes(all_users, user_id, user_attrs, is_new_user=True) -> None:
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

    # Authentication: Password or Secret
    if "automation_secret" in user_attrs:
        secret = user_attrs["automation_secret"]
        if len(secret) < 10:
            raise MKUserError(
                "secret", _("Please specify a secret of at least 10 characters length.")
            )
    else:
        password = user_attrs.get("password")
        if password:
            verify_password_policy(password)

    # Email
    email = user_attrs.get("email")
    vs_email = EmailAddress()
    vs_email.validate_value(email, "email")

    # Idle timeout
    idle_timeout = user_attrs.get("idle_timeout")
    vs_user_idle_timeout = get_vs_user_idle_timeout()
    vs_user_idle_timeout.validate_value(idle_timeout, "idle_timeout")

    # Notification settings are only active if we do *not* have rule based notifications!
    if not global_settings.rulebased_notifications_enabled():
        # Notifications
        notifications_enabled = user_attrs.get("notification_enabled")

        # Check if user can receive notifications
        if notifications_enabled:
            if not email:
                raise MKUserError(
                    "email",
                    _(
                        "You have enabled the notifications but missed to configure a "
                        "Email address. You need to configure your mail address in order "
                        "to be able to receive emails."
                    ),
                )

            contactgroups = user_attrs.get("contactgroups")
            if not contactgroups:
                raise MKUserError(
                    "notifications_enabled",
                    _(
                        "You have enabled the notifications but missed to make the "
                        "user member of at least one contact group. You need to make "
                        "the user member of a contact group which has hosts assigned "
                        "in order to be able to receive emails."
                    ),
                )

            roles = user_attrs.get("roles")
            if not roles:
                raise MKUserError(
                    "role_user", _("Your user has no roles. Please assign at least one role.")
                )

        notification_method = user_attrs.get("notification_method")
        get_vs_flexible_notifications().validate_value(notification_method, "notification_method")
    else:
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
            Age(
                title=_("Set an individual idle timeout"),
                display=["minutes", "hours", "days"],
                minvalue=60,
                default_value=3600,
            ),
        ],
        orientation="horizontal",
    )


def get_vs_flexible_notifications():
    # Make sure, that list is not trivially false
    def validate_only_services(value, varprefix):
        for s in value:
            if s and s[0] != "!":
                return
        raise MKUserError(varprefix + "_0", _("The list of services will never match"))

    return CascadingDropdown(
        title=_("Notification Method"),
        choices=[
            ("email", _("Plain Text Email (using configured templates)")),
            (
                "flexible",
                _("Flexible Custom Notifications"),
                ListOf(
                    valuespec=Foldable(
                        Dictionary(
                            optional_keys=[
                                "service_blacklist",
                                "only_hosts",
                                "only_services",
                                "escalation",
                                "match_sl",
                            ],
                            columns=1,
                            elements=[
                                (
                                    "plugin",
                                    DropdownChoice(
                                        title=_("Notification Plugin"),
                                        choices=notification_script_choices,
                                        default_value="mail",
                                    ),
                                ),
                                (
                                    "parameters",
                                    ListOfStrings(
                                        title=_("Plugin Arguments"),
                                        help=_(
                                            "You can specify arguments to the notification plugin here. "
                                            "Please refer to the documentation about the plugin for what "
                                            "parameters are allowed or required here."
                                        ),
                                    ),
                                ),
                                (
                                    "disabled",
                                    Checkbox(
                                        title=_("Disabled"),
                                        label=_("Currently disable this notification"),
                                        default_value=False,
                                    ),
                                ),
                                (
                                    "timeperiod",
                                    cmk.gui.watolib.timeperiods.TimeperiodSelection(
                                        title=_("Timeperiod"),
                                        help=_("Do only notifiy alerts within this time period"),
                                    ),
                                ),
                                (
                                    "escalation",
                                    Tuple(
                                        title=_(
                                            "Restrict to n<sup>th</sup> to m<sup>th</sup> notification (escalation)"
                                        ),
                                        orientation="float",
                                        elements=[
                                            Integer(
                                                label=_("from"),
                                                help=_(
                                                    "Let through notifications counting from this number"
                                                ),
                                                default_value=1,
                                                minvalue=1,
                                                maxvalue=999999,
                                            ),
                                            Integer(
                                                label=_("to"),
                                                help=_(
                                                    "Let through notifications counting upto this number"
                                                ),
                                                default_value=999999,
                                                minvalue=1,
                                                maxvalue=999999,
                                            ),
                                        ],
                                    ),
                                ),
                                (
                                    "match_sl",
                                    Tuple(
                                        title=_("Match service level"),
                                        help=_(
                                            "Host or Service must be in the following service level to get notification"
                                        ),
                                        orientation="horizontal",
                                        show_titles=False,
                                        elements=[
                                            DropdownChoice(
                                                label=_("from:"),
                                                choices=cmk.gui.mkeventd.service_levels,
                                                prefix_values=True,
                                            ),
                                            DropdownChoice(
                                                label=_(" to:"),
                                                choices=cmk.gui.mkeventd.service_levels,
                                                prefix_values=True,
                                            ),
                                        ],
                                    ),
                                ),
                                (
                                    "host_events",
                                    ListChoice(
                                        title=_("Host Events"),
                                        choices=[
                                            ("d", _("Host goes down")),
                                            ("u", _("Host gets unreachble")),
                                            ("r", _("Host goes up again")),
                                            ("f", _("Start or end of flapping state")),
                                            ("s", _("Start or end of a scheduled downtime ")),
                                            ("x", _("Acknowledgement of host problem")),
                                        ],
                                        default_value=["d", "u", "r", "f", "s", "x"],
                                    ),
                                ),
                                (
                                    "service_events",
                                    ListChoice(
                                        title=_("Service Events"),
                                        choices=[
                                            ("w", _("Service goes into warning state")),
                                            ("u", _("Service goes into unknown state")),
                                            ("c", _("Service goes into critical state")),
                                            ("r", _("Service recovers to OK")),
                                            ("f", _("Start or end of flapping state")),
                                            ("s", _("Start or end of a scheduled downtime")),
                                            ("x", _("Acknowledgement of service problem")),
                                        ],
                                        default_value=["w", "c", "u", "r", "f", "s", "x"],
                                    ),
                                ),
                                (
                                    "only_hosts",
                                    ListOfStrings(
                                        title=_("Limit to the following hosts"),
                                        help=_(
                                            "Configure the hosts for this notification. Without prefix, only exact, case sensitive matches, "
                                            "<tt>!</tt> for negation and <tt>~</tt> for regex matches."
                                        ),
                                        orientation="horizontal",
                                        # TODO: Clean this up to use an alternative between TextInput() and RegExp(). Also handle the negation in a different way
                                        valuespec=TextInput(
                                            size=20,
                                        ),
                                    ),
                                ),
                                (
                                    "only_services",
                                    ListOfStrings(
                                        title=_("Limit to the following services"),
                                        help=_(
                                            "Configure regular expressions that match the beginning of the service names here. Prefix an "
                                            "entry with <tt>!</tt> in order to <i>exclude</i> that service."
                                        ),
                                        orientation="horizontal",
                                        # TODO: Clean this up to use an alternative between TextInput() and RegExp(). Also handle the negation in a different way
                                        valuespec=TextInput(
                                            size=20,
                                        ),
                                        validate=validate_only_services,
                                    ),
                                ),
                                (
                                    "service_blacklist",
                                    ListOfStrings(
                                        title=_("Blacklist the following services"),
                                        help=_(
                                            "Configure regular expressions that match the beginning of the service names here."
                                        ),
                                        orientation="horizontal",
                                        valuespec=RegExp(
                                            size=20,
                                            mode=RegExp.prefix,
                                        ),
                                        validate=validate_only_services,
                                    ),
                                ),
                            ],
                        ),
                        title_function=lambda v: _("Notify by: ")
                        + notification_script_title(v["plugin"]),
                    ),
                    title=_("Flexible Custom Notifications"),
                    add_label=_("Add notification"),
                ),
            ),
        ],
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


def verify_password_policy(password):
    min_len = config.password_policy.get("min_length")
    if min_len and len(password) < min_len:
        raise MKUserError(
            "password",
            _("The given password is too short. It must have at least %d characters.") % min_len,
        )

    num_groups = config.password_policy.get("num_groups")
    if num_groups:
        groups = {}
        for c in password:
            if c in "abcdefghijklmnopqrstuvwxyz":
                groups["lcase"] = 1
            elif c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                groups["ucase"] = 1
            elif c in "0123456789":
                groups["numbers"] = 1
            else:
                groups["special"] = 1

        if sum(groups.values()) < num_groups:
            raise MKUserError(
                "password",
                _(
                    "The password does not use enough character groups. You need to "
                    "set a password which uses at least %d of them."
                )
                % num_groups,
            )
