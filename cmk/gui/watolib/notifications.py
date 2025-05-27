#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Module for managing rule based notifications

The class 'NotificationRule' represents a single rule object that bridges
the mk file config format of a notification rule and an api response.

The classes RuleProperties, NotificationMethod, ContactSelection &
Condition represent parts of a Notification rule and are handled by
the NotificationRule class.

A NotificationRule object can be created from an api request
(APINotificationRule) or from a rule loaded from the notifications.mk
file (EventRule).

obj = NotificationRule.from_mk_file_format(EventRule)

obj = NotificationRule.from_api_request(APINotificationRule)

"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast, NotRequired, override, TypedDict

from cmk.ccc import store
from cmk.ccc.user import UserId

from cmk.utils.notify_types import (
    EventRule,
    NotificationParameterGeneralInfos,
    NotificationParameterID,
    NotificationParameterItem,
    NotificationParameterSpec,
    NotificationPluginNameStr,
    NotificationRuleID,
    NotifyBulkType,
    NotifyPlugin,
    PluginNameWithParameters,
)

from cmk.gui import userdb
from cmk.gui.i18n import _
from cmk.gui.rest_api_types.notifications_rule_types import (
    APIConditions,
    APIContactSelection,
    APINotificationMethod,
    APINotificationRule,
    APIRuleProperties,
    CheckboxMatchHostEvents,
    CheckboxMatchHostTags,
    CheckboxMatchServiceEvents,
    CheckboxNotificationBulking,
    CheckboxThrottlePeriodicNotifications,
    CheckboxWithBoolValue,
    CheckboxWithListOfStrValues,
    CheckboxWithStrValue,
    ContactMatchMacros,
    EventConsoleAlerts,
    MatchLabels,
    MatchServiceGroupsRegex,
    MatchServiceLevels,
    RestrictToNotificationNumbers,
)
from cmk.gui.rest_api_types.notifications_types import (
    CustomPluginAdapter,
    get_plugin_from_api_request,
    get_plugin_from_mk_file,
    PluginAdapter,
)
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.simple_config_file import (
    ConfigFileRegistry,
    WatoListConfigFile,
    WatoSimpleConfigFile,
)
from cmk.gui.watolib.user_scripts import load_notification_scripts
from cmk.gui.watolib.utils import wato_root_dir

logger = logging.getLogger(__name__)


class NotificationRuleConfigFile(WatoListConfigFile[EventRule]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=wato_root_dir() / "notifications.mk",
            config_variable="notification_rules",
            spec_class=EventRule,
        )

    @override
    def _load_file(self, *, lock: bool) -> list[EventRule]:
        notification_rules = store.load_from_mk_file(
            self._config_file_path,
            key=self._config_variable,
            default=list[Any](),  # Sigh... :-/
            lock=lock,
        )
        # Convert to new plug-in configuration format
        for rule in notification_rules:
            if "notify_method" in rule:
                method = rule["notify_method"]
                plugin = rule["notify_plugin"]
                del rule["notify_method"]
                rule["notify_plugin"] = (plugin, method)

        return notification_rules


def register(config_file_registry: ConfigFileRegistry) -> None:
    config_file_registry.register(NotificationRuleConfigFile())


def _generate_new_rule_id() -> NotificationRuleID:
    return NotificationRuleID(str(uuid.uuid4()))


def load_user_notification_rules() -> Mapping[UserId, list[EventRule]]:
    rules = {}
    for user_id, user in userdb.load_users().items():
        user_rules = user.get("notification_rules")
        if user_rules:
            rules[user_id] = user_rules
    return rules


@dataclass
class RuleProperties:
    description: str
    comment: str | None
    documentation_url: str | None
    do_not_apply_this_rule: CheckboxWithBoolValue
    allow_users_to_deactivate: CheckboxWithBoolValue
    user_id: str | None = None

    @classmethod
    def from_mk_file_format(cls, internal_config: EventRule) -> RuleProperties:
        return cls(
            description=internal_config["description"],
            comment=internal_config.get("comment"),
            documentation_url=internal_config.get("docu_url"),
            do_not_apply_this_rule=CheckboxWithBoolValue.from_mk_file_format(
                internal_config.get("disabled")
            ),
            allow_users_to_deactivate=CheckboxWithBoolValue.from_mk_file_format(
                internal_config.get("allow_disable")
            ),
            user_id=internal_config.get("user_id", ""),
        )

    @classmethod
    def from_api_request(cls, incoming: APIRuleProperties) -> RuleProperties:
        return cls(
            description=incoming["description"],
            comment=incoming["comment"],
            documentation_url=incoming["documentation_url"],
            do_not_apply_this_rule=CheckboxWithBoolValue.from_api_request(
                incoming["do_not_apply_this_rule"]
            ),
            allow_users_to_deactivate=CheckboxWithBoolValue.from_api_request(
                incoming["allow_users_to_deactivate"]
            ),
            user_id=incoming.get("user_id", ""),
        )

    def api_response(self) -> APIRuleProperties:
        r: APIRuleProperties = {
            "description": self.description,
            "comment": "" if self.comment is None else self.comment,
            "documentation_url": "" if self.documentation_url is None else self.documentation_url,
            "do_not_apply_this_rule": self.do_not_apply_this_rule.api_response(),
            "allow_users_to_deactivate": self.allow_users_to_deactivate.api_response(),
            "user_id": self.user_id,
        }
        return r

    def to_mk_file_format(self) -> dict[str, Any]:
        r: dict[str, Any] = {"description": self.description}

        if (allow_disable := self.allow_users_to_deactivate.to_mk_file_format()) is not None:
            r["allow_disable"] = allow_disable

        if (disabled := self.do_not_apply_this_rule.to_mk_file_format()) is not None:
            r["disabled"] = disabled

        if self.comment is not None:
            r["comment"] = self.comment

        if self.documentation_url is not None:
            r["docu_url"] = self.documentation_url

        if self.user_id is not None:
            r["user_id"] = self.user_id

        return r


class BulkNotAllowedException(Exception): ...


class NotificationMethodMkFormat(TypedDict):
    notify_plugin: PluginNameWithParameters
    bulk: NotRequired[NotifyBulkType | None]


@dataclass
class NotificationMethod:
    notification_bulking: CheckboxNotificationBulking
    notify_plugin: PluginAdapter | CustomPluginAdapter

    @classmethod
    def from_mk_file_format(
        cls, notify_plugin: PluginNameWithParameters, bulk_config: NotifyBulkType | None
    ) -> NotificationMethod:
        return cls(
            notify_plugin=get_plugin_from_mk_file(notify_plugin),
            notification_bulking=CheckboxNotificationBulking.from_mk_file_format(bulk_config),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotificationMethod) -> NotificationMethod:
        return cls(
            notification_bulking=CheckboxNotificationBulking.from_api_request(
                incoming.get("notification_bulking")
            ),
            notify_plugin=get_plugin_from_api_request(incoming["notify_plugin"]),
        )

    def api_response(self) -> APINotificationMethod:
        r: APINotificationMethod = {
            "notify_plugin": self.notify_plugin.api_response(),
        }
        if self._bulking_allowed():
            r["notification_bulking"] = self.notification_bulking.api_response()

        return r

    def to_mk_file_format(self) -> NotificationMethodMkFormat:
        r = NotificationMethodMkFormat(notify_plugin=self.notify_plugin.to_mk_file_format())
        if (bulk := self.notification_bulking.to_mk_file_format()) is not None:
            if not self._bulking_allowed():
                raise BulkNotAllowedException(
                    _("The notification script %s does not allow bulking.")
                    % self.notify_plugin.plugin_name
                )

            r["bulk"] = bulk

        return r

    def _bulking_allowed(self) -> bool:
        return self.notify_plugin.plugin_name in (
            plugin_name for plugin_name, info in load_notification_scripts().items() if info["bulk"]
        )


@dataclass
class ContactSelection:
    all_contacts_of_the_notified_object: CheckboxWithBoolValue
    all_users: CheckboxWithBoolValue
    all_users_with_an_email_address: CheckboxWithBoolValue
    the_following_users: CheckboxWithListOfStrValues
    members_of_contact_groups: CheckboxWithListOfStrValues
    explicit_email_addresses: CheckboxWithListOfStrValues
    restrict_by_contact_groups: CheckboxWithListOfStrValues
    restrict_by_custom_macros: ContactMatchMacros

    @classmethod
    def from_mk_file_format(cls, config: EventRule) -> ContactSelection:
        return cls(
            all_contacts_of_the_notified_object=CheckboxWithBoolValue.from_mk_file_format(
                config.get("contact_object")
            ),
            all_users=CheckboxWithBoolValue.from_mk_file_format(config.get("contact_all")),
            all_users_with_an_email_address=CheckboxWithBoolValue.from_mk_file_format(
                config.get("contact_all_with_email")
            ),
            the_following_users=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("contact_users")
            ),
            members_of_contact_groups=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("contact_groups")
            ),
            explicit_email_addresses=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("contact_emails")
            ),
            restrict_by_contact_groups=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("contact_match_groups")
            ),
            restrict_by_custom_macros=ContactMatchMacros.from_mk_file_format(
                config.get("contact_match_macros")
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APIContactSelection) -> ContactSelection:
        return cls(
            all_contacts_of_the_notified_object=CheckboxWithBoolValue.from_api_request(
                incoming["all_contacts_of_the_notified_object"]
            ),
            all_users=CheckboxWithBoolValue.from_api_request(incoming["all_users"]),
            all_users_with_an_email_address=CheckboxWithBoolValue.from_api_request(
                incoming["all_users_with_an_email_address"]
            ),
            the_following_users=CheckboxWithListOfStrValues.from_api_request(
                incoming["the_following_users"]
            ),
            members_of_contact_groups=CheckboxWithListOfStrValues.from_api_request(
                incoming["members_of_contact_groups"]
            ),
            explicit_email_addresses=CheckboxWithListOfStrValues.from_api_request(
                incoming["explicit_email_addresses"]
            ),
            restrict_by_contact_groups=CheckboxWithListOfStrValues.from_api_request(
                incoming["restrict_by_contact_groups"]
            ),
            restrict_by_custom_macros=ContactMatchMacros.from_api_request(
                incoming["restrict_by_custom_macros"]
            ),
        )

    def api_response(self) -> APIContactSelection:
        r: APIContactSelection = {
            "all_contacts_of_the_notified_object": self.all_contacts_of_the_notified_object.api_response(),
            "all_users": self.all_users.api_response(),
            "all_users_with_an_email_address": self.all_users_with_an_email_address.api_response(),
            "the_following_users": self.the_following_users.api_response(),
            "members_of_contact_groups": self.members_of_contact_groups.api_response(),
            "explicit_email_addresses": self.explicit_email_addresses.api_response(),
            "restrict_by_custom_macros": self.restrict_by_custom_macros.api_response(),
            "restrict_by_contact_groups": self.restrict_by_contact_groups.api_response(),
        }
        return r

    def to_mk_file_format(self) -> dict[str, Any]:
        r: dict[str, Any] = {
            "contact_object": self.all_contacts_of_the_notified_object.to_mk_file_format(),
            "contact_all": self.all_users.to_mk_file_format(),
            "contact_all_with_email": self.all_users_with_an_email_address.to_mk_file_format(),
            "contact_users": self.the_following_users.to_mk_file_format(),
            "contact_groups": self.members_of_contact_groups.to_mk_file_format(),
            "contact_emails": self.explicit_email_addresses.to_mk_file_format(),
            "contact_match_macros": self.restrict_by_custom_macros.to_mk_file_format(),
            "contact_match_groups": self.restrict_by_contact_groups.to_mk_file_format(),
        }
        return {k: v for k, v in r.items() if v is not None}


@dataclass
class Conditions:
    match_sites: CheckboxWithListOfStrValues
    match_folder: CheckboxWithStrValue
    match_host_groups: CheckboxWithListOfStrValues
    match_hosts: CheckboxWithListOfStrValues
    match_exclude_hosts: CheckboxWithListOfStrValues
    match_service_groups: CheckboxWithListOfStrValues
    match_exclude_service_groups: CheckboxWithListOfStrValues
    match_services: CheckboxWithListOfStrValues
    match_exclude_services: CheckboxWithListOfStrValues
    match_check_types: CheckboxWithListOfStrValues
    match_plugin_output: CheckboxWithStrValue
    # match_contacts: MatchContacts  # GUI shows There are no elements defined for this selection yet.
    match_contact_groups: CheckboxWithListOfStrValues
    match_only_during_timeperiod: CheckboxWithStrValue
    match_notification_comment: CheckboxWithStrValue
    match_service_levels: MatchServiceLevels
    match_service_labels: MatchLabels
    match_host_labels: MatchLabels
    match_service_groups_regex: MatchServiceGroupsRegex
    match_exclude_service_groups_regex: MatchServiceGroupsRegex
    restrict_to_notification_numbers: RestrictToNotificationNumbers
    match_host_tags: CheckboxMatchHostTags
    match_host_event_type: CheckboxMatchHostEvents
    match_service_event_type: CheckboxMatchServiceEvents
    throttle_periodic_notifications: CheckboxThrottlePeriodicNotifications
    event_console_alerts: EventConsoleAlerts

    @classmethod
    def from_mk_file_format(cls, config: EventRule) -> Conditions:
        return cls(
            match_sites=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("match_site"),
            ),
            match_folder=CheckboxWithStrValue.from_mk_file_format(
                config.get("match_folder"),
            ),
            match_host_groups=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("match_hostgroups"),
            ),
            match_hosts=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("match_hosts"),
            ),
            match_exclude_hosts=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("match_exclude_hosts"),
            ),
            match_service_groups=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("match_servicegroups"),
            ),
            match_exclude_service_groups=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("match_exclude_servicegroups"),
            ),
            match_services=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("match_services"),
            ),
            match_exclude_services=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("match_exclude_services"),
            ),
            match_check_types=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("match_checktype"),
            ),
            match_plugin_output=CheckboxWithStrValue.from_mk_file_format(
                config.get("match_plugin_output"),
            ),
            # match_contacts=, NOT IMPLEMENTED IN THE GUI
            match_contact_groups=CheckboxWithListOfStrValues.from_mk_file_format(
                config.get("match_contactgroups"),
            ),
            match_only_during_timeperiod=CheckboxWithStrValue.from_mk_file_format(
                config.get("match_timeperiod"),
            ),
            match_notification_comment=CheckboxWithStrValue.from_mk_file_format(
                config.get("match_notification_comment"),
            ),
            match_service_levels=MatchServiceLevels.from_mk_file_format(
                config.get("match_sl"),
            ),
            match_host_labels=MatchLabels.from_mk_file_format(
                config.get("match_hostlabels"),
            ),
            match_service_labels=MatchLabels.from_mk_file_format(
                config.get("match_servicelabels"),
            ),
            match_service_groups_regex=MatchServiceGroupsRegex.from_mk_file_format(
                config.get("match_servicegroups_regex"),
            ),
            match_exclude_service_groups_regex=MatchServiceGroupsRegex.from_mk_file_format(
                config.get("match_exclude_servicegroups_regex"),
            ),
            restrict_to_notification_numbers=RestrictToNotificationNumbers.from_mk_file_format(
                config.get("match_escalation"),
            ),
            match_host_tags=CheckboxMatchHostTags.from_mk_file_format(
                config.get("match_hosttags"),
            ),
            match_host_event_type=CheckboxMatchHostEvents.from_mk_file_format(
                config.get("match_host_event"),
            ),
            match_service_event_type=CheckboxMatchServiceEvents.from_mk_file_format(
                config.get("match_service_event"),
            ),
            throttle_periodic_notifications=CheckboxThrottlePeriodicNotifications.from_mk_file_format(
                config.get("match_escalation_throttle"),
            ),
            event_console_alerts=EventConsoleAlerts.from_mk_file_format(
                config.get("match_ec"),
            ),
        )

    @classmethod
    def from_api_request(cls, incoming: APIConditions) -> Conditions:
        return cls(
            match_sites=CheckboxWithListOfStrValues.from_api_request(
                incoming["match_sites"],
            ),
            match_folder=CheckboxWithStrValue.from_api_request(
                incoming["match_folder"],
            ),
            match_host_groups=CheckboxWithListOfStrValues.from_api_request(
                incoming["match_host_groups"]
            ),
            match_hosts=CheckboxWithListOfStrValues.from_api_request(
                incoming["match_hosts"],
            ),
            match_exclude_hosts=CheckboxWithListOfStrValues.from_api_request(
                incoming["match_exclude_hosts"]
            ),
            match_service_groups=CheckboxWithListOfStrValues.from_api_request(
                incoming["match_service_groups"]
            ),
            match_exclude_service_groups=CheckboxWithListOfStrValues.from_api_request(
                incoming["match_exclude_service_groups"]
            ),
            match_services=CheckboxWithListOfStrValues.from_api_request(
                incoming["match_services"],
            ),
            match_exclude_services=CheckboxWithListOfStrValues.from_api_request(
                incoming["match_exclude_services"]
            ),
            match_check_types=CheckboxWithListOfStrValues.from_api_request(
                incoming["match_check_types"]
            ),
            match_plugin_output=CheckboxWithStrValue.from_api_request(
                incoming["match_plugin_output"]
            ),
            # match_contacts: MatchContacts  # GUI shows There are no elements defined for this selection yet.
            match_contact_groups=CheckboxWithListOfStrValues.from_api_request(
                incoming["match_contact_groups"]
            ),
            match_only_during_timeperiod=CheckboxWithStrValue.from_api_request(
                incoming["match_only_during_time_period"]
            ),
            match_notification_comment=CheckboxWithStrValue.from_api_request(
                incoming["match_notification_comment"]
            ),
            match_service_levels=MatchServiceLevels.from_api_request(
                incoming["match_service_levels"]
            ),
            match_service_labels=MatchLabels.from_api_request(
                incoming["match_service_labels"],
            ),
            match_host_labels=MatchLabels.from_api_request(
                incoming["match_host_labels"],
            ),
            match_service_groups_regex=MatchServiceGroupsRegex.from_api_request(
                incoming["match_service_groups_regex"]
            ),
            match_exclude_service_groups_regex=MatchServiceGroupsRegex.from_api_request(
                incoming["match_exclude_service_groups_regex"]
            ),
            restrict_to_notification_numbers=RestrictToNotificationNumbers.from_api_request(
                incoming["restrict_to_notification_numbers"]
            ),
            match_host_tags=CheckboxMatchHostTags.from_api_request(
                incoming["match_host_tags"],
            ),
            match_host_event_type=CheckboxMatchHostEvents.from_api_request(
                incoming["match_host_event_type"]
            ),
            match_service_event_type=CheckboxMatchServiceEvents.from_api_request(
                incoming["match_service_event_type"]
            ),
            throttle_periodic_notifications=CheckboxThrottlePeriodicNotifications.from_api_request(
                incoming["throttle_periodic_notifications"]
            ),
            event_console_alerts=EventConsoleAlerts.from_api_request(
                incoming["event_console_alerts"]
            ),
        )

    def api_response(self) -> APIConditions:
        r: APIConditions = {
            "match_sites": self.match_sites.api_response(),
            "match_folder": self.match_folder.api_response(),
            "match_host_tags": self.match_host_tags.api_response(),
            "match_host_labels": self.match_host_labels.api_response(),
            "match_host_groups": self.match_host_groups.api_response(),
            "match_hosts": self.match_hosts.api_response(),
            "match_exclude_hosts": self.match_exclude_hosts.api_response(),
            "match_service_labels": self.match_service_labels.api_response(),
            "match_service_groups": self.match_service_groups.api_response(),
            "match_exclude_service_groups": self.match_exclude_service_groups.api_response(),
            "match_service_groups_regex": self.match_service_groups_regex.api_response(),
            "match_exclude_service_groups_regex": self.match_exclude_service_groups_regex.api_response(),
            "match_services": self.match_services.api_response(),
            "match_exclude_services": self.match_exclude_services.api_response(),
            "match_check_types": self.match_check_types.api_response(),
            "match_plugin_output": self.match_plugin_output.api_response(),
            "match_contact_groups": self.match_contact_groups.api_response(),
            "match_service_levels": self.match_service_levels.api_response(),
            "match_only_during_time_period": self.match_only_during_timeperiod.api_response(),
            "match_host_event_type": self.match_host_event_type.api_response(),
            "match_service_event_type": self.match_service_event_type.api_response(),
            "restrict_to_notification_numbers": self.restrict_to_notification_numbers.api_response(),
            "throttle_periodic_notifications": self.throttle_periodic_notifications.api_response(),
            "match_notification_comment": self.match_notification_comment.api_response(),
            "event_console_alerts": self.event_console_alerts.api_response(),
        }
        return r

    def to_mk_file_format(self) -> dict[str, Any]:
        r: dict[str, Any] = {
            "match_site": self.match_sites.to_mk_file_format(),
            "match_folder": self.match_folder.to_mk_file_format(),
            "match_hosttags": self.match_host_tags.to_mk_file_format(),
            "match_hostlabels": self.match_host_labels.to_mk_file_format(),
            "match_hostgroups": self.match_host_groups.to_mk_file_format(),
            "match_hosts": self.match_hosts.to_mk_file_format(),
            "match_exclude_hosts": self.match_exclude_hosts.to_mk_file_format(),
            "match_servicelabels": self.match_service_labels.to_mk_file_format(),
            "match_servicegroups": self.match_service_groups.to_mk_file_format(),
            "match_exclude_servicegroups": self.match_exclude_service_groups.to_mk_file_format(),
            "match_servicegroups_regex": self.match_service_groups_regex.to_mk_file_format(),
            "match_exclude_servicegroups_regex": self.match_exclude_service_groups_regex.to_mk_file_format(),
            "match_services": self.match_services.to_mk_file_format(),
            "match_exclude_services": self.match_exclude_services.to_mk_file_format(),
            "match_checktype": self.match_check_types.to_mk_file_format(),
            "match_plugin_output": self.match_plugin_output.to_mk_file_format(),
            "match_contactgroups": self.match_contact_groups.to_mk_file_format(),
            "match_sl": self.match_service_levels.to_mk_file_format(),
            "match_timeperiod": self.match_only_during_timeperiod.to_mk_file_format(),
            "match_host_event": self.match_host_event_type.to_mk_file_format(),
            "match_service_event": self.match_service_event_type.to_mk_file_format(),
            "match_escalation": self.restrict_to_notification_numbers.to_mk_file_format(),
            "match_escalation_throttle": self.throttle_periodic_notifications.to_mk_file_format(),
            "match_notification_comment": self.match_notification_comment.to_mk_file_format(),
            "match_ec": self.event_console_alerts.to_mk_file_format(),
        }
        return {k: v for k, v in r.items() if v is not None}


def _get_parameters_for_rule_with_id(
    notify_plugin_name: NotificationPluginNameStr,
    params_id: NotificationParameterID | None,
) -> PluginNameWithParameters:
    if params_id is None:
        return (notify_plugin_name, None)

    all_parameters = NotificationParameterConfigFile().load_for_reading()
    parameters_for_method = all_parameters.get(notify_plugin_name, {})
    if params_id not in parameters_for_method:
        return (notify_plugin_name, None)

    return (notify_plugin_name, parameters_for_method[params_id]["parameter_properties"])


def _create_parameters_for_rule(
    notify_plugin: PluginNameWithParameters, pprint_value: bool
) -> NotifyPlugin:
    if notify_plugin[1] is None:
        return (notify_plugin[0], None)

    notification_parameters = NotificationParameterConfigFile().load_for_reading()
    new_params_id = NotificationParameterID(str(uuid.uuid4()))
    new_notification_parameter_item = NotificationParameterItem(
        general=NotificationParameterGeneralInfos(
            description="",
            comment="",
            docu_url="",
        ),
        parameter_properties=notify_plugin[1],
    )

    if notify_plugin[0] not in notification_parameters:
        notification_parameters[notify_plugin[0]] = {new_params_id: new_notification_parameter_item}
    else:
        notification_parameters[notify_plugin[0]].update(
            {new_params_id: new_notification_parameter_item}
        )

    NotificationParameterConfigFile().save(notification_parameters, pprint_value)
    return (notify_plugin[0], new_params_id)


@dataclass
class NotificationRule:
    rule_properties: RuleProperties
    notification_method: NotificationMethod
    contact_selection: ContactSelection
    conditions: Conditions
    rule_id: NotificationRuleID

    @classmethod
    def from_mk_file_format(cls, config: EventRule) -> NotificationRule:
        notify_plugin_name, params_id = config["notify_plugin"]
        return cls(
            rule_properties=RuleProperties.from_mk_file_format(config),
            notification_method=NotificationMethod.from_mk_file_format(
                _get_parameters_for_rule_with_id(notify_plugin_name, params_id),
                config.get("bulk"),
            ),
            contact_selection=ContactSelection.from_mk_file_format(config),
            conditions=Conditions.from_mk_file_format(config),
            rule_id=config["rule_id"],
        )

    @classmethod
    def from_api_request(
        cls, incoming: APINotificationRule, rule_id: NotificationRuleID | None = None
    ) -> NotificationRule:
        return cls(
            rule_properties=RuleProperties.from_api_request(incoming["rule_properties"]),
            contact_selection=ContactSelection.from_api_request(incoming["contact_selection"]),
            conditions=Conditions.from_api_request(incoming["conditions"]),
            notification_method=NotificationMethod.from_api_request(
                incoming["notification_method"]
            ),
            rule_id=rule_id if rule_id is not None else _generate_new_rule_id(),
        )

    def api_response(self) -> APINotificationRule:
        r: APINotificationRule = {
            "rule_properties": self.rule_properties.api_response(),
            "notification_method": self.notification_method.api_response(),
            "conditions": self.conditions.api_response(),
            "contact_selection": self.contact_selection.api_response(),
        }
        return r

    def to_mk_file_format(self, pprint_value: bool) -> EventRule:
        r: dict[str, Any] = {"rule_id": self.rule_id}
        notify_method = self.notification_method.to_mk_file_format()
        if "bulk" in notify_method:
            r["bulk"] = notify_method["bulk"]

        r["notify_plugin"] = _create_parameters_for_rule(
            notify_method["notify_plugin"], pprint_value
        )

        r.update(self.rule_properties.to_mk_file_format() | self.conditions.to_mk_file_format())

        if self.contact_selection is not None:
            r.update(self.contact_selection.to_mk_file_format())

        er = cast(EventRule, r)
        return er


def find_usages_of_contact_group_in_notification_rules(
    name: str, _settings: GlobalSettings
) -> list[tuple[str, str]]:
    used_in: list[tuple[str, str]] = []
    for rule in NotificationRuleConfigFile().load_for_reading():
        if _used_in_notification_rule(name, rule):
            title = "{}: {}".format(_("Notification rule"), rule.get("description", ""))
            used_in.append((title, "wato.py?mode=notifications"))

    for user_id, user_rules in load_user_notification_rules().items():
        for rule in user_rules:
            if _used_in_notification_rule(name, rule):
                title = "{}: {}".format(
                    _("Notification rules of user %s") % user_id,
                    rule.get("description", ""),
                )
                used_in.append((title, "wato.py?mode=user_notifications&user=%s" % user_id))

    return used_in


def _used_in_notification_rule(name: str, rule: EventRule) -> bool:
    return name in rule.get("contact_groups", []) or name in rule.get("match_contactgroups", [])


def find_timeperiod_usage_in_notification_rules(time_period_name: str) -> list[tuple[str, str]]:
    used_in: list[tuple[str, str]] = []
    for index, rule in enumerate(NotificationRuleConfigFile().load_for_reading()):
        used_in += userdb.find_timeperiod_usage_in_notification_rule(time_period_name, index, rule)
    return used_in


class NotificationParameterConfigFile(WatoSimpleConfigFile[NotificationParameterSpec]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=wato_root_dir() / "notification_parameter.mk",
            config_variable="notification_parameter",
            spec_class=NotificationParameterSpec,
        )
