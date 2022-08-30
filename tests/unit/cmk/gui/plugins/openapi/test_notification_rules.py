#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from itertools import permutations
from typing import Any, get_args, Iterator, Literal

import pytest

from tests.testlib.rest_api_client import ClientRegistry

from cmk.utils import version
from cmk.utils.type_defs.rest_api_types.notifications_rule_types import (
    API_ServiceNowData,
    APIConditions,
    APIContactSelection,
    APINotificationRule,
    APIRuleProperties,
    CASE_STATE_TYPE,
    INCIDENT_STATE_TYPE,
    MgmtTypeAPI,
    MgmtTypeParamsAPI,
    NotificationBulkingAPIAttrs,
    NotificationBulkingAPIValueType,
    PluginType,
)

from cmk.gui.plugins.openapi.endpoints.notification_rules.request_example import (
    notification_rule_request_example,
)
from cmk.gui.plugins.openapi.endpoints.site_management.common import (
    default_config_example as _default_config,
)
from cmk.gui.watolib.user_scripts import load_notification_scripts

managedtest = pytest.mark.skipif(not version.is_managed_edition(), reason="see #7213")


def cb_str_options() -> Iterator[str]:
    yield "str1"


def time_period_option() -> Iterator[str]:
    yield "time_period_1"


def cb_folder_options() -> Iterator[str]:
    yield "Main"


def cb_list_str_options() -> Iterator[list[str]]:
    yield ["str1", "str2", "str3"]


def contact_group_list_option() -> Iterator[list[str]]:
    yield ["cg1", "cg2"]


def host_group_list_option() -> Iterator[list[str]]:
    yield ["hg1", "hg2"]


def service_group_list_option() -> Iterator[list[str]]:
    yield ["sg1", "sg2"]


def cb_host_list_of_hosts() -> Iterator[list[str]]:
    yield ["example.com"]


def cb_list_sites_options() -> Iterator[list[str]]:
    yield ["site_id_1"]


def cb_from_to_notifications() -> Iterator[dict[str, int]]:
    yield {"beginning_from": 2, "up_to": 493}


def cb_throttle_periodic_notifications() -> Iterator[dict[str, int]]:
    yield {"beginning_from": 2, "send_every_nth_notification": 493}


def cb_labels() -> Iterator[list[dict[str, str]]]:
    yield [{"key": "label1", "value": "value1"}, {"key": "label2", "value": "value2"}]


def cb_regex() -> Iterator:
    yield {"match_type": "match_id", "regex_list": ["^abc", "^def"]}
    yield {"match_type": "match_alias", "regex_list": ["alias1", "alias2"]}


def cb_service_levels() -> Iterator[dict[str, str]]:
    for from_level, to_level in permutations(["no_service_level", "silver", "gold", "platinum"], 2):
        yield {
            "from_level": from_level,
            "to_level": to_level,
        }


def cb_host_tags() -> Iterator[dict[str, str]]:
    yield {
        "ip_address_family": "ip-v4-only",
        "ip_v4": "ip-v4",
        "ip_v6": "!ip-v6",
        "checkmk_agent_api_integration": "special-agents",
        "piggyback": "piggyback",
        "snmp": "snmp-v1",
        "monitor_via_snmp": "snmp",
        "monitor_via_checkmkagent_or_specialagent": "tcp",
        "monitor_via_checkmkagent": "checkmk-agent",
        "only_ping_this_device": "ping",
        "criticality": "test",
        "networking_segment": "wan",
    }

    yield {
        "ip_address_family": "ignore",
        "ip_v4": "ignore",
        "ip_v6": "ignore",
        "checkmk_agent_api_integration": "ignore",
        "piggyback": "ignore",
        "snmp": "ignore",
        "monitor_via_snmp": "ignore",
        "monitor_via_checkmkagent_or_specialagent": "ignore",
        "monitor_via_checkmkagent": "ignore",
        "only_ping_this_device": "ignore",
        "criticality": "ignore",
        "networking_segment": "ignore",
    }


def cb_host_event_type() -> Iterator[dict[str, bool]]:
    def host_event_types(value: bool) -> dict[str, bool]:
        return {
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

    yield host_event_types(True)
    yield host_event_types(False)


def cb_service_event_type() -> Iterator[dict[str, bool]]:
    def service_event_types(value: bool) -> dict[str, bool]:
        return {
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

    yield service_event_types(True)
    yield service_event_types(False)


def cb_event_console() -> Iterator[dict[str, Any]]:
    yield {
        "match_type": "do_not_match_event_console_alerts",
    }

    yield {
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
    }

    yield {
        "match_type": "match_only_event_console_alerts",
        "values": {
            "match_rule_ids": {"state": "disabled"},
            "match_syslog_priority": {"state": "disabled"},
            "match_syslog_facility": {"state": "disabled"},
            "match_event_comment": {"state": "disabled"},
        },
    }


def conditions_options(status_code: int) -> Iterator:
    conditions = {
        "match_sites": cb_list_sites_options,
        "match_folder": cb_folder_options,
        "match_host_tags": cb_host_tags,
        "match_host_labels": cb_labels,
        "match_host_groups": host_group_list_option,
        "match_hosts": cb_host_list_of_hosts,
        "match_exclude_hosts": cb_host_list_of_hosts,
        "match_service_labels": cb_labels,
        "match_service_groups": service_group_list_option,
        "match_exclude_service_groups": service_group_list_option,
        "match_service_groups_regex": cb_regex,
        "match_exclude_service_groups_regex": cb_regex,
        "match_services": cb_list_str_options,
        "match_exclude_services": cb_list_str_options,
        "match_check_types": cb_list_str_options,
        "match_plugin_output": cb_str_options,
        "match_contact_groups": contact_group_list_option,
        "match_service_levels": cb_service_levels,
        "match_only_during_time_period": time_period_option,
        "match_host_event_type": cb_host_event_type,
        "match_service_event_type": cb_service_event_type,
        "restrict_to_notification_numbers": cb_from_to_notifications,
        "throttle_periodic_notifications": cb_throttle_periodic_notifications,
        "match_notification_comment": cb_str_options,
        "event_console_alerts": cb_event_console,
    }

    for k, gen in conditions.items():
        if status_code == 200:
            for value in gen():
                yield {k: {"state": "enabled", "value": value}}  # type: ignore
            yield {k: {"state": "disabled"}}  # type: ignore
        else:
            yield {k: {"state": "enabled"}}  # type: ignore


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
            "value": ["monkey@tribe29.com", "thelionsleepstonight@thetokens.com"],
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
        owner="admin",
        password="tt",
        shared=["all"],
        customer="global",
    )


@managedtest
@pytest.mark.usefixtures("with_host")
@pytest.mark.parametrize("testdata", conditions_options(200))
def test_create_and_update_rule_with_conditions_data_200(
    clients: ClientRegistry,
    testdata: APIConditions,
) -> None:
    setup_site_data(clients)

    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)
    config["conditions"].update(testdata)

    r2 = clients.RuleNotification.edit(
        rule_id=r1.json["id"],
        rule_config=config,
    )
    assert r2.json["extensions"] == {"rule_config": config}


@managedtest
@pytest.mark.parametrize("testdata", conditions_options(400))
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
            "notification_bulks_based_on_custom_macros": ["macro3", "macro4"],
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
        "sort_order_for_bulk_notificaions": {
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
        "sort_order_for_bulk_notificaions": {"state": "enabled", "value": "newest_first"},
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
        "username": "Gav",
        "password": "gav1234",
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
            "value": "http://http_proxy_test_url/here",
        },
        "http_proxy": {
            "state": "enabled",
            "value": {"option": "environment"},
        },
        "priority": {
            "state": "enabled",
            "value": "high",
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
        "username": "test_username",
        "user_password": {
            "option": "explicit",
            "password": "testpassword",
        },
        "use_site_id_prefix": {
            "state": "enabled",
            "value": "use_site_id_prefix",
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
        "username": "test_username",
        "user_password": {
            "option": "store",
            "store_id": "some_store_id",
        },
        "use_site_id_prefix": {
            "state": "enabled",
            "value": "use_site_id_prefix",
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
            "url": "http://www.slack-webhook-url.com",
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
]


@pytest.mark.parametrize("plugin_data", plugin_test_data)
def test_update_notification_method_cancel_previous(
    clients: ClientRegistry,
    plugin_data: PluginType,
) -> None:
    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)

    config["notification_method"]["notify_plugin"] = {
        "option": "cancel_previous_notifications",
        "plugin_params": {"plugin_name": plugin_data["plugin_name"]},
    }
    r2 = clients.RuleNotification.edit(
        rule_id=r1.json["id"],
        rule_config=config,
    )
    assert r2.json["extensions"] == {"rule_config": config}


@managedtest
@pytest.mark.parametrize("plugin_data", plugin_test_data)
def test_create_notification_method(
    clients: ClientRegistry,
    plugin_data: PluginType,
) -> None:
    setup_site_data(clients)

    config = notification_rule_request_example()
    config["notification_method"]["notify_plugin"] = {
        "option": "create_notification_with_the_following_parameters",
        "plugin_params": plugin_data,
    }

    r1 = clients.RuleNotification.create(rule_config=config)
    assert r1.json["extensions"] == {"rule_config": config}


@managedtest
@pytest.mark.parametrize("plugin_data", plugin_test_data)
def test_update_notification_method(
    clients: ClientRegistry,
    plugin_data: PluginType,
) -> None:
    setup_site_data(clients)

    config = notification_rule_request_example()
    r1 = clients.RuleNotification.create(rule_config=config)
    config["notification_method"]["notify_plugin"] = {
        "option": "create_notification_with_the_following_parameters",
        "plugin_params": plugin_data,
    }
    r2 = clients.RuleNotification.edit(
        rule_id=r1.json["id"],
        rule_config=config,
    )
    assert r2.json["extensions"] == {"rule_config": config}


service_now: API_ServiceNowData = {
    "plugin_name": "servicenow",
    "servicenow_url": "https://service_now_url_test",
    "http_proxy": {
        "state": "enabled",
        "value": {"option": "url", "url": "http://http_proxy_test_url/here"},
    },
    "username": "test_username",
    "user_password": {
        "option": "explicit",
        "password": "testpassword",
    },
    "use_site_id_prefix": {
        "state": "enabled",
        "value": "use_site_id_prefix",
    },
    "optional_timeout": {
        "state": "enabled",
        "value": "13",
    },
    "management_type": {},
}

service_now_incident: MgmtTypeAPI = {
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


def incident_states() -> list[MgmtTypeParamsAPI]:
    d: list[MgmtTypeParamsAPI] = []
    for n, predefined_state in enumerate(list(get_args(INCIDENT_STATE_TYPE))):
        d.append(
            {
                "state_acknowledgement": {
                    "state": "enabled",
                    "value": {"start_predefined": predefined_state},
                },
            },
        )
        d.append(
            {
                "state_acknowledgement": {
                    "state": "enabled",
                    "value": {"start_integer": n},
                },
            },
        )
        d.append(
            {
                "state_downtime": {
                    "state": "enabled",
                    "value": {
                        "start_predefined": predefined_state,
                        "end_predefined": predefined_state,
                    },
                },
            },
        )
        d.append(
            {
                "state_downtime": {
                    "state": "enabled",
                    "value": {"start_integer": n, "end_integer": n},
                },
            },
        )
        d.append(
            {
                "state_recovery": {
                    "state": "enabled",
                    "value": {"start_predefined": predefined_state},
                },
            },
        )
        d.append(
            {
                "state_recovery": {
                    "state": "enabled",
                    "value": {"start_integer": n},
                },
            },
        )
    return d


@pytest.mark.parametrize("mgmt_type_data", incident_states())
def test_service_now_management_incident_types_200(
    clients: ClientRegistry,
    mgmt_type_data: MgmtTypeParamsAPI,
) -> None:
    service_now["management_type"] = service_now_incident
    service_now["management_type"]["params"].update(mgmt_type_data)
    config = notification_rule_request_example()
    config["notification_method"]["notify_plugin"] = {
        "option": "create_notification_with_the_following_parameters",
        "plugin_params": service_now,
    }
    r1 = clients.RuleNotification.create(rule_config=config)
    assert r1.json["extensions"] == {"rule_config": config}


service_now_case: MgmtTypeAPI = {
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


def case_states() -> list[MgmtTypeParamsAPI]:
    d: list[MgmtTypeParamsAPI] = []
    for n, predefined_state in enumerate(list(get_args(CASE_STATE_TYPE))):
        d.append(
            {
                "state_recovery": {
                    "state": "enabled",
                    "value": {"start_predefined": predefined_state},
                },
            },
        )
        d.append(
            {
                "state_recovery": {
                    "state": "enabled",
                    "value": {"start_integer": n},
                },
            },
        )
    return d


@pytest.mark.parametrize("mgmt_type_data", case_states())
def test_service_now_management_case_types_200(
    clients: ClientRegistry,
    mgmt_type_data: MgmtTypeParamsAPI,
) -> None:
    service_now["management_type"] = service_now_case
    service_now["management_type"]["params"].update(mgmt_type_data)
    config = notification_rule_request_example()
    config["notification_method"]["notify_plugin"] = {
        "option": "create_notification_with_the_following_parameters",
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
        "option": "create_notification_with_the_following_parameters",
        "plugin_params": plugin,
    }
    return config


def plugin_with_bulking(
    bulking: Literal["allowed", "not_allowed"]
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
def test_bulking_200(
    clients: ClientRegistry,
    config: APINotificationRule,
) -> None:
    setup_site_data(clients)

    clients.RuleNotification.create(rule_config=config)


@managedtest
@pytest.mark.parametrize("config", plugin_with_bulking(bulking="not_allowed"))
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
