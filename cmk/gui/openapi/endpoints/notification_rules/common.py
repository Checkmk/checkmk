#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.rest_api_types.notifications_rule_types import APINotificationRule
from cmk.utils.notify_types import PluginOptions

EVENT_CONSOLE_ALERTS_DESCRIPTION = """The Event Console can have events create notifications
in Checkmk. These notifications are processed by the rule based notification system of
Checkmk. This condition lets you distinguish them from host and service notifications and
gives you access to special event fields.

With this condition disabled, Event Console alerts do not match a rule that restricts host or
service events. Since `match_host_event_type` and `match_service_event_type` are enabled by
default, that is the case for every rule which does not explicitly disable both of them. Only
a rule that disables both matches all events, Event Console alerts included."""

EVENT_CONSOLE_MATCH_TYPE_DESCRIPTION = """How this rule treats Event Console alerts.

`match_only_event_console_alerts`: Event Console alerts match this rule. If at least one
filter is set in `values`, the rule matches Event Console alerts exclusively and host and
service notifications no longer match it. Without any filter, Event Console alerts match in
addition to the host and service events configured in `match_host_event_type` and
`match_service_event_type`.

`do_not_match_event_console_alerts`: Event Console alerts never match this rule. Host and
service notifications match according to the other conditions of the rule."""


def notification_rule_request_example() -> APINotificationRule:
    r: APINotificationRule = {
        "rule_properties": {
            "description": "A description or title of this rule.",
            "comment": "A example comment.",
            "documentation_url": "http://link/to/documentation",
            "do_not_apply_this_rule": {"state": "disabled"},
            "allow_users_to_deactivate": {"state": "enabled"},
        },
        "notification_method": {
            "notify_plugin": {
                "option": PluginOptions.WITH_PARAMS.value,
                "plugin_params": {
                    "plugin_name": "mail",
                    "from_details": {"state": "disabled"},
                    "reply_to": {"state": "disabled"},
                    "subject_for_host_notifications": {"state": "disabled"},
                    "subject_for_service_notifications": {"state": "disabled"},
                    "info_to_be_displayed_in_the_email_body": {"state": "disabled"},
                    "insert_html_section_between_body_and_table": {"state": "disabled"},
                    "url_prefix_for_links_to_checkmk": {"state": "disabled"},
                    "sort_order_for_bulk_notifications": {"state": "disabled"},
                    "send_separate_notification_to_every_recipient": {"state": "disabled"},
                    "enable_sync_smtp": {"state": "disabled"},
                    "display_graphs_among_each_other": {"state": "disabled"},
                    "graphs_per_notification": {"state": "disabled"},
                    "bulk_notifications_with_graphs": {"state": "disabled"},
                },
            },
            "notification_bulking": {"state": "disabled"},
        },
        "contact_selection": {
            "all_contacts_of_the_notified_object": {"state": "disabled"},
            "all_users": {"state": "disabled"},
            "all_users_with_an_email_address": {"state": "disabled"},
            "the_following_users": {"state": "disabled"},
            "members_of_contact_groups": {"state": "disabled"},
            "explicit_email_addresses": {"state": "disabled"},
            "restrict_by_custom_macros": {"state": "disabled"},
            "restrict_by_contact_groups": {"state": "disabled"},
        },
        "conditions": {
            "match_sites": {"state": "disabled"},
            "match_folder": {"state": "disabled"},
            "match_host_tags": {"state": "disabled"},
            "match_host_labels": {"state": "disabled"},
            "match_host_groups": {"state": "disabled"},
            "match_hosts": {"state": "disabled"},
            "match_exclude_hosts": {"state": "disabled"},
            "match_service_labels": {"state": "disabled"},
            "match_service_groups": {"state": "disabled"},
            "match_exclude_service_groups": {"state": "disabled"},
            "match_service_groups_regex": {"state": "disabled"},
            "match_exclude_service_groups_regex": {"state": "disabled"},
            "match_services": {"state": "disabled"},
            "match_exclude_services": {"state": "disabled"},
            "match_check_types": {"state": "disabled"},
            "match_plugin_output": {"state": "disabled"},
            "match_contact_groups": {"state": "disabled"},
            "match_service_levels": {"state": "disabled"},
            "match_only_during_time_period": {"state": "disabled"},
            "match_host_event_type": {"state": "disabled"},
            "match_service_event_type": {"state": "disabled"},
            "restrict_to_notification_numbers": {"state": "disabled"},
            "throttle_periodic_notifications": {"state": "disabled"},
            "match_notification_comment": {"state": "disabled"},
            "event_console_alerts": {"state": "disabled"},
        },
    }
    return r
