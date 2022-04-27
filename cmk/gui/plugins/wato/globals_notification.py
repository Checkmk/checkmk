#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuration variables for the notification via cmk --notify"""

# TODO: Remove all configuration for legacy-Email to deprecated, or completely
# remove from WATO.

import cmk.utils.paths

from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    ConfigDomainCore,
    ConfigDomainGUI,
    ConfigVariableGroupNotifications,
    notification_parameter_registry,
)
from cmk.gui.plugins.watolib.utils import config_variable_registry, ConfigVariable
from cmk.gui.valuespec import (
    Age,
    CascadingDropdown,
    Checkbox,
    DropdownChoice,
    EmailAddress,
    Integer,
    ListOf,
    TextInput,
    Transform,
    Tuple,
)
from cmk.gui.watolib.utils import site_neutral_path


@config_variable_registry.register
class ConfigVariableEnableRBN(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "enable_rulebased_notifications"

    def valuespec(self):
        return Checkbox(
            title=_("Rule based notifications"),
            label=_("Enable new rule based notifications"),
            help=_(
                "If you enable the new rule based notifications then the current plain text email and "
                "&quot;flexible notifications&quot; will become inactive. Instead notificatios will "
                "be configured with the WATO module <i>Notifications</i> on a global base."
            ),
        )

    # TODO: Duplicate with domain specification. Drop this?
    def need_restart(self):
        return True


@config_variable_registry.register
class ConfigVariableNotificationFallbackEmail(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "notification_fallback_email"

    def valuespec(self):
        return EmailAddress(
            title=_("Fallback email address for notifications"),
            help=_(
                "In case none of your notification rules handles a certain event a notification "
                "will be sent to this address. This makes sure that in that case at least <i>someone</i> "
                "gets notified. Furthermore this email address will be used in notifications as a "
                "contact for any host or service "
                "that is not known to the monitoring. This can happen when you forward notifications "
                "from the Event Console.<br><br>Notification fallback can also configured in single "
                "user profiles."
            ),
            empty_text=_("(No fallback email address configured!)"),
            make_clickable=False,
        )


@config_variable_registry.register
class ConfigVariableNotificationFallbackFormat(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "notification_fallback_format"

    def valuespec(self):
        return CascadingDropdown(
            title=_("Fallback notification email format"),
            choices=[
                (
                    "asciimail",
                    _("ASCII Email"),
                    notification_parameter_registry["asciimail"]().spec,
                ),
                (
                    "mail",
                    _("HTML Email"),
                    notification_parameter_registry["mail"]().spec,
                ),
            ],
        )


@config_variable_registry.register
class ConfigVariableNotificationBacklog(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "notification_backlog"

    def valuespec(self):
        return Integer(
            title=_("Store notifications for rule analysis"),
            help=_(
                "If this option is set to a non-zero number, then Check_MK "
                "keeps the last <i>X</i> notifications for later reference. "
                "You can replay these notifications and analyse your set of "
                "notifications rules. This only works with rulebased notifications. Note: "
                "only notifications sent out by the local notification system can be "
                "tracked. If you have a distributed environment you need to do the analysis "
                "directly on the remote sites - unless you use a central spooling."
            ),
        )


@config_variable_registry.register
class ConfigVariableNotificationBulkInterval(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "notification_bulk_interval"

    def valuespec(self):
        return Age(
            title=_("Interval for checking for ripe bulk notifications"),
            help=_(
                "If you are using rule based notifications with and <i>Bulk Notifications</i> "
                "then Check_MK will check for ripe notification bulks to be sent out "
                "at latest every this interval."
            ),
            minvalue=1,
        )

    # TODO: Duplicate with domain specification. Drop this?
    def need_restart(self):
        return True


@config_variable_registry.register
class ConfigVariableNotificationPluginTimeout(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "notification_plugin_timeout"

    def valuespec(self):
        return Age(
            title=_("Notification plugin timeout"),
            help=_("After the configured time notification plugins are being interrupted."),
            minvalue=1,
        )


@config_variable_registry.register
class ConfigVariableNotificationLogging(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainCore

    def ident(self):
        return "notification_logging"

    def valuespec(self):
        return Transform(
            valuespec=DropdownChoice(
                choices=[
                    (20, _("Minimal logging")),
                    (15, _("Normal logging")),
                    (10, _("Full dump of all variables and command")),
                ],
            ),
            forth=self._transform_log_level,
            title=_("Notification log level"),
            help=_(
                "You can configure the notification mechanism to log more details about "
                "the notifications into the notification log. This information are logged "
                "into the file <tt>%s</tt>"
            )
            % site_neutral_path(cmk.utils.paths.log_dir + "/notify.log"),
        )

    @staticmethod
    def _transform_log_level(level):
        # The former values 1 and 2 are mapped to the values 20 (default) and 10 (debug)
        # which agree with the values used in cmk/utils/log.py.
        # The decprecated value 0 is transformed to the default logging value.
        if level in [0, 1]:
            return 20
        if level == 2:
            return 10
        return level


@config_variable_registry.register
class ConfigVariableServiceLevels(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "mkeventd_service_levels"

    def valuespec(self):
        return ListOf(
            valuespec=Tuple(
                elements=[
                    Integer(
                        title=_("internal ID"),
                        minvalue=0,
                        maxvalue=100,
                    ),
                    TextInput(
                        title=_("Name / Description"),
                        allow_empty=False,
                    ),
                ],
                orientation="horizontal",
            ),
            title=_("Service Levels"),
            help=_(
                "Here you can configure the list of possible service levels for hosts, services and "
                "events. A service level can be assigned to a host or service by configuration. "
                "The event console can configure each created event to have a specific service level. "
                "Internally the level is represented as an integer number. Note: a higher number represents "
                "a higher service level. This is important when filtering views "
                "by the service level.<p>You can also attach service levels to hosts "
                "and services in the monitoring. These levels will then be sent to the "
                "Event Console when you forward notifications to it and will override the "
                "setting of the matching rule."
            ),
            allow_empty=False,
        )

    def allow_reset(self):
        return False


@config_variable_registry.register
class ConfigVariableFailedNotificationHorizon(ConfigVariable):
    def group(self):
        return ConfigVariableGroupNotifications

    def domain(self):
        return ConfigDomainGUI

    def ident(self):
        return "failed_notification_horizon"

    def valuespec(self):
        return Age(
            title=_("Failed notification horizon"),
            help=_(
                "The tactical overview snapin is reporing about notifications that could not be sent "
                'by Check_MK. Users with the permission "See failed Notifications (all)" get the number '
                "of failed notification within the configured horizon."
            ),
            default_value=60 * 60 * 24 * 7,
            display=["days"],
            minvalue=60 * 60 * 24,
        )
