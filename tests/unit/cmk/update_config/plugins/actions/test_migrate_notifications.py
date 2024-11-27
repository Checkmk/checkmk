#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest
from polyfactory.factories import TypedDictFactory
from pytest import MonkeyPatch

from cmk.utils.notify_types import (
    AsciiMailPluginModel,
    BasicAuthCredentials,
    CiscoPluginModel,
    EventRule,
    IlertPluginModel,
    JiraIssuePluginModel,
    MailPluginModel,
    MgmtTypeCase,
    MicrosoftTeamsPluginModel,
    MKEventdPluginModel,
    NotificationParameterID,
    NotificationParameterSpecs,
    NotificationPluginNameStr,
    OpsGenieIssuesPluginModel,
    PagerDutyPluginModel,
    PushoverPluginModel,
    ServiceNowPluginModel,
    SignL4PluginModel,
    SlackPluginModel,
    SmsApiPluginModel,
    SpectrumPluginModel,
    SplunkPluginModel,
)

from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.gui.watolib import sample_config
from cmk.gui.watolib.notifications import (
    NotificationParameterConfigFile,
    NotificationRuleConfigFile,
)

from cmk.update_config.plugins.actions.migrate_notifications import (
    MigrateNotifications,
)


class EventRuleFactory(TypedDictFactory[EventRule]): ...


@pytest.fixture(autouse=True)
def patch_new_notification_parameter_id(monkeypatch: MonkeyPatch) -> None:
    """Swap out random uuid generation with an accumulating mock uuid.

    This helps with asserting the output of the tests. Ideally, we could inject this stub into
    `MigrateNotificationParameters`. However, the class relies on an abstract base class, so there
    is little we can do in terms of changing the method signatures - so patching it is.
    """
    current_id = 0

    def patch() -> NotificationParameterID:
        nonlocal current_id
        current_id += 1
        return NotificationParameterID(f"<uuid-{current_id}>")

    monkeypatch.setattr(sample_config, "new_notification_parameter_id", patch)


@pytest.mark.parametrize(
    ["rule_config", "notification_parameter", "expected_plugin"],
    [
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "spectrum",
                        SpectrumPluginModel(
                            destination="1.1.1.1",
                            community="gaergerag",  # type: ignore[typeddict-item]
                            baseoid="1.3.6.1.4.1.1234",
                        ),
                    ),
                )
            ],
            {
                "spectrum": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "destination": "1.1.1.1",
                            "community": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<uuid-1>", "gaergerag"),
                            ),
                            "baseoid": "1.3.6.1.4.1.1234",
                        },
                    }
                }
            },
            [("spectrum", "<uuid-1>")],
            id="Spectrum",
            marks=pytest.mark.skip(reason="Fails because of UUID difference in PW"),
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "asciimail",
                        AsciiMailPluginModel(
                            {
                                "common_body": "Host:     $HOSTNAME$\nAlias:    $HOSTALIAS$\nAddress:  $HOSTADDRESS$\n",
                                "host_body": "Event:    $EVENT_TXT$\nOutput:   $HOSTOUTPUT$\nPerfdata: $HOSTPERFDATA$\n$LONGHOSTOUTPUT$\n",
                                "service_body": "Service:  $SERVICEDESC$\n+          Event:    $EVENT_TXT$\n+          Output:   $SERVICEOUTPUT$\n+          Perfdata: $SERVICEPERFDATA$\n+          $LONGSERVICEOUTPUT$\n",
                                "from": {"address": "from@you.com", "display_name": "From Someone"},
                                "reply_to": {
                                    "address": "to@you.com",
                                    "display_name": "To Somebody",
                                },
                                "host_subject": "Check_MK: $HOSTNAME$ - $EVENT_TXT$', 'service_subject': 'Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
                                "service_subject": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
                                "disable_multiplexing": True,
                                "bulk_sort_order": "newest_first",
                            }
                        ),
                    ),
                )
            ],
            {
                "asciimail": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "common_body": "Host:     $HOSTNAME$\nAlias:    $HOSTALIAS$\nAddress:  $HOSTADDRESS$\n",
                            "host_body": "Event:    $EVENT_TXT$\nOutput:   $HOSTOUTPUT$\nPerfdata: $HOSTPERFDATA$\n$LONGHOSTOUTPUT$\n",
                            "service_body": "Service:  $SERVICEDESC$\n+          Event:    $EVENT_TXT$\n+          Output:   $SERVICEOUTPUT$\n+          Perfdata: $SERVICEPERFDATA$\n+          $LONGSERVICEOUTPUT$\n",
                            "from": {"address": "from@you.com", "display_name": "From Someone"},
                            "reply_to": {"address": "to@you.com", "display_name": "To Somebody"},
                            "host_subject": "Check_MK: $HOSTNAME$ - $EVENT_TXT$', 'service_subject': 'Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
                            "service_subject": "Check_MK: $HOSTNAME$/$SERVICEDESC$ $EVENT_TXT$",
                            "disable_multiplexing": True,
                            "bulk_sort_order": "newest_first",
                        },
                    }
                }
            },
            [("asciimail", "<uuid-1>")],
            id="ASCII Email",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "cisco_webex_teams",
                        CiscoPluginModel(
                            webhook_url=(
                                "webhook_url",
                                "https://alert.victorops.com/integrations/blub",
                            ),
                            url_prefix={"automatic": "https"},  # type: ignore[typeddict-item]
                            ignore_ssl=True,
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                        ),
                    ),
                )
            ],
            {
                "cisco_webex_teams": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "webhook_url": (
                                "webhook_url",
                                "https://alert.victorops.com/integrations/blub",
                            ),
                            "url_prefix": ("automatic_https", None),
                            "ignore_ssl": True,
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                        },
                    }
                }
            },
            [("cisco_webex_teams", "<uuid-1>")],
            id="Cisco Webex Teams explicit webhook_url",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "cisco_webex_teams",
                        CiscoPluginModel(
                            webhook_url=("store", "password_1"),
                            url_prefix={"automatic": "https"},  # type: ignore[typeddict-item]
                            ignore_ssl=True,
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                        ),
                    ),
                )
            ],
            {
                "cisco_webex_teams": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "webhook_url": (
                                "store",
                                "password_1",
                            ),
                            "url_prefix": ("automatic_https", None),
                            "ignore_ssl": True,
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                        },
                    }
                }
            },
            [("cisco_webex_teams", "<uuid-1>")],
            id="Cisco Webex Teams explicit webhook_url",
            marks=pytest.mark.skip(
                reason="Still investigating how to use correct FormSpec for Passwordstoremix"
            ),
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "mkeventd",
                        MKEventdPluginModel(
                            facility=5,
                            remote="1.1.1.1",
                        ),
                    ),
                )
            ],
            {
                "mkeventd": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {"facility": 5, "remote": "1.1.1.1"},
                    }
                }
            },
            [("mkeventd", "<uuid-1>")],
            id="Forward notification to Event Console",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "opsgenie_issues",
                        OpsGenieIssuesPluginModel(
                            password=("password", "zhfziuofoziudfozuidouizd"),  # type: ignore[typeddict-item]
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                        ),
                    ),
                ),
            ],
            {
                "opsgenie_issues": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "password": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<uuid-b>", "zhfziuofoziudfozuidouizd"),
                            ),
                            "proxy_url": (
                                "cmk_postprocessed",
                                "no_proxy",
                                "",
                            ),
                        },
                    }
                }
            },
            [("opsgenie_issues", "<uuid-1>")],
            id="OpsGenie Issues",
            marks=pytest.mark.skip(reason="Fails because of UUID difference in PW"),
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "ilert",
                        IlertPluginModel(
                            ilert_api_key=(
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<uuid-a>", "gaergerag"),
                            ),
                            ilert_priority="HIGH",
                            ilert_summary_host="",
                            ilert_summary_service="",
                            url_prefix={"automatic": "https"},  # type: ignore[typeddict-item]
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                        ),
                    ),
                ),
            ],
            {
                "ilert": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "ilert_api_key": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<uuid-a>", "gaergerag"),
                            ),
                            "ilert_priority": "HIGH",
                            "ilert_summary_host": "",
                            "ilert_summary_service": "",
                            "url_prefix": ("automatic_https", None),
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                        },
                    }
                }
            },
            [("ilert", "<uuid-1>")],
            id="Ilert",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "jira_issues",
                        JiraIssuePluginModel(
                            url="test_url",
                            auth=(
                                "auth_basic",
                                BasicAuthCredentials(
                                    username="username",
                                    password=(
                                        "cmk_postprocessed",
                                        "explicit_password",
                                        ("<uuid-a>", "gaergerag"),
                                    ),
                                ),
                            ),
                            project="project",
                            issuetype="issuetype",
                            host_customid="custom_id",
                            service_customid="custom_id",
                            monitoring="monitoring",
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                        ),
                    ),
                )
            ],
            {
                "jira_issues": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "url": "test_url",
                            "auth": (
                                "auth_basic",
                                {
                                    "username": "username",
                                    "password": (
                                        "cmk_postprocessed",
                                        "explicit_password",
                                        ("<uuid-a>", "gaergerag"),
                                    ),
                                },
                            ),
                            "project": "project",
                            "issuetype": "issuetype",
                            "host_customid": "custom_id",
                            "service_customid": "custom_id",
                            "monitoring": "monitoring",
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                        },
                    }
                }
            },
            [("jira_issues", "<uuid-1>")],
            id="Jira Issues",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "msteams",
                        MicrosoftTeamsPluginModel(
                            webhook_url=("webhook_url", "https://mywebhook.url"),
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                        ),
                    ),
                )
            ],
            {
                "msteams": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "webhook_url": (
                                "webhook_url",
                                "https://mywebhook.url",
                            ),
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                        },
                    }
                }
            },
            [("msteams", "<uuid-1>")],
            id="Microsoft teams",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "pagerduty",
                        PagerDutyPluginModel(
                            routing_key=("routing_key", "zhfziuofoziudfozuidouizd"),
                            webhook_url="https://events.pagerduty.com/v2/enqueue",
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                        ),
                    ),
                )
            ],
            {
                "pagerduty": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "routing_key": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<uuid-1>", "zhfziuofoziudfozuidouizd"),
                            ),
                            "webhook_url": "https://events.pagerduty.com/v2/enqueue",
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                        },
                    }
                }
            },
            [("pagerduty", "<uuid-1>")],
            id="PagerDuty",
            marks=pytest.mark.skip(reason="Fails because of UUID difference in PW"),
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "pushover",
                        PushoverPluginModel(
                            api_key="jkdleowiufnkg8jwe9whf9ig6f7roe91d",
                            recipient_key="jkdleowiufnkg8jwe9whf9ig6f7roe91d",
                            url_prefix={"automatic": "https"},  # type: ignore[typeddict-item]
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                            priority=("normal", None),
                        ),
                    ),
                )
            ],
            {
                "pushover": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "api_key": "jkdleowiufnkg8jwe9whf9ig6f7roe91d",
                            "recipient_key": "jkdleowiufnkg8jwe9whf9ig6f7roe91d",
                            "url_prefix": ("automatic_https", None),
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                            "priority": ("normal", None),
                        },
                    }
                }
            },
            [("pushover", "<uuid-1>")],
            id="PushOver",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "servicenow",
                        ServiceNowPluginModel(
                            url="url",
                            auth=(
                                "auth_basic",
                                BasicAuthCredentials(
                                    username="username",
                                    password=(
                                        "cmk_postprocessed",
                                        "explicit_password",
                                        ("<uuid-a>", "gaergerag"),
                                    ),
                                ),
                            ),
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                            mgmt_type=(
                                "case",
                                MgmtTypeCase(
                                    priority="low",
                                    recovery_state={"start": ("predefined", "closed")},
                                ),
                            ),
                            use_site_id="use_site_id",
                        ),
                    ),
                )
            ],
            {
                "servicenow": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "url": "url",
                            "auth": (
                                "auth_basic",
                                {
                                    "username": "username",
                                    "password": (
                                        "cmk_postprocessed",
                                        "explicit_password",
                                        ("<uuid-a>", "gaergerag"),
                                    ),
                                },
                            ),
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                            "mgmt_type": (
                                "case",
                                {
                                    "priority": "low",
                                    "recovery_state": {"start": ("predefined", "closed")},
                                },
                            ),
                            "use_site_id": "use_site_id",
                        },
                    }
                }
            },
            [("servicenow", "<uuid-1>")],
            id="ServiceNow",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "signl4",
                        SignL4PluginModel(
                            password=("password", "gaergerag"),  # type: ignore[typeddict-item]
                            url_prefix={"automatic": "https"},  # type: ignore[typeddict-item]
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                        ),
                    ),
                )
            ],
            {
                "signl4": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "password": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<uuid-a>", "gaergerag"),
                            ),
                            "url_prefix": ("automatic_https", None),
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                        },
                    }
                }
            },
            [("signl4", "<uuid-1>")],
            id="Signl4",
            marks=pytest.mark.skip(reason="Fails because of UUID difference in PW"),
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "slack",
                        SlackPluginModel(
                            webhook_url=(
                                "webhook_url",
                                "https://alert.victorops.com/integrations/blub",
                            ),
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                        ),
                    ),
                )
            ],
            {
                "slack": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "webhook_url": (
                                "webhook_url",
                                "https://alert.victorops.com/integrations/blub",
                            ),
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                        },
                    }
                }
            },
            [("slack", "<uuid-1>")],
            id="Slack",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "sms_api",
                        SmsApiPluginModel(
                            modem_type="trb140",
                            url="url",
                            username="username",
                            password=(
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<uuid-a>", "gaergerag"),
                            ),
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                            timeout="60",
                        ),
                    ),
                )
            ],
            {
                "sms_api": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "modem_type": "trb140",
                            "url": "url",
                            "username": "username",
                            "password": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<uuid-a>", "gaergerag"),
                            ),
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                            "timeout": "60",
                        },
                    }
                }
            },
            [("sms_api", "<uuid-1>")],
            id="SMS API",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "victorops",
                        SplunkPluginModel(
                            webhook_url=(
                                "webhook_url",
                                "https://alert.victorops.com/integrations/blub",
                            ),
                            url_prefix={"automatic": "https"},  # type: ignore[typeddict-item]
                            proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
                        ),
                    ),
                )
            ],
            {
                "victorops": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "webhook_url": (
                                "webhook_url",
                                "https://alert.victorops.com/integrations/blub",
                            ),
                            "url_prefix": ("automatic_https", None),
                            "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                        },
                    }
                }
            },
            [("victorops", "<uuid-1>")],
            id="Splunk",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "opsgenie_issues",
                        OpsGenieIssuesPluginModel(
                            password=(
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<uuid-b>", "zhfziuofoziudfozuidouizd"),
                            ),
                            host_desc="Host: $HOSTNAME$\nEvent:    $EVENT_TXT$\nOutput:   $HOSTOUTPUT$\nPerfdata: $HOSTPERFDATA$\n$LONGHOSTOUTPUT$\n",
                            actions=["MY_ACTION"],
                            tags=["MY_TAG"],
                        ),
                    ),
                ),
                EventRuleFactory.build(
                    notify_plugin=(
                        "mail",
                        MailPluginModel(
                            {
                                "url_prefix": {"automatic": "https"},  # type: ignore[typeddict-item]
                                "disable_multiplexing": True,
                            }
                        ),
                    ),
                ),
                EventRuleFactory.build(
                    notify_plugin=(
                        "mail",
                        MailPluginModel(
                            {
                                "url_prefix": {"automatic": "https"},  # type: ignore[typeddict-item]
                                "from": {"address": "from@me.com"},
                                "disable_multiplexing": True,
                            }
                        ),
                    ),
                ),
                EventRuleFactory.build(
                    notify_plugin=(
                        "mkeventd",
                        MKEventdPluginModel(
                            facility=5,
                            remote="1.1.1.1",
                        ),
                    ),
                ),
                EventRuleFactory.build(
                    notify_plugin=(
                        "mkeventd",
                        MKEventdPluginModel(
                            facility=5,
                            remote="1.1.1.1",
                        ),
                    ),
                ),
                EventRuleFactory.build(
                    notify_plugin=(
                        "mkeventd",
                        None,
                    ),
                ),
            ],
            {
                "opsgenie_issues": {
                    "<uuid-1>": {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "password": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<uuid-b>", "zhfziuofoziudfozuidouizd"),
                            ),
                            "host_desc": "Host: $HOSTNAME$\nEvent:    $EVENT_TXT$\nOutput:   $HOSTOUTPUT$\nPerfdata: $HOSTPERFDATA$\n$LONGHOSTOUTPUT$\n",
                            "actions": ["MY_ACTION"],
                            "tags": ["MY_TAG"],
                        },
                    }
                },
                "mail": {
                    "<uuid-2>": {
                        "general": {
                            "description": "Migrated from notification rule #1",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "url_prefix": ("automatic_https", None),
                            "disable_multiplexing": True,
                        },
                    },
                    "<uuid-3>": {
                        "general": {
                            "description": "Migrated from notification rule #2",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "url_prefix": ("automatic_https", None),
                            "from": {"address": "from@me.com"},
                            "disable_multiplexing": True,
                        },
                    },
                },
                "mkeventd": {
                    "<uuid-4>": {
                        "general": {
                            "description": "Migrated from notification rule #3",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {"facility": 5, "remote": "1.1.1.1"},
                    }
                },
            },
            [
                ("opsgenie_issues", "<uuid-1>"),
                ("mail", "<uuid-2>"),
                ("mail", "<uuid-3>"),
                ("mkeventd", "<uuid-4>"),
                ("mkeventd", "<uuid-4>"),
                ("mkeventd", None),
            ],
            id="Mixed notification rules",
        ),
    ],
)
def test_migrate_notifications(
    rule_config: list[EventRule],
    notification_parameter: NotificationParameterSpecs,
    expected_plugin: list[tuple[NotificationPluginNameStr, NotificationParameterID]],
) -> None:
    with application_and_request_context():
        NotificationRuleConfigFile().save(rule_config)

        MigrateNotifications(
            name="migrate_notification_parameters",
            title="Migrate notification parameters",
            sort_index=50,
        )(logging.getLogger())

    migrated_parameters = NotificationParameterConfigFile().load_for_reading()

    assert migrated_parameters == notification_parameter

    for nr, rule in enumerate(NotificationRuleConfigFile().load_for_reading()):
        assert rule["notify_plugin"] == expected_plugin[nr]
