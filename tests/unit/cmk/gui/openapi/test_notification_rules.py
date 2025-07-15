#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Generator, Iterator
from typing import Any, get_args, Literal

import pytest

from tests.testlib.unit.rest_api_client import ClientRegistry

from cmk.ccc import version

from cmk.utils import paths
from cmk.utils.notify_types import CaseStateStr, CustomPluginName, IncidentStateStr, PluginOptions
from cmk.utils.tags import TagID

from cmk.gui.openapi.endpoints.notification_rules.request_example import (
    notification_rule_request_example,
)
from cmk.gui.openapi.endpoints.site_management.common import (
    default_config_example as _default_config,
)
from cmk.gui.rest_api_types.notifications_rule_types import (
    AckStateAPI,
    API_BasicAuthExplicit,
    API_BasicAuthStore,
    API_ExplicitToken,
    API_JiraData,
    API_PushOverData,
    API_ServiceNowData,
    API_StoreToken,
    APIConditions,
    APIContactSelection,
    APINotificationRule,
    APIPluginDict,
    APIPluginList,
    APIRuleProperties,
    DowntimeStateAPI,
    MatchHostEventsAPIType,
    MatchServiceEventsAPIType,
    MgmtTypeCaseAPI,
    MgmtTypeCaseParamsAPI,
    MgmtTypeIncidentAPI,
    MgmtTypeIncidentParamsAPI,
    NotificationBulkingAPIAttrs,
    NotificationBulkingAPIValueType,
    PluginType,
    RecoveryStateCaseAPI,
    RecoveryStateIncidentAPI,
)
from cmk.gui.valuespec import Checkbox, Dictionary, Integer, ListOfStrings, TextInput
from cmk.gui.watolib.notification_parameter import (
    notification_parameter_registry,
    register_notification_parameters,
)
from cmk.gui.watolib.user_scripts import load_notification_scripts

managedtest = pytest.mark.skipif(
    version.edition(paths.omd_root) is not version.Edition.CME, reason="see #7213"
)


def test_get_notification_rule(clients: ClientRegistry) -> None:
    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(config)
    r2 = clients.RuleNotification.get(rule_id=r1.json["id"])
    assert r2.json["extensions"] == {"rule_config": config}


def test_get_notification_rules(clients: ClientRegistry) -> None:
    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(config)
    r2 = clients.RuleNotification.create(config)
    r3 = clients.RuleNotification.get_all()
    rules = r3.json["value"]
    assert rules[0]["id"] == r1.json["id"]
    assert rules[1]["id"] == r2.json["id"]


def test_create_notification_rule(clients: ClientRegistry) -> None:
    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(config)
    assert r1.json["extensions"] == {"rule_config": config}


@managedtest
def test_update_rule_with_full_contact_selection_data(clients: ClientRegistry) -> None:
    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(config)

    clients.ContactGroup.bulk_create(
        groups=(
            {"name": "cg1", "alias": "cg1", "customer": "provider"},
            {"name": "cg2", "alias": "cg2", "customer": "provider"},
        )
    )

    config["contact_selection"] = {
        "all_contacts_of_the_notified_object": {"state": "enabled"},
        "all_users": {"state": "enabled"},
        "all_users_with_an_email_address": {"state": "enabled"},
        "the_following_users": {"state": "enabled", "value": []},
        "members_of_contact_groups": {"state": "enabled", "value": ["cg1", "cg2"]},
        "explicit_email_addresses": {
            "state": "enabled",
            "value": ["monkey@example.com", "thelionsleepstonight@example.com"],
        },
        "restrict_by_custom_macros": {"state": "enabled", "value": []},
        "restrict_by_contact_groups": {"state": "enabled", "value": []},
    }

    r2 = clients.RuleNotification.edit(r1.json["id"], config)
    assert r2.json["extensions"] == {"rule_config": config}


def test_create_rule_delete_rule(clients: ClientRegistry) -> None:
    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)
    clients.RuleNotification.get(rule_id=r1.json["id"])
    clients.RuleNotification.delete(rule_id=r1.json["id"])
    clients.RuleNotification.get(
        rule_id=r1.json["id"],
        expect_ok=False,
    ).assert_status_code(404)


def setup_site_data(clients: ClientRegistry) -> None:
    clients.ContactGroup.bulk_create(
        groups=(
            {"name": "cg1", "alias": "cg1", "customer": "provider"},
            {"name": "cg2", "alias": "cg2", "customer": "provider"},
        )
    )

    clients.TimePeriod.create(
        time_period_data={
            "name": "time_period_1",
            "alias": "time_period_1",
            "active_time_ranges": [{"day": "all"}],
            "exceptions": [{"date": "2020-01-01"}],
        }
    )

    clients.HostGroup.bulk_create(
        groups=(
            {"name": "hg1", "alias": "hg1", "customer": "provider"},
            {"name": "hg2", "alias": "hg2", "customer": "provider"},
        )
    )

    clients.ServiceGroup.bulk_create(
        groups=(
            {"name": "sg1", "alias": "sg1", "customer": "provider"},
            {"name": "sg2", "alias": "hs2", "customer": "provider"},
        )
    )
    clients.SiteManagement.create(site_config=_default_config())

    clients.Password.create(
        ident="some_store_id",
        title="foobar",
        password="tt",
        shared=["all"],
        editable_by="admin",
        customer="global",
    )

    clients.Folder.create(title="test_folder1", parent="~")
    clients.Folder.create(title="test_folder2", parent="~test_folder1")


def host_event_types(value: bool) -> MatchHostEventsAPIType:
    event_types_for_host: MatchHostEventsAPIType = {
        "up_down": value,
        "up_unreachable": value,
        "down_up": value,
        "down_unreachable": value,
        "unreachable_down": value,
        "unreachable_up": value,
        "any_up": value,
        "any_down": value,
        "any_unreachable": value,
        "start_or_end_of_flapping_state": value,
        "start_or_end_of_scheduled_downtime": value,
        "acknowledgement_of_problem": value,
        "alert_handler_execution_successful": value,
        "alert_handler_execution_failed": value,
    }
    return event_types_for_host


def service_event_types(value: bool) -> MatchServiceEventsAPIType:
    event_types_for_service: MatchServiceEventsAPIType = {
        "ok_warn": value,
        "ok_ok": value,
        "ok_crit": value,
        "ok_unknown": value,
        "warn_ok": value,
        "warn_crit": value,
        "warn_unknown": value,
        "crit_ok": value,
        "crit_warn": value,
        "crit_unknown": value,
        "unknown_ok": value,
        "unknown_warn": value,
        "unknown_crit": value,
        "any_ok": value,
        "any_warn": value,
        "any_crit": value,
        "any_unknown": value,
        "start_or_end_of_flapping_state": value,
        "start_or_end_of_scheduled_downtime": value,
        "acknowledgement_of_problem": value,
        "alert_handler_execution_successful": value,
        "alert_handler_execution_failed": value,
    }
    return event_types_for_service


def conditions_set_1() -> APIConditions:
    """Here we are testing sets of 'conditions' for rule notifications.
    The conditions are being tested with sets to cover all valid field values.
    We are testing in sets to reduce the number of api requests and therefore
    reduce the test time. These sets are not testing anything specific to any
    of the fields that are being passed, only that the schemas accept the
    correct fields and field values.
    """

    conditions: APIConditions = {
        "match_sites": {"state": "enabled", "value": ["site_id_1"]},
        "match_folder": {
            "state": "enabled",
            "value": "~",
        },
        "match_host_tags": {
            "state": "enabled",
            "value": [],
        },
        "match_host_labels": {
            "state": "enabled",
            "value": [{"key": "label1", "value": "value1"}, {"key": "label2", "value": "value2"}],
        },
        "match_host_groups": {"state": "enabled", "value": ["hg1", "hg2"]},
        "match_hosts": {"state": "enabled", "value": ["example.com"]},
        "match_exclude_hosts": {"state": "enabled", "value": ["example.com"]},
        "match_service_labels": {
            "state": "enabled",
            "value": [{"key": "label1", "value": "value1"}, {"key": "label2", "value": "value2"}],
        },
        "match_service_groups": {"state": "enabled", "value": ["sg1", "sg2"]},
        "match_exclude_service_groups": {"state": "enabled", "value": ["sg1", "sg2"]},
        "match_service_groups_regex": {
            "state": "enabled",
            "value": {"match_type": "match_id", "regex_list": ["^abc", "^def"]},
        },
        "match_exclude_service_groups_regex": {
            "state": "enabled",
            "value": {"match_type": "match_alias", "regex_list": ["alias1", "alias2"]},
        },
        "match_services": {"state": "enabled", "value": ["str1", "str2", "str3"]},
        "match_exclude_services": {"state": "enabled", "value": ["str4", "str5", "str6"]},
        "match_check_types": {"state": "enabled", "value": ["ch1", "ch2", "ch3"]},
        "match_plugin_output": {"state": "enabled", "value": "str1"},
        "match_contact_groups": {"state": "enabled", "value": ["cg1", "cg2"]},
        "match_service_levels": {
            "state": "enabled",
            "value": {"from_level": 0, "to_level": 30},
        },
        "match_only_during_time_period": {"state": "enabled", "value": "time_period_1"},
        "match_host_event_type": {
            "state": "enabled",
            "value": host_event_types(True),
        },
        "match_service_event_type": {
            "state": "enabled",
            "value": service_event_types(True),
        },
        "restrict_to_notification_numbers": {
            "state": "enabled",
            "value": {"beginning_from": 2, "up_to": 493},
        },
        "throttle_periodic_notifications": {
            "state": "enabled",
            "value": {"beginning_from": 2, "send_every_nth_notification": 493},
        },
        "match_notification_comment": {"state": "enabled", "value": "str1"},
        "event_console_alerts": {
            "state": "enabled",
            "value": {"match_type": "do_not_match_event_console_alerts"},
        },
    }
    return conditions


def conditions_set_2() -> APIConditions:
    conditions: APIConditions = {
        "match_folder": {
            "state": "enabled",
            "value": "~test_folder1~test_folder2",
        },
        "match_host_tags": {
            "state": "enabled",
            "value": [
                {
                    "tag_type": "aux_tag",
                    "tag_id": TagID("ip-v4"),
                    "operator": "is_set",
                },
                {
                    "tag_type": "tag_group",
                    "tag_group_id": "piggyback",
                    "operator": "is_not",
                    "tag_id": TagID("auto-piggyback"),
                },
            ],
        },
        "match_service_groups_regex": {
            "state": "enabled",
            "value": {"match_type": "match_alias", "regex_list": ["alias1", "alias2"]},
        },
        "match_exclude_service_groups_regex": {
            "state": "enabled",
            "value": {"match_type": "match_id", "regex_list": ["^abc", "^def"]},
        },
        "match_host_event_type": {
            "state": "enabled",
            "value": host_event_types(False),
        },
        "match_service_event_type": {
            "state": "enabled",
            "value": service_event_types(False),
        },
        "event_console_alerts": {
            "state": "enabled",
            "value": {
                "match_type": "match_only_event_console_alerts",
                "values": {
                    "match_rule_ids": {
                        "state": "enabled",
                        "value": ["rule_id1", "rule_id2"],
                    },
                    "match_syslog_priority": {
                        "state": "enabled",
                        "value": {"from_priority": "emerg", "to_priority": "emerg"},
                    },
                    "match_syslog_facility": {
                        "state": "enabled",
                        "value": "kern",
                    },
                    "match_event_comment": {
                        "state": "enabled",
                        "value": "comment_1",
                    },
                },
            },
        },
    }
    return conditions


def conditions_set_3() -> APIConditions:
    conditions: APIConditions = {
        "match_folder": {
            "state": "enabled",
            "value": "~test_folder1",
        },
        "event_console_alerts": {
            "state": "enabled",
            "value": {
                "match_type": "match_only_event_console_alerts",
                "values": {
                    "match_rule_ids": {"state": "disabled"},
                    "match_syslog_priority": {"state": "disabled"},
                    "match_syslog_facility": {"state": "disabled"},
                    "match_event_comment": {"state": "disabled"},
                },
            },
        },
    }
    return conditions


@managedtest
@pytest.mark.usefixtures("mock_password_file_regeneration")
@pytest.mark.parametrize("testdata", [conditions_set_1(), conditions_set_2(), conditions_set_3()])
def test_create_and_update_rule_with_conditions_data_200(
    clients: ClientRegistry,
    testdata: APIConditions,
) -> None:
    setup_site_data(clients)
    clients.HostConfig.create(host_name="example.com", folder="/")

    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)

    config["conditions"].update(testdata)
    r2 = clients.RuleNotification.edit(
        rule_id=r1.json["id"],
        rule_config=config,
    )
    assert r2.json["extensions"] == {"rule_config": config}


def invalid_conditions() -> Iterator:
    for k in notification_rule_request_example()["conditions"]:
        config = notification_rule_request_example()
        config["conditions"].update({k: {"state": "enabled"}})  # type: ignore[misc]
        yield config


@managedtest
@pytest.mark.parametrize("testdata", invalid_conditions())
@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_create_and_update_rule_with_conditions_data_400(
    clients: ClientRegistry,
    testdata: APIConditions,
) -> None:
    setup_site_data(clients)
    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)
    config["conditions"].update(testdata)
    clients.RuleNotification.edit(
        rule_id=r1.json["id"],
        rule_config=config,
        expect_ok=False,
    ).assert_status_code(400)


rule_properties_testdata: list[APIRuleProperties] = [
    {"allow_users_to_deactivate": {"state": "enabled"}},
    {"do_not_apply_this_rule": {"state": "disabled"}},
    {"do_not_apply_this_rule": {"state": "enabled"}},
    {"description": "updated description"},
    {"comment": "updated_comment"},
    {"documentation_url": "updated_doc_url"},
]


@pytest.mark.parametrize("testdata", rule_properties_testdata)
def test_create_and_update_rule_with_properties_data(
    clients: ClientRegistry,
    testdata: APIRuleProperties,
) -> None:
    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)
    config["rule_properties"].update(testdata)
    r2 = clients.RuleNotification.edit(
        rule_id=r1.json["id"],
        rule_config=config,
    )
    assert r2.json["extensions"] == {"rule_config": config}


contact_selection_testdata: list[APIContactSelection] = [
    {"all_contacts_of_the_notified_object": {"state": "enabled"}},
    {"all_users": {"state": "enabled"}},
    {"all_users_with_an_email_address": {"state": "enabled"}},
    {"the_following_users": {"state": "enabled", "value": ["user1", "user2", "user3"]}},
    {"members_of_contact_groups": {"state": "enabled", "value": ["cg1", "cg2"]}},
    {
        "explicit_email_addresses": {
            "state": "enabled",
            "value": ["bob@tribe.com", "jess@tribe.com", "sofia@tribe.com"],
        }
    },
    {
        "restrict_by_custom_macros": {
            "state": "enabled",
            "value": [
                {"macro_name": "macro1", "match_regex": "^abc"},
                {"macro_name": "macro2", "match_regex": "^abc"},
            ],
        }
    },
    {"restrict_by_contact_groups": {"state": "enabled", "value": ["cg3"]}},
]


@managedtest
@pytest.mark.parametrize("testdata", contact_selection_testdata)
def test_create_and_update_rule_with_contact_selection_data(
    clients: ClientRegistry,
    testdata: APIContactSelection,
) -> None:
    clients.ContactGroup.bulk_create(
        groups=(
            {"name": "cg1", "alias": "cg1", "customer": "provider"},
            {"name": "cg2", "alias": "cg2", "customer": "provider"},
            {"name": "cg3", "alias": "cg3", "customer": "provider"},
        )
    )

    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)
    config["contact_selection"].update(testdata)
    r2 = clients.RuleNotification.edit(
        rule_id=r1.json["id"],
        rule_config=config,
    )
    assert r2.json["extensions"] == {"rule_config": config}


bulking_method_test_data: list[NotificationBulkingAPIAttrs] = [
    {
        "when_to_bulk": "always",
        "params": {
            "time_horizon": 1212,
            "subject_for_bulk_notifications": {"state": "enabled", "value": "always_subject"},
            "max_bulk_size": 111,
            "notification_bulks_based_on": ["folder", "sl", "ec_comment", "state"],
            "notification_bulks_based_on_custom_macros": ["macro1", "macro2"],
        },
    },
    {
        "when_to_bulk": "timeperiod",
        "params": {
            "time_period": "24X7",
            "subject_for_bulk_notifications": {"state": "enabled", "value": "time_period_subject"},
            "max_bulk_size": 222,
            "notification_bulks_based_on": ["host", "service", "check_type", "ec_contact"],
            "notification_bulks_based_on_custom_macros": ["macro3", "macro4"],
            "bulk_outside_timeperiod": {"state": "disabled"},
        },
    },
    {
        "when_to_bulk": "timeperiod",
        "params": {
            "time_period": "24X7",
            "subject_for_bulk_notifications": {"state": "enabled", "value": "time_period_subject"},
            "max_bulk_size": 333,
            "notification_bulks_based_on": ["host", "service", "check_type", "ec_contact"],
            "bulk_outside_timeperiod": {
                "state": "enabled",
                "value": {
                    "subject_for_bulk_notifications": {
                        "state": "enabled",
                        "value": "time_period_subject",
                    },
                    "max_bulk_size": 444,
                    "notification_bulks_based_on": ["check_type"],
                    "notification_bulks_based_on_custom_macros": ["macro5", "macro6"],
                    "time_horizon": 3434,
                },
            },
        },
    },
]


@pytest.mark.parametrize("testdata", bulking_method_test_data)
def test_create_and_update_rule_with_bulking_method_data(
    clients: ClientRegistry,
    testdata: NotificationBulkingAPIAttrs,
) -> None:
    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)

    notification_bulking: NotificationBulkingAPIValueType = {"state": "enabled", "value": testdata}
    config["notification_method"]["notification_bulking"] = notification_bulking
    r2 = clients.RuleNotification.edit(
        rule_id=r1.json["id"],
        rule_config=config,
    )
    assert r2.json["extensions"] == {"rule_config": config}


plugin_test_data: list[PluginType] = [
    {
        "plugin_name": "cisco_webex_teams",
        "webhook_url": {
            "option": "explicit",
            "url": "http://abc.com",
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "automatic", "schema": "http"},
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
    },
    {
        "plugin_name": "cisco_webex_teams",
        "webhook_url": {
            "option": "explicit",
            "url": "http://abc.com",
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "automatic", "schema": "http"},
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "global", "global_proxy_id": "some_proxy_id"},
        },
    },
    {
        "plugin_name": "cisco_webex_teams",
        "webhook_url": {
            "option": "store",
            "store_id": "some_store_id",
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "automatic", "schema": "http"},
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
    },
    {
        "plugin_name": "mkeventd",
        "syslog_facility_to_use": {
            "state": "enabled",
            "value": "user",
        },
        "ip_address_of_remote_event_console": {
            "state": "enabled",
            "value": "123.12.14.1",
        },
    },
    {
        "plugin_name": "asciimail",
        "from_details": {
            "state": "enabled",
            "value": {"address": "abc@tribe.com", "display_name": "name_example"},
        },
        "reply_to": {
            "state": "enabled",
            "value": {"address": "def@tribe.com", "display_name": "name_example"},
        },
        "subject_for_host_notifications": {
            "state": "enabled",
            "value": "Check_MK: $HOSTNAME$ - $EVENT_TXT$",
        },
        "subject_for_service_notifications": {
            "state": "enabled",
            "value": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
        },
        "sort_order_for_bulk_notifications": {
            "state": "enabled",
            "value": "newest_first",
        },
        "send_separate_notification_to_every_recipient": {
            "state": "enabled",
        },
        "body_head_for_both_host_and_service_notifications": {
            "state": "enabled",
            "value": "Host:     $HOSTNAME$\nAlias:    $HOSTALIAS$\nAddress:  $HOSTADDRESS$\n",
        },
        "body_tail_for_host_notifications": {
            "state": "enabled",
            "value": "Event:    $EVENT_TXT$\nOutput:   $HOSTOUTPUT$\nPerfdata: $HOSTPERFDATA$\n$LONGHOSTOUTPUT$\n",
        },
        "body_tail_for_service_notifications": {
            "state": "enabled",
            "value": "Service:  $SERVICEDESC$\nEvent:    $EVENT_TXT$\nOutput:   $SERVICEOUTPUT$\nPerfdata: $SERVICEPERFDATA$\n$LONGSERVICEOUTPUT$\n",
        },
    },
    {
        "plugin_name": "mail",
        "from_details": {
            "state": "enabled",
            "value": {"address": "asdfasfdsa@ladjf.com", "display_name": "name_example"},
        },
        "reply_to": {
            "state": "enabled",
            "value": {"address": "afasdfas@tribe.com", "display_name": "name_example"},
        },
        "subject_for_host_notifications": {
            "state": "enabled",
            "value": "Check_MK: $HOSTNAME$ - $EVENT_TXT$",
        },
        "subject_for_service_notifications": {
            "state": "enabled",
            "value": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
        },
        "info_to_be_displayed_in_the_email_body": {
            "state": "enabled",
            "value": [
                "address",
                "abstime",
                "longoutput",
                "ack_author",
                "ack_comment",
                "notification_author",
                "perfdata",
                "graph",
            ],
        },
        "insert_html_section_between_body_and_table": {
            "state": "enabled",
            "value": "<HTMLTAG>CONTENT</HTMLTAG>\n",
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "automatic", "schema": "https"},
        },
        "sort_order_for_bulk_notifications": {"state": "enabled", "value": "newest_first"},
        "send_separate_notification_to_every_recipient": {"state": "enabled"},
        "enable_sync_smtp": {
            "state": "enabled",
            "value": {
                "auth": {
                    "state": "enabled",
                    "value": {"method": "plaintext", "password": "gav1234", "user": "gav"},
                },
                "encryption": "ssl_tls",
                "port": 25,
                "smarthosts": ["abc", "def"],
            },
        },
        "display_graphs_among_each_other": {
            "state": "enabled",
        },
        "graphs_per_notification": {
            "state": "enabled",
            "value": 5,
        },
        "bulk_notifications_with_graphs": {
            "state": "enabled",
            "value": 5,
        },
    },
    {
        "plugin_name": "ilert",
        "api_key": {
            "option": "explicit",
            "key": "abcdefghijklmnopqrstuvwxyz",
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "notification_priority": "HIGH",
        "custom_summary_for_host_alerts": "$NOTIFICATIONTYPE$ Host Alert: $HOSTNAME$ is $HOSTSTATE$ - $HOSTOUTPUT$",
        "custom_summary_for_service_alerts": "$NOTIFICATIONTYPE$ Service Alert: $HOSTALIAS$/$SERVICEDESC$ is $SERVICESTATE$ - $SERVICEOUTPUT$",
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "manual", "url": "http://klapp0084/heute/check_mk"},
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
    },
    {
        "plugin_name": "ilert",
        "api_key": {
            "option": "store",
            "store_id": "some_store_id",
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "notification_priority": "HIGH",
        "custom_summary_for_host_alerts": "$NOTIFICATIONTYPE$ Host Alert: $HOSTNAME$ is $HOSTSTATE$ - $HOSTOUTPUT$",
        "custom_summary_for_service_alerts": "$NOTIFICATIONTYPE$ Service Alert: $HOSTALIAS$/$SERVICEDESC$ is $SERVICESTATE$ - $SERVICEOUTPUT$",
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "manual", "url": "http://klapp0084/heute/check_mk"},
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
    },
    {
        "plugin_name": "jira_issues",
        "jira_url": "https://test_jira_url.com/here",
        "disable_ssl_cert_verification": {"state": "disabled"},
        "auth": {
            "option": "explicit_password",
            "username": "user_username",
            "password": "user_password",
        },
        "project_id": "1234",
        "issue_type_id": "2345",
        "host_custom_id": "3456",
        "service_custom_id": "",
        "monitoring_url": "http://test_monitoring_url.com/here",
        "site_custom_id": {
            "state": "disabled",
        },
        "priority_id": {
            "state": "enabled",
            "value": "123456",
        },
        "host_summary": {
            "state": "enabled",
            "value": "Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$",
        },
        "service_summary": {
            "state": "enabled",
            "value": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$",
        },
        "label": {
            "state": "enabled",
            "value": "label_key:label_value",
        },
        "graphs_per_notification": {
            "state": "enabled",
            "value": 3,
        },
        "resolution_id": {
            "state": "enabled",
            "value": "abc",
        },
        "optional_timeout": {
            "state": "enabled",
            "value": "11",
        },
    },
    {
        "plugin_name": "opsgenie_issues",
        "api_key": {
            "option": "explicit",
            "key": "abcdefghijklmnopqrstuvwxyz",
        },
        "domain": {
            "state": "enabled",
            "value": "https://domain_test",
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {"state": "enabled", "value": {"option": "no_proxy"}},
        "owner": {
            "state": "enabled",
            "value": "Gav",
        },
        "source": {
            "state": "enabled",
            "value": "abc",
        },
        "priority": {
            "state": "enabled",
            "value": "moderate",
        },
        "note_while_creating": {
            "state": "enabled",
            "value": "Alert created by Check_MK",
        },
        "note_while_closing": {
            "state": "enabled",
            "value": "Alert closed by Check_MK",
        },
        "desc_for_host_alerts": {
            "state": "enabled",
            "value": "Host: $HOSTNAME$\nEvent:    $EVENT_TXT$\nOutput:   $HOSTOUTPUT$\nPerfdata: $HOSTPERFDATA$\n$LONGHOSTOUTPUT$\n",
        },
        "desc_for_service_alerts": {
            "state": "enabled",
            "value": "Host: $HOSTNAME$\nService:  $SERVICEDESC$\nEvent:    $EVENT_TXT$\nOutput:   $SERVICEOUTPUT$\nPerfdata: $SERVICEPERFDATA$\n$LONGSERVICEOUTPUT$\n",
        },
        "message_for_host_alerts": {
            "state": "enabled",
            "value": "Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$",
        },
        "message_for_service_alerts": {
            "state": "enabled",
            "value": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$",
        },
        "responsible_teams": {
            "state": "enabled",
            "value": ["test_team_1", "test_team_2"],
        },
        "actions": {
            "state": "enabled",
            "value": ["action_1", "action_2", "action_3", "action_4"],
        },
        "tags": {
            "state": "enabled",
            "value": ["tag_test_1", "tag_test_2", "tag_test_3"],
        },
        "entity": {
            "state": "enabled",
            "value": "entity_test",
        },
        "extra_properties": {"state": "disabled"},
    },
    {
        "plugin_name": "opsgenie_issues",
        "api_key": {
            "option": "store",
            "store_id": "some_store_id",
        },
        "domain": {
            "state": "enabled",
            "value": "https://domain_test",
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "no_proxy"},
        },
        "owner": {
            "state": "enabled",
            "value": "Gav",
        },
        "source": {
            "state": "enabled",
            "value": "abc",
        },
        "priority": {
            "state": "enabled",
            "value": "critical",
        },
        "note_while_creating": {
            "state": "enabled",
            "value": "Alert created by Check_MK",
        },
        "note_while_closing": {
            "state": "enabled",
            "value": "Alert closed by Check_MK",
        },
        "desc_for_host_alerts": {
            "state": "enabled",
            "value": "Host: $HOSTNAME$\nEvent:    $EVENT_TXT$\nOutput:   $HOSTOUTPUT$\nPerfdata: $HOSTPERFDATA$\n$LONGHOSTOUTPUT$\n",
        },
        "desc_for_service_alerts": {
            "state": "enabled",
            "value": "Host: $HOSTNAME$\nService:  $SERVICEDESC$\nEvent:    $EVENT_TXT$\nOutput:   $SERVICEOUTPUT$\nPerfdata: $SERVICEPERFDATA$\n$LONGSERVICEOUTPUT$\n",
        },
        "message_for_host_alerts": {
            "state": "enabled",
            "value": "Check_MK: $HOSTNAME$ - $HOSTSHORTSTATE$",
        },
        "message_for_service_alerts": {
            "state": "enabled",
            "value": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$",
        },
        "responsible_teams": {
            "state": "enabled",
            "value": ["test_team_1", "test_team_2"],
        },
        "actions": {
            "state": "enabled",
            "value": ["action_1", "action_2", "action_3", "action_4"],
        },
        "tags": {
            "state": "enabled",
            "value": ["tag_test_1", "tag_test2", "tag_test3"],
        },
        "entity": {
            "state": "enabled",
            "value": "entity_test",
        },
        "extra_properties": {
            "state": "enabled",
            "value": [
                "omd_site",
                "hosttags",
                "address",
                "abstime",
                "reltime",
                "longoutput",
                "ack_author",
                "ack_comment",
                "notification_author",
                "notification_comment",
                "perfdata",
                "notesurl",
                "context",
            ],
        },
    },
    {
        "plugin_name": "pagerduty",
        "integration_key": {
            "option": "explicit",
            "key": "abcdefghijklmnopqrstuvqxyz",
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "url", "url": "http://explicit_proxy_settings"},
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "manual", "url": "http://klapp0084/heute/check_mk/"},
        },
    },
    {
        "plugin_name": "pagerduty",
        "integration_key": {
            "option": "store",
            "store_id": "some_store_id",
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "url", "url": "http://explicit_proxy_settings"},
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "manual", "url": "http://klapp0084/heute/check_mk/"},
        },
    },
    {
        "plugin_name": "pushover",
        "api_key": "azGDORePK8gMaC0QOYAMyEEuzJnyUi",
        "user_group_key": "azGDORePK8gMaC0QOYAMyEEuzJnyUi",
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "manual", "url": "http://klapp0084/heute/check_mk/"},
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
        "priority": {
            "state": "enabled",
            "value": {"level": "high"},
        },
        "sound": {
            "state": "enabled",
            "value": "cosmic",
        },
    },
    {
        "plugin_name": "servicenow",
        "servicenow_url": "https://service_now_url_test",
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "url", "url": "http://http_proxy_test_url/here"},
        },
        "auth": {
            "option": "explicit_password",
            "username": "user_username",
            "password": "user_password",
        },
        "use_site_id_prefix": {
            "state": "enabled",
            "value": "use_site_id",
        },
        "optional_timeout": {
            "state": "enabled",
            "value": "13",
        },
        "management_type": {
            "option": "incident",
            "params": {
                "caller": "",
                "host_description": {
                    "state": "disabled",
                },
                "host_short_description": {
                    "state": "disabled",
                },
                "impact": {
                    "state": "disabled",
                },
                "service_description": {
                    "state": "disabled",
                },
                "service_short_description": {
                    "state": "disabled",
                },
                "state_acknowledgement": {
                    "state": "disabled",
                },
                "state_downtime": {
                    "state": "disabled",
                },
                "state_recovery": {
                    "state": "disabled",
                },
                "urgency": {
                    "state": "disabled",
                },
            },
        },
    },
    {
        "plugin_name": "servicenow",
        "servicenow_url": "https://service_now_url_test",
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "url", "url": "http://http_proxy_test_url/here"},
        },
        "auth": {
            "option": "explicit_token",
            "token": "explicit_service_now_token",
        },
        "use_site_id_prefix": {
            "state": "enabled",
            "value": "use_site_id",
        },
        "optional_timeout": {
            "state": "enabled",
            "value": "13",
        },
        "management_type": {
            "option": "incident",
            "params": {
                "caller": "",
                "host_description": {
                    "state": "disabled",
                },
                "host_short_description": {
                    "state": "disabled",
                },
                "impact": {
                    "state": "disabled",
                },
                "service_description": {
                    "state": "disabled",
                },
                "service_short_description": {
                    "state": "disabled",
                },
                "state_acknowledgement": {
                    "state": "disabled",
                },
                "state_downtime": {
                    "state": "disabled",
                },
                "state_recovery": {
                    "state": "disabled",
                },
                "urgency": {
                    "state": "disabled",
                },
            },
        },
    },
    {
        "plugin_name": "signl4",
        "team_secret": {
            "option": "explicit",
            "secret": "explicit_team_secret",
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "manual", "url": "http://klapp0084/heute/check_mk/"},
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
    },
    {
        "plugin_name": "signl4",
        "team_secret": {
            "option": "store",
            "store_id": "some_store_id",
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "manual", "url": "http://klapp0084/heute/check_mk/"},
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
    },
    {
        "plugin_name": "slack",
        "webhook_url": {
            "option": "explicit",
            "url": "https://hooks.slack.com/services/sorry/not/real",
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "automatic", "schema": "https"},
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
    },
    {
        "plugin_name": "slack",
        "webhook_url": {
            "option": "store",
            "store_id": "some_store_id",
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "automatic", "schema": "https"},
        },
        "disable_ssl_cert_verification": {
            "state": "enabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
    },
    {
        "plugin_name": "slack",
        "webhook_url": {
            "option": "explicit",
            "url": "http://my-mattermost.local/hook/not-real",
        },
        "url_prefix_for_links_to_checkmk": {
            "state": "disabled",
        },
        "disable_ssl_cert_verification": {
            "state": "disabled",
        },
        "http_proxy": {
            "state": "disabled",
        },
    },
    {
        "plugin_name": "sms_api",
        "modem_type": "trb140",
        "modem_url": "https://teltonika.com",
        "disable_ssl_cert_verification": {
            "state": "disabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
        "username": "test_username",
        "user_password": {
            "option": "explicit",
            "password": "password_1",
        },
        "timeout": "10",
    },
    {
        "plugin_name": "sms_api",
        "modem_type": "trb140",
        "modem_url": "https://teltonika.com",
        "disable_ssl_cert_verification": {
            "state": "disabled",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
        "username": "test_username",
        "user_password": {
            "option": "store",
            "store_id": "some_store_id",
        },
        "timeout": "10",
    },
    {
        "plugin_name": "sms",
        "params": ["param_1", "param_2", "param_3"],
    },
    {
        "plugin_name": "spectrum",
        "base_oid": "1.3.6.1.4.1.1234",
        "destination_ip": "127.0.0.1",
        "snmp_community": "abcdefghijklmnopqrstuvwxyz",
    },
    {
        "plugin_name": "victorops",
        "disable_ssl_cert_verification": {"state": "enabled"},
        "http_proxy": {"state": "enabled", "value": {"option": "no_proxy"}},
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "automatic", "schema": "http"},
        },
        "splunk_on_call_rest_endpoint": {
            "option": "explicit",
            "url": "https://alert.victorops.com/integrations/splunk_on_call_endpoint",
        },
    },
    {
        "plugin_name": "victorops",
        "disable_ssl_cert_verification": {"state": "enabled"},
        "http_proxy": {"state": "enabled", "value": {"option": "no_proxy"}},
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "automatic", "schema": "http"},
        },
        "splunk_on_call_rest_endpoint": {
            "option": "store",
            "store_id": "some_store_id",
        },
    },
    {
        "plugin_name": "msteams",
        "affected_host_groups": {"state": "enabled"},
        "host_details": {
            "state": "enabled",
            "value": "__Host__: $HOSTNAME$\n"
            "\n"
            "__Event__:    $EVENT_TXT$\n"
            "\n"
            "__Output__:   $HOSTOUTPUT$\n"
            "\n"
            "__Perfdata__: $HOSTPERFDATA$\n"
            "\n"
            "<br>\n"
            "$LONGHOSTOUTPUT$\n",
        },
        "service_details": {
            "state": "enabled",
            "value": "__Host__: $HOSTNAME$\n"
            "\n"
            "__Service__:  $SERVICEDESC$\n"
            "\n"
            "__Event__:    $EVENT_TXT$\n"
            "\n"
            "__Output__:   $SERVICEOUTPUT$\n"
            "\n"
            "__Perfdata__: $SERVICEPERFDATA$\n"
            "\n"
            "<br>\n"
            "$LONGSERVICEOUTPUT$\n",
        },
        "host_summary": {"state": "enabled", "value": "Checkmk: $HOSTNAME$ - $EVENT_TXT$"},
        "service_summary": {
            "state": "enabled",
            "value": "Checkmk: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
        },
        "host_title": {"state": "enabled", "value": "Checkmk: $HOSTNAME$ - $HOSTSHORTSTATE$"},
        "service_title": {
            "state": "enabled",
            "value": "Checkmk: $HOSTNAME$/$SERVICEDESC$ $SERVICESHORTSTATE$",
        },
        "http_proxy": {"state": "enabled", "value": {"option": "no_proxy"}},
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "automatic", "schema": "http"},
        },
        "webhook_url": {
            "option": "explicit",
            "url": "http://abc.com",
        },
    },
    {
        "plugin_name": "pushover",
        "api_key": "azGDORePK8gMaC0QOYAMyEEuzJnyUi",
        "user_group_key": "azGDORePK8gMaC0QOYAMyEEuzJnyUi",
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "manual", "url": "http://klapp0084/heute/check_mk/"},
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
        "priority": {
            "state": "enabled",
            "value": {
                "level": "emergency",
                "retry": 60,
                "expire": 3600,
                "receipt": "abcdefghijklmnopqrst0123456789",
            },
        },
        "sound": {
            "state": "enabled",
            "value": "cosmic",
        },
    },
]


def test_update_notification_method_cancel_previous(
    clients: ClientRegistry,
) -> None:
    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)

    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.CANCEL,
        "plugin_params": {"plugin_name": "mail"},
    }
    r2 = clients.RuleNotification.edit(
        rule_id=r1.json["id"],
        rule_config=config,
    )
    assert r2.json["extensions"] == {"rule_config": config}


@managedtest
@pytest.mark.parametrize("plugin_data", plugin_test_data)
@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_update_notification_method(
    clients: ClientRegistry,
    plugin_data: PluginType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup_site_data(clients)

    monkeypatch.setattr(
        "cmk.gui.fields.custom_fields._global_proxy_choices",
        lambda: [("some_proxy_id")],
    )

    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)
    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_PARAMS,
        "plugin_params": plugin_data,
    }
    if config["notification_method"]["notify_plugin"]["plugin_params"]["plugin_name"] not in (
        "mail",
        "asciimail",
    ):
        del config["notification_method"]["notification_bulking"]

    r2 = clients.RuleNotification.edit(
        rule_id=r1.json["id"],
        rule_config=config,
    )
    assert r2.json["extensions"] == {"rule_config": config}


invalid_pushover_keys = [
    "TwentyNineCharacters123456789",
    "FortyOneCharacters12345678901234567899012",
    "Between30&40But_Not_all_Letters/Numbers",
]


@managedtest
@pytest.mark.parametrize("invalid_key", invalid_pushover_keys)
def test_pushover_key_regex(
    clients: ClientRegistry,
    invalid_key: str,
) -> None:
    push_over_plugin: API_PushOverData = {
        "plugin_name": "pushover",
        "api_key": invalid_key,
        "user_group_key": invalid_key,
        "url_prefix_for_links_to_checkmk": {
            "state": "enabled",
            "value": {"option": "automatic", "schema": "http"},
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
        "priority": {
            "state": "enabled",
            "value": {"level": "low"},
        },
        "sound": {
            "state": "enabled",
            "value": "cosmic",
        },
    }

    config = notification_rule_request_example()
    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_PARAMS,
        "plugin_params": push_over_plugin,
    }

    r = clients.RuleNotification.create(rule_config=config, expect_ok=False)
    r.assert_status_code(400)
    assert r.json["fields"]["rule_config"]["notification_method"]["notify_plugin"][
        "plugin_params"
    ] == {
        "api_key": [f"'{invalid_key}' does not match pattern '^[a-zA-Z0-9]{{30,40}}$'."],
        "user_group_key": [f"'{invalid_key}' does not match pattern '^[a-zA-Z0-9]{{30,40}}$'."],
    }


service_now: API_ServiceNowData = {
    "plugin_name": "servicenow",
    "servicenow_url": "https://service_now_url_test",
    "http_proxy": {
        "state": "enabled",
        "value": {"option": "url", "url": "http://http_proxy_test_url/here"},
    },
    "auth": {
        "option": "explicit_password",
        "username": "user_username",
        "password": "user_password",
    },
    "use_site_id_prefix": {
        "state": "enabled",
        "value": "use_site_id",
    },
    "optional_timeout": {
        "state": "enabled",
        "value": "13",
    },
    "management_type": {},
}

service_now_incident: MgmtTypeIncidentAPI = {
    "option": "incident",
    "params": {
        "caller": "",
        "host_description": {
            "state": "disabled",
        },
        "host_short_description": {
            "state": "disabled",
        },
        "impact": {
            "state": "disabled",
        },
        "service_description": {
            "state": "disabled",
        },
        "service_short_description": {
            "state": "disabled",
        },
        "state_acknowledgement": {"state": "enabled", "value": {"start_integer": 4}},
        "state_downtime": {"state": "enabled", "value": {"start_integer": 1, "end_integer": 2}},
        "state_recovery": {"state": "enabled", "value": {"start_integer": 3}},
        "urgency": {
            "state": "disabled",
        },
    },
}


def incident_states() -> list[MgmtTypeIncidentParamsAPI]:
    d: list[MgmtTypeIncidentParamsAPI] = []
    for n, predefined_state in enumerate(list(get_args(IncidentStateStr))):
        d.append(
            MgmtTypeIncidentParamsAPI(
                state_acknowledgement=AckStateAPI(
                    state="enabled",
                    value={"start_predefined": predefined_state},
                ),
            ),
        )
        d.append(
            MgmtTypeIncidentParamsAPI(
                state_acknowledgement=AckStateAPI(
                    state="enabled",
                    value={"start_integer": n},
                ),
            ),
        )
        d.append(
            MgmtTypeIncidentParamsAPI(
                state_downtime=DowntimeStateAPI(
                    state="enabled",
                    value={
                        "start_predefined": predefined_state,
                        "end_predefined": predefined_state,
                    },
                ),
            ),
        )
        d.append(
            MgmtTypeIncidentParamsAPI(
                state_downtime=DowntimeStateAPI(
                    state="enabled",
                    value={"start_integer": n, "end_integer": n},
                ),
            ),
        )
        d.append(
            MgmtTypeIncidentParamsAPI(
                state_recovery=RecoveryStateIncidentAPI(
                    state="enabled",
                    value={"start_predefined": predefined_state},
                ),
            ),
        )
        d.append(
            MgmtTypeIncidentParamsAPI(
                state_recovery=RecoveryStateIncidentAPI(
                    state="enabled",
                    value={"start_integer": n},
                ),
            ),
        )
    return d


@pytest.mark.parametrize("mgmt_type_data", incident_states())
def test_service_now_management_incident_types_200(
    clients: ClientRegistry,
    mgmt_type_data: MgmtTypeIncidentParamsAPI,
) -> None:
    service_now["management_type"] = service_now_incident
    service_now["management_type"]["params"].update(mgmt_type_data)  # type: ignore[typeddict-item]
    config = notification_rule_request_example()
    del config["notification_method"]["notification_bulking"]
    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_PARAMS,
        "plugin_params": service_now,
    }
    r1 = clients.RuleNotification.create(rule_config=config)
    assert r1.json["extensions"] == {"rule_config": config}


service_now_case: MgmtTypeCaseAPI = {
    "option": "case",
    "params": {
        "host_description": {
            "state": "disabled",
        },
        "host_short_description": {
            "state": "disabled",
        },
        "service_description": {
            "state": "disabled",
        },
        "service_short_description": {
            "state": "disabled",
        },
        "state_recovery": {"state": "enabled", "value": {"start_integer": 3}},
        "priority": {
            "state": "disabled",
        },
    },
}


def case_states() -> list[MgmtTypeCaseParamsAPI]:
    d: list[MgmtTypeCaseParamsAPI] = []
    for n, predefined_state in enumerate(list(get_args(CaseStateStr))):
        d.append(
            MgmtTypeCaseParamsAPI(
                state_recovery=RecoveryStateCaseAPI(
                    state="enabled",
                    value={"start_predefined": predefined_state},
                ),
            ),
        )
        d.append(
            MgmtTypeCaseParamsAPI(
                state_recovery=RecoveryStateCaseAPI(
                    state="enabled",
                    value={"start_integer": n},
                ),
            ),
        )
    return d


@pytest.mark.parametrize("mgmt_type_data", case_states())
def test_service_now_management_case_types_200(
    clients: ClientRegistry,
    mgmt_type_data: MgmtTypeCaseParamsAPI,
) -> None:
    service_now["management_type"] = service_now_case
    service_now["management_type"]["params"].update(mgmt_type_data)  # type: ignore[typeddict-item]
    config = notification_rule_request_example()
    del config["notification_method"]["notification_bulking"]
    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_PARAMS,
        "plugin_params": service_now,
    }
    r1 = clients.RuleNotification.create(rule_config=config)
    assert r1.json["extensions"] == {"rule_config": config}


def config_with_bulk(plugin: PluginType) -> APINotificationRule:
    config = notification_rule_request_example()
    notification_bulking: NotificationBulkingAPIValueType = {
        "state": "enabled",
        "value": bulking_method_test_data[0],
    }
    config["notification_method"]["notification_bulking"] = notification_bulking

    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_PARAMS,
        "plugin_params": plugin,
    }
    return config


def plugin_with_bulking(
    bulking: Literal["allowed", "not_allowed"],
) -> Iterator[APINotificationRule]:
    notification_scripts = load_notification_scripts()
    plugins: list[str] = []
    for plugin in plugin_test_data:
        if plugin["plugin_name"] not in plugins:
            if bulking == "allowed":
                if notification_scripts[plugin["plugin_name"]]["bulk"]:
                    yield config_with_bulk(plugin)
                    plugins.append(plugin["plugin_name"])
                continue

            if not notification_scripts[plugin["plugin_name"]]["bulk"]:
                yield config_with_bulk(plugin)
                plugins.append(plugin["plugin_name"])


@managedtest
@pytest.mark.parametrize("config", plugin_with_bulking(bulking="allowed"))
@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_bulking_200(
    clients: ClientRegistry,
    config: APINotificationRule,
) -> None:
    setup_site_data(clients)

    clients.RuleNotification.create(rule_config=config)


@managedtest
@pytest.mark.parametrize("config", plugin_with_bulking(bulking="not_allowed"))
@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_bulking_400(
    clients: ClientRegistry,
    config: APINotificationRule,
) -> None:
    setup_site_data(clients)

    resp = clients.RuleNotification.create(
        rule_config=config,
        expect_ok=False,
    )
    resp.assert_status_code(400)

    plugin_name = config["notification_method"]["notify_plugin"]["plugin_params"]["plugin_name"]
    assert resp.json["title"] == "Bulking not allowed"
    assert resp.json["detail"] == "The notification script %s does not allow bulking." % plugin_name


def test_create_notification_with_invalid_custom_plugin(
    clients: ClientRegistry,
) -> None:
    config = notification_rule_request_example()
    plugin_params: APIPluginDict = {
        "plugin_name": CustomPluginName("my_cool_plugin"),
    }
    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_CUSTOM_PARAMS,
        "plugin_params": plugin_params,
    }

    resp = clients.RuleNotification.create(rule_config=config, expect_ok=False)
    resp.assert_status_code(400)

    assert resp.json["fields"]["rule_config"]["notification_method"]["notify_plugin"] == {
        "plugin_params": {"_schema": ["my_cool_plugin does not exist"]}
    }


invalid_list_configs = [
    (
        {
            "params": ["param1", "param2", "param3"],
        },
        {
            "plugin_name": ["Missing data for required field."],
        },
    ),
    (
        {
            "plugin_name": "my_cool_plugin",
        },
        {
            "params": ["Missing data for required field."],
        },
    ),
    (
        {
            "plugin_name": "my_cool_plugin",
            "params": ["param1", "param2", "param3"],
            "extra_field": "extra",
        },
        {
            "extra_field": ["Unknown field."],
        },
    ),
]


@managedtest
@pytest.mark.parametrize("plugin_params, expected_error", invalid_list_configs)
def test_create_notification_custom_plugin_invalid_list_config(
    clients: ClientRegistry,
    plugin_params: APIPluginList,
    expected_error: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.endpoints.notification_rules.request_schemas.user_script_choices",
        lambda what: [("my_cool_plugin", "info")],
    )

    config = notification_rule_request_example()
    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_CUSTOM_PARAMS,
        "plugin_params": plugin_params,
    }

    resp = clients.RuleNotification.create(rule_config=config, expect_ok=False)
    resp.assert_status_code(400)

    assert (
        resp.json["fields"]["rule_config"]["notification_method"]["notify_plugin"]["plugin_params"]
        == expected_error
    )


def test_create_notification_custom_plugin_valid_list_config(
    clients: ClientRegistry,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.endpoints.notification_rules.request_schemas.user_script_choices",
        lambda what: [("my_cool_plugin", "info")],
    )

    plugin_params: APIPluginList = {
        "plugin_name": CustomPluginName("my_cool_plugin"),
        "params": ["param1", "param2", "param3"],
    }

    config = notification_rule_request_example()
    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_CUSTOM_PARAMS,
        "plugin_params": plugin_params,
    }

    resp = clients.RuleNotification.create(rule_config=config)
    clients.RuleNotification.get(rule_id=resp.json["id"])


@pytest.fixture
def register_custom_plugin() -> Generator:
    register_notification_parameters(
        "my_cool_plugin",
        Dictionary(
            optional_keys=["originator", "list_of_strings", "test_dict", "test_int", "test_bool"],
            elements=[
                (
                    "user_key",
                    TextInput(
                        title="User Key",
                        size=40,
                        allow_empty=False,
                    ),
                ),
                (
                    "api_password",
                    TextInput(
                        title="API Password",
                        size=40,
                        allow_empty=False,
                    ),
                ),
                (
                    "originator",
                    TextInput(
                        title="Originator",
                        size=40,
                    ),
                ),
                ("list_of_strings", ListOfStrings(TextInput())),
                (
                    "test_dict",
                    Dictionary(
                        elements=[
                            (
                                "key1",
                                TextInput(),
                            ),
                            (
                                "key2",
                                TextInput(),
                            ),
                        ],
                    ),
                ),
                (
                    "test_int",
                    Integer(),
                ),
                ("test_bool", Checkbox()),
            ],
        ),
    )
    yield
    notification_parameter_registry.unregister("my_cool_plugin")


valid_dict_configs = [
    {
        "plugin_name": "my_cool_plugin",
        "user_key": "some_user_key",
        "api_password": "some_api_password",
    },
    {
        "plugin_name": "my_cool_plugin",
        "user_key": "some_user_key",
        "api_password": "some_api_password",
        "originator": "me",
    },
    {
        "plugin_name": "my_cool_plugin",
        "user_key": "some_user_key",
        "api_password": "some_api_password",
        "originator": "me",
        "list_of_strings": ["str1", "str2", "str3", "str4"],
    },
    {
        "plugin_name": "my_cool_plugin",
        "user_key": "some_user_key",
        "api_password": "some_api_password",
        "originator": "me",
        "list_of_strings": ["str1", "str2", "str3", "str4"],
        "test_dict": {"key1": "sometext", "key2": "somemoretext"},
    },
    {
        "plugin_name": "my_cool_plugin",
        "user_key": "some_user_key",
        "api_password": "some_api_password",
        "originator": "me",
        "list_of_strings": ["str1", "str2", "str3", "str4"],
        "test_dict": {"key1": "sometext", "key2": "somemoretext"},
        "test_int": 3,
    },
    {
        "plugin_name": "my_cool_plugin",
        "user_key": "some_user_key",
        "api_password": "some_api_password",
        "originator": "me",
        "list_of_strings": ["str1", "str2", "str3", "str4"],
        "test_dict": {"key1": "sometext", "key2": "somemoretext"},
        "test_bool": True,
    },
]


@managedtest
@pytest.mark.parametrize("plugin_params", valid_dict_configs)
@pytest.mark.usefixtures("register_custom_plugin")
def test_create_notification_custom_plugin_valid_dict_config(
    clients: ClientRegistry,
    plugin_params: APIPluginDict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.endpoints.notification_rules.request_schemas.user_script_choices",
        lambda what: [("my_cool_plugin", "info")],
    )

    config = notification_rule_request_example()
    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_CUSTOM_PARAMS,
        "plugin_params": plugin_params,
    }

    resp = clients.RuleNotification.create(rule_config=config)
    clients.RuleNotification.get(rule_id=resp.json["id"])


invalid_dict_configs = [
    (
        {
            "user_key": "some_user_key",
            "api_password": "some_api_password",
        },
        {"plugin_name": ["Missing data for required field."]},
    ),
    (
        {
            "plugin_name": "my_cool_plugin",
            "api_password": "some_api_password",
        },
        {"plugin_params": ["A required (sub-)field is missing."]},
    ),
    (
        {
            "plugin_name": "my_cool_plugin",
            "non_valid_key": "some_invalid_key",
            "user_key": "some_user_key",
            "api_password": "some_api_password",
        },
        {
            "plugin_params": [
                "Undefined key 'non_valid_key' in the dictionary. Allowed are user_key, api_password, originator, list_of_strings, test_dict, test_int, test_bool."
            ]
        },
    ),
    (
        {
            "plugin_name": "my_cool_plugin",
            "user_key": "some_user_key",
            "api_password": {"some_api_password": "pass", "non_valid_key": "some_invalid_key"},
        },
        {"api_password": ["The value must be of type str, but it has type dict"]},
    ),
]


@pytest.mark.parametrize("plugin_params, expected_error", invalid_dict_configs)
@pytest.mark.usefixtures("register_custom_plugin")
def test_create_notification_custom_plugin_invalid_dict_config(
    clients: ClientRegistry,
    plugin_params: APIPluginDict,
    expected_error: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "cmk.gui.openapi.endpoints.notification_rules.request_schemas.user_script_choices",
        lambda what: [("my_cool_plugin", "info")],
    )
    config = notification_rule_request_example()
    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_CUSTOM_PARAMS,
        "plugin_params": plugin_params,
    }

    resp = clients.RuleNotification.create(rule_config=config, expect_ok=False)
    resp.assert_status_code(400)

    assert (
        resp.json["fields"]["rule_config"]["notification_method"]["notify_plugin"]["plugin_params"]
        == expected_error
    )


def setup_host_tags_on_site(clients: ClientRegistry) -> None:
    clients.HostTagGroup.create(
        ident="criticality",
        title="Criticality",
        help_text="",
        tags=[
            {"id": "prod", "title": "Productive system"},
            {"id": "critical", "title": "Business critical"},
            {"id": "test", "title": "Test system"},
            {"id": "offline", "title": "Do not monitor this host"},
        ],
    )

    clients.HostTagGroup.create(
        ident="networking",
        title="Networking Segment",
        help_text="",
        tags=[
            {"id": "lan", "title": "Local network (low latency)"},
            {"id": "wan", "title": "WAN (high latency)"},
            {"id": "dmz", "title": "DMZ (low latency, secure access)"},
        ],
    )

    test_data: dict[str, Any] = {
        "aux_tag_id": "aux_tag_id_1",
        "title": "aux_tag_1",
        "topic": "topic_1",
        "help": "HELP",
    }
    clients.AuxTag.create(tag_data=test_data)


@pytest.mark.usefixtures("suppress_spec_generation_in_background")
def test_match_host_tags(clients: ClientRegistry) -> None:
    setup_host_tags_on_site(clients)
    config = notification_rule_request_example()
    config["conditions"]["match_host_tags"] = {
        "state": "enabled",
        "value": [
            {
                "tag_type": "aux_tag",
                "tag_id": TagID("aux_tag_id_1"),
                "operator": "is_set",
            },
            {
                "tag_type": "tag_group",
                "tag_group_id": "criticality",
                "operator": "is_not",
                "tag_id": TagID("prod"),
            },
            {
                "tag_type": "tag_group",
                "tag_group_id": "networking",
                "operator": "is_not",
                "tag_id": TagID("lan"),
            },
            {
                "tag_type": "tag_group",
                "tag_group_id": "agent",
                "operator": "is",
                "tag_id": TagID("cmk-agent"),
            },
            {
                "tag_type": "tag_group",
                "tag_group_id": "snmp_ds",
                "operator": "one_of",
                "tag_ids": [TagID("snmp-v1"), TagID("no-snmp"), TagID("snmp-v2")],
            },
            {
                "tag_type": "tag_group",
                "tag_group_id": "address_family",
                "operator": "none_of",
                "tag_ids": [TagID("ip-v4-only"), TagID("ip-v4v6")],
            },
        ],
    }

    resp = clients.RuleNotification.create(rule_config=config)
    assert resp.json["extensions"]["rule_config"] == config


auth_methods: list[
    API_ExplicitToken | API_StoreToken | API_BasicAuthExplicit | API_BasicAuthStore
] = [
    {
        "option": "explicit_password",
        "username": "a_user_name",
        "password": "_!$%@w&*@",
    },
    {
        "option": "password_store_id",
        "username": "a_user_name",
        "store_id": "some_store_id",
    },
    {
        "option": "explicit_token",
        "token": "some_token",
    },
    {
        "option": "token_store_id",
        "store_id": "some_store_id",
    },
]


@managedtest
@pytest.mark.parametrize("plugin", [plugin_test_data[8], plugin_test_data[14]])
@pytest.mark.parametrize("auth_method", auth_methods)
@pytest.mark.usefixtures("mock_password_file_regeneration")
def test_create_rules_with_basic_and_token_auth(
    clients: ClientRegistry,
    plugin: API_JiraData | API_ServiceNowData,
    auth_method: API_ExplicitToken | API_StoreToken | API_BasicAuthExplicit | API_BasicAuthStore,
) -> None:
    setup_site_data(clients)
    plugin["auth"] = auth_method
    config = notification_rule_request_example()
    del config["notification_method"]["notification_bulking"]
    config["notification_method"]["notify_plugin"] = {
        "option": PluginOptions.WITH_PARAMS,
        "plugin_params": plugin,
    }
    r1 = clients.RuleNotification.create(rule_config=config)
    assert r1.json["extensions"] == {"rule_config": config}
