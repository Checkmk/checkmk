#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Configuration variables for the notification via cmk --notify"""

from cmk.gui.form_specs.generators.age import Age as FSAge
from cmk.gui.form_specs.unstable import OptionalChoice
from cmk.gui.form_specs.unstable.legacy_converter.transform import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.watolib.config_domain_name import (
    ConfigVariable,
    ConfigVariableRegistry,
    GlobalSettingsContext,
)
from cmk.gui.watolib.config_domains import ConfigDomainCore, ConfigDomainGUI
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupNotifications
from cmk.gui.watolib.notification_parameter import (
    notification_parameter_registry,
)
from cmk.rulesets.internal.form_specs import (
    DictionaryExtended,
    SingleChoiceElementExtended,
    SingleChoiceExtended,
)
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.rule_specs import NotificationParameters


def register(config_variable_registry: ConfigVariableRegistry) -> None:
    config_variable_registry.register(ConfigVariableNotificationFallbackEmail)
    config_variable_registry.register(ConfigVariableNotificationFallbackFormat)
    config_variable_registry.register(ConfigVariableNotificationBacklog)
    config_variable_registry.register(ConfigVariableNotificationBulkInterval)
    config_variable_registry.register(ConfigVariableNotificationPluginTimeout)
    config_variable_registry.register(ConfigVariableNotificationLogging)
    config_variable_registry.register(ConfigVariableFailedNotificationHorizon)


ConfigVariableNotificationFallbackEmail = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    primary_domain=ConfigDomainCore,
    ident="notification_fallback_email",
    form_spec=lambda context: TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=OptionalChoice(
            title=Title("Fallback email address for notifications"),
            help_text=Help(
                "In case none of your notification rules handles a certain event a notification "
                "will be sent to this address. This makes sure that in that case at least <i>someone</i> "
                "gets notified. Furthermore this email address will be used in notifications as a "
                "contact for any host or service that is not known to the monitoring. "
                "This can happen when you forward notifications from the Event Console. "
                "<br><br>Notification fallback can also be configured in single user profiles."
            ),
            label=Label("Send fallback notifications to:"),
            none_label=Label("(No fallback email address configured!)"),
            parameter_form=fs.String(
                custom_validate=[fs.validators.EmailAddress()],
            ),
        ),
        from_disk=lambda value: value or None,
        to_disk=lambda value: value or "",
    ),
)


def _get_parameter_form(plugin_name: str) -> fs.Dictionary | DictionaryExtended:
    plugin = notification_parameter_registry[plugin_name]
    if isinstance(plugin, NotificationParameters):
        return plugin.parameter_form()
    assert plugin.form_spec is not None
    return plugin.form_spec()


ConfigVariableNotificationFallbackFormat = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    primary_domain=ConfigDomainCore,
    ident="notification_fallback_format",
    form_spec=lambda context: fs.CascadingSingleChoice(
        title=Title("Fallback notification email format"),
        elements=[
            fs.CascadingSingleChoiceElement(
                name="asciimail",
                title=Title("ASCII email"),
                parameter_form=_get_parameter_form("asciimail"),
            ),
            fs.CascadingSingleChoiceElement(
                name="mail",
                title=Title("HTML email"),
                parameter_form=_get_parameter_form("mail"),
            ),
        ],
        prefill=fs.DefaultValue("asciimail"),
    ),
)

ConfigVariableNotificationBacklog = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    primary_domain=ConfigDomainCore,
    ident="notification_backlog",
    form_spec=lambda context: fs.Integer(
        title=Title("Store notifications for rule analysis"),
        help_text=Help(
            "If this option is set to a non-zero number, then Checkmk "
            "keeps the last <i>X</i> notifications for later reference. "
            "You can replay these notifications and analyse your set of "
            "notifications rules. This only works with rulebased notifications. Note: "
            "only notifications sent out by the local notification system can be "
            "tracked. If you have a distributed environment you need to do the analysis "
            "directly on the remote sites - unless you use a central spooling."
        ),
    ),
)

ConfigVariableNotificationBulkInterval = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    primary_domain=ConfigDomainCore,
    ident="notification_bulk_interval",
    form_spec=lambda context: FSAge(
        title=Title("Interval for checking for ripe bulk notifications"),
        help_text=Help(
            "If you use rule based notifications with <i>Bulk notifications</i>, "
            "then Checkmk will check for ripe bulk notifications to be sent "
            "at this interval at the latest."
        ),
        custom_validate=[fs.validators.NumberInRange(min_value=1)],
    ),
    # TODO: Duplicate with domain specification. Drop this?
    need_restart=True,
)

ConfigVariableNotificationPluginTimeout = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    primary_domain=ConfigDomainCore,
    ident="notification_plugin_timeout",
    form_spec=lambda context: FSAge(
        title=Title("Notification plug-in timeout"),
        help_text=Help("After the configured time notification plug-ins are being interrupted."),
        custom_validate=[fs.validators.NumberInRange(min_value=1)],
    ),
)


def _form_spec_notification_logging(context: GlobalSettingsContext) -> SingleChoiceExtended[int]:
    return SingleChoiceExtended[int](
        title=Title("Notification log level"),
        help_text=Help(
            "You can configure the notification mechanism to log more details about "
            "the notifications into the notification log. This information is logged "
            "into the file <tt>%(log_file)s</tt>"
        )
        % {"log_file": str(context.site_neutral_log_dir / "notify.log")},
        elements=[
            SingleChoiceElementExtended(name=20, title=Title("Minimal logging")),
            SingleChoiceElementExtended(name=15, title=Title("Normal logging")),
            SingleChoiceElementExtended(
                name=10, title=Title("Full dump of all variables and command")
            ),
        ],
        prefill=fs.DefaultValue(20),
    )


ConfigVariableNotificationLogging = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    primary_domain=ConfigDomainCore,
    ident="notification_logging",
    form_spec=_form_spec_notification_logging,
)

ConfigVariableFailedNotificationHorizon = ConfigVariable(
    group=ConfigVariableGroupNotifications,
    primary_domain=ConfigDomainGUI,
    ident="failed_notification_horizon",
    form_spec=lambda context: FSAge(
        title=Title("Failed notification horizon"),
        help_text=Help(
            "The tactical overview snap-in is reporting about notifications that could not be sent "
            'by Checkmk. Users with the permission "See failed notifications (all)" get the number '
            "of failed notifications within the configured horizon."
        ),
        prefill=fs.DefaultValue(float(60 * 60 * 24 * 7)),
        displayed_magnitudes=[fs.TimeMagnitude.DAY],
        custom_validate=[fs.validators.NumberInRange(min_value=60 * 60 * 24)],
    ),
)
