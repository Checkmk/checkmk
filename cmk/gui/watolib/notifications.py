#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
""" Module for managing rule based notifications

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
from typing import Any, cast

import cmk.utils.store as store
from cmk.utils.notify_types import (
    BuiltInPluginNames,
    EventRule,
    NotificationRuleID,
    NotifyBulkType,
    NotifyPlugin,
)
from cmk.utils.type_defs import UserId

import cmk.gui.userdb as userdb
from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.watolib.user_scripts import load_notification_scripts
from cmk.gui.watolib.utils import wato_root_dir

from .notifications_rule_types import (
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
from .notifications_types import (
    get_plugin_from_api_request,
    get_plugin_from_mk_file,
    NotificationPlugin,
)

logger = logging.getLogger(__name__)


def _generate_new_rule_id() -> NotificationRuleID:
    return NotificationRuleID(str(uuid.uuid4()))


def load_notification_rules(lock: bool = False) -> list[EventRule]:
    filename = wato_root_dir() + "notifications.mk"
    notification_rules = store.load_from_mk_file(filename, "notification_rules", [], lock=lock)

    # Convert to new plugin configuration format
    for rule in notification_rules:
        if "notify_method" in rule:
            method = rule["notify_method"]
            plugin = rule["notify_plugin"]
            del rule["notify_method"]
            rule["notify_plugin"] = (plugin, method)

    return notification_rules


def save_notification_rules(rules: list[EventRule]) -> None:
    store.mkdir(wato_root_dir())
    store.save_to_mk_file(
        wato_root_dir() + "notifications.mk",
        "notification_rules",
        rules,
        pprint_value=active_config.wato_pprint_config,
    )


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


class BulkNotAllowedException(Exception):
    ...


@dataclass
class NotificationMethod:
    notification_bulking: CheckboxNotificationBulking
    notify_plugin: NotificationPlugin

    @classmethod
    def from_mk_file_format(
        cls, notify_plugin: NotifyPlugin, bulk_config: NotifyBulkType | None
    ) -> NotificationMethod:
        plugin_name, pluginparams = notify_plugin
        builtin_plugin_name = cast(BuiltInPluginNames, plugin_name)

        return cls(
            notify_plugin=get_plugin_from_mk_file(builtin_plugin_name, pluginparams),
            notification_bulking=CheckboxNotificationBulking.from_mk_file_format(bulk_config),
        )

    @classmethod
    def from_api_request(cls, incoming: APINotificationMethod) -> NotificationMethod:
        return cls(
            notification_bulking=CheckboxNotificationBulking.from_api_request(
                incoming["notification_bulking"]
            ),
            notify_plugin=get_plugin_from_api_request(incoming["notify_plugin"]),
        )

    def api_response(self) -> APINotificationMethod:
        r: APINotificationMethod = {
            "notify_plugin": self.notify_plugin.api_response(),
            "notification_bulking": self.notification_bulking.api_response(),
        }
        return r

    def to_mk_file_format(self) -> dict[str, Any]:
        plugin_name, plugin_params = self.notify_plugin.to_mk_file_format()
        r: dict[str, Any] = {"notify_plugin": (plugin_name, plugin_params)}

        notification_scripts = load_notification_scripts()
        if plugin_name in notification_scripts:
            bulk_allowed = notification_scripts[plugin_name]["bulk"]
        else:
            bulk_allowed = False

        if (bulk := self.notification_bulking.to_mk_file_format()) is not None:
            if not bulk_allowed:
                raise BulkNotAllowedException(
                    _("The notification script %s does not allow bulking.") % plugin_name
                )

            r["bulk"] = bulk

        return r


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
            "match_service_level": self.match_service_levels.to_mk_file_format(),
            "match_only_during_timeperiod": self.match_only_during_timeperiod.to_mk_file_format(),
            "match_host_event": self.match_host_event_type.to_mk_file_format(),
            "match_service_event": self.match_service_event_type.to_mk_file_format(),
            "match_escalation": self.restrict_to_notification_numbers.to_mk_file_format(),
            "match_escalation_throttle": self.throttle_periodic_notifications.to_mk_file_format(),
            "match_notification_comment": self.match_notification_comment.to_mk_file_format(),
            "match_ec": self.event_console_alerts.to_mk_file_format(),
        }
        return {k: v for k, v in r.items() if v is not None}


@dataclass
class NotificationRule:
    rule_properties: RuleProperties
    notification_method: NotificationMethod
    contact_selection: ContactSelection
    conditions: Conditions
    rule_id: NotificationRuleID

    @classmethod
    def from_mk_file_format(cls, config: EventRule) -> NotificationRule:
        return cls(
            rule_properties=RuleProperties.from_mk_file_format(config),
            notification_method=NotificationMethod.from_mk_file_format(
                config["notify_plugin"], config.get("bulk")
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

    def to_mk_file_format(self) -> EventRule:
        r: dict[str, Any] = {"rule_id": self.rule_id}
        r.update(
            self.rule_properties.to_mk_file_format()
            | self.notification_method.to_mk_file_format()
            | self.conditions.to_mk_file_format()
        )
        if self.contact_selection is not None:
            r.update(self.contact_selection.to_mk_file_format())

        er = cast(EventRule, r)
        return er
