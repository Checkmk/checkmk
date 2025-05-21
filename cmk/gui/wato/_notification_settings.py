#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuration variables for the notification via cmk --notify"""

import cmk.utils.paths

from cmk.gui.i18n import _
from cmk.gui.utils.rule_specs.legacy_converter import convert_to_legacy_valuespec
from cmk.gui.valuespec import (
    Age,
    CascadingDropdown,
    DropdownChoice,
    EmailAddress,
    Integer,
    ValueSpec,
)
from cmk.gui.wato import notification_parameter_registry
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigVariable,
    ConfigVariableGroup,
    ConfigVariableRegistry,
)
from cmk.gui.watolib.config_domains import ConfigDomainCore, ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupNotifications
from cmk.gui.watolib.utils import site_neutral_path

from cmk.rulesets.v1.rule_specs import NotificationParameters


def register(config_variable_registry: ConfigVariableRegistry) -> None:
    config_variable_registry.register(ConfigVariableNotificationFallbackEmail)
    config_variable_registry.register(ConfigVariableNotificationFallbackFormat)
    config_variable_registry.register(ConfigVariableNotificationBacklog)
    config_variable_registry.register(ConfigVariableNotificationBulkInterval)
    config_variable_registry.register(ConfigVariableNotificationPluginTimeout)
    config_variable_registry.register(ConfigVariableNotificationLogging)
    config_variable_registry.register(ConfigVariableFailedNotificationHorizon)


class ConfigVariableNotificationFallbackEmail(ConfigVariable):
    def group(self) -> type[ConfigVariableGroup]:
        return ConfigVariableGroupNotifications

    def domain(self) -> type[ABCConfigDomain]:
        return ConfigDomainCore

    def ident(self) -> str:
        return "notification_fallback_email"

    def valuespec(self) -> ValueSpec:
        return EmailAddress(
            title=_("Fallback email address for notifications"),
            help=_(
                "In case none of your notification rules handles a certain event a notification "
                "will be sent to this address. This makes sure that in that case at least <i>someone</i> "
                "gets notified. Furthermore this email address will be used in notifications as a "
                "contact for any host or service that is not known to the monitoring. "
                "This can happen when you forward notifications from the Event Console. "
                "<br><br>Notification fallback can also be configured in single user profiles."
            ),
            empty_text=_("(No fallback email address configured!)"),
            make_clickable=False,
        )


def _get_valuespec(plugin_name: str) -> ValueSpec:
    plugin = notification_parameter_registry[plugin_name]
    if isinstance(plugin, NotificationParameters):
        return convert_to_legacy_valuespec(plugin.parameter_form(), _)
    return plugin().spec


class ConfigVariableNotificationFallbackFormat(ConfigVariable):
    def group(self) -> type[ConfigVariableGroup]:
        return ConfigVariableGroupNotifications

    def domain(self) -> type[ABCConfigDomain]:
        return ConfigDomainCore

    def ident(self) -> str:
        return "notification_fallback_format"

    def valuespec(self) -> ValueSpec:
        return CascadingDropdown(
            title=_("Fallback notification email format"),
            choices=[
                ("asciimail", _("ASCII email"), _get_valuespec("asciimail")),
                ("mail", _("HTML email"), _get_valuespec("mail")),
            ],
        )


class ConfigVariableNotificationBacklog(ConfigVariable):
    def group(self) -> type[ConfigVariableGroup]:
        return ConfigVariableGroupNotifications

    def domain(self) -> type[ABCConfigDomain]:
        return ConfigDomainCore

    def ident(self) -> str:
        return "notification_backlog"

    def valuespec(self) -> ValueSpec:
        return Integer(
            title=_("Store notifications for rule analysis"),
            help=_(
                "If this option is set to a non-zero number, then Checkmk "
                "keeps the last <i>X</i> notifications for later reference. "
                "You can replay these notifications and analyse your set of "
                "notifications rules. This only works with rulebased notifications. Note: "
                "only notifications sent out by the local notification system can be "
                "tracked. If you have a distributed environment you need to do the analysis "
                "directly on the remote sites - unless you use a central spooling."
            ),
        )


class ConfigVariableNotificationBulkInterval(ConfigVariable):
    def group(self) -> type[ConfigVariableGroup]:
        return ConfigVariableGroupNotifications

    def domain(self) -> type[ABCConfigDomain]:
        return ConfigDomainCore

    def ident(self) -> str:
        return "notification_bulk_interval"

    def valuespec(self) -> ValueSpec:
        return Age(
            title=_("Interval for checking for ripe bulk notifications"),
            help=_(
                "If you are using rule based notifications with and <i>Bulk Notifications</i> "
                "then Checkmk will check for ripe notification bulks to be sent out "
                "at latest every this interval."
            ),
            minvalue=1,
        )

    # TODO: Duplicate with domain specification. Drop this?
    def need_restart(self) -> bool:
        return True


class ConfigVariableNotificationPluginTimeout(ConfigVariable):
    def group(self) -> type[ConfigVariableGroup]:
        return ConfigVariableGroupNotifications

    def domain(self) -> type[ABCConfigDomain]:
        return ConfigDomainCore

    def ident(self) -> str:
        return "notification_plugin_timeout"

    def valuespec(self) -> ValueSpec:
        return Age(
            title=_("Notification plug-in timeout"),
            help=_("After the configured time notification plug-ins are being interrupted."),
            minvalue=1,
        )


class ConfigVariableNotificationLogging(ConfigVariable):
    def group(self) -> type[ConfigVariableGroup]:
        return ConfigVariableGroupNotifications

    def domain(self) -> type[ABCConfigDomain]:
        return ConfigDomainCore

    def ident(self) -> str:
        return "notification_logging"

    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Notification log level"),
            help=_(
                "You can configure the notification mechanism to log more details about "
                "the notifications into the notification log. This information are logged "
                "into the file <tt>%s</tt>"
            )
            % site_neutral_path(cmk.utils.paths.log_dir + "/notify.log"),
            choices=[
                (20, _("Minimal logging")),
                (15, _("Normal logging")),
                (10, _("Full dump of all variables and command")),
            ],
        )


class ConfigVariableFailedNotificationHorizon(ConfigVariable):
    def group(self) -> type[ConfigVariableGroup]:
        return ConfigVariableGroupNotifications

    def domain(self) -> type[ABCConfigDomain]:
        return ConfigDomainGUI

    def ident(self) -> str:
        return "failed_notification_horizon"

    def valuespec(self) -> ValueSpec:
        return Age(
            title=_("Failed notification horizon"),
            help=_(
                "The tactical overview snap-in is reporting about notifications that could not be sent "
                'by Checkmk. Users with the permission "See failed notifications (all)" get the number '
                "of failed notification within the configured horizon."
            ),
            default_value=60 * 60 * 24 * 7,
            display=["days"],
            minvalue=60 * 60 * 24,
        )
