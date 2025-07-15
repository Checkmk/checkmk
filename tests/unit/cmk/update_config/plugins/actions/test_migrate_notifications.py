#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Final
from unittest.mock import MagicMock, patch

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
    NotificationParameterSpec,
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
from cmk.utils.password_store import Password

import cmk.gui.exceptions
from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.gui.watolib import sample_config
from cmk.gui.watolib.notifications import (
    NotificationParameterConfigFile,
    NotificationRuleConfigFile,
)
from cmk.gui.watolib.password_store import PasswordStore

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


PW_STORE_KEY = "from_store"
PW_STORE = Password(
    title="title",
    password="password",
    comment="comment",
    docu_url="docu_url",
    owned_by=None,
    shared_with=[],
)


@pytest.fixture(autouse=True)
def make_pw_store_user_independent(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(PasswordStore, "filter_usable_entries", lambda self, entries: entries)
    monkeypatch.setattr(PasswordStore, "load_for_reading", lambda path: {PW_STORE_KEY: PW_STORE})


def migrate_parameters(rule_config: list[EventRule]) -> dict[str, NotificationParameterSpec]:
    NotificationRuleConfigFile().save(rule_config, pprint_value=False)
    with application_and_request_context():
        MigrateNotifications(
            name="migrate_notification_parameters",
            title="Migrate notification parameters",
            sort_index=50,
        )(logging.getLogger())

    return NotificationParameterConfigFile().load_for_reading()


SPECTRUM_RULE_CONFIG: Final = [
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
]


@patch("cmk.gui.wato._notification_parameter._spectrum.uuid4", return_value="<migrate-uuid>")
def test_migrate_spectrum_notification_parameter(_: MagicMock) -> None:
    value = migrate_parameters(SPECTRUM_RULE_CONFIG)
    expected = {
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
                        ("<migrate-uuid>", "gaergerag"),
                    ),
                    "baseoid": "1.3.6.1.4.1.1234",
                },
            }
        }
    }
    assert value == expected


def test_migrate_spectrum_notification_plugin() -> None:
    migrate_parameters(SPECTRUM_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("spectrum", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


ASCII_RULE_CONFIG: Final = [
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
        )
    )
]


def test_migrate_asciimail_notification_parameter() -> None:
    value = migrate_parameters(ASCII_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_asciimail_notification_plugin() -> None:
    migrate_parameters(ASCII_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("asciimail", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


CISCO_WEBEX_TEAMS_EXPLICIT_WEBHOOK_RULE_CONFIG: Final = [
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
]


def test_migrate_cisco_webex_teams_explicit_webhook_notification_parameter() -> None:
    value = migrate_parameters(CISCO_WEBEX_TEAMS_EXPLICIT_WEBHOOK_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_cisco_webex_teams_explicit_webhook_notification_plugin() -> None:
    migrate_parameters(CISCO_WEBEX_TEAMS_EXPLICIT_WEBHOOK_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("cisco_webex_teams", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


CISCO_WEBEX_TEAMS_PASSWORD_STORE_RULE_CONFIG: Final = [
    EventRuleFactory.build(
        notify_plugin=(
            "cisco_webex_teams",
            CiscoPluginModel(
                webhook_url=("store", PW_STORE_KEY),
                url_prefix={"automatic": "https"},  # type: ignore[typeddict-item]
                ignore_ssl=True,
                proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
            ),
        ),
    )
]


def test_migrate_cisco_webex_teams_password_store_notification_parameter() -> None:
    value = migrate_parameters(CISCO_WEBEX_TEAMS_PASSWORD_STORE_RULE_CONFIG)
    expected = {
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
                        PW_STORE_KEY,
                    ),
                    "url_prefix": ("automatic_https", None),
                    "ignore_ssl": True,
                    "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                },
            }
        }
    }
    assert value == expected


def test_migrate_cisco_webex_teams_password_store_notification_plugin() -> None:
    migrate_parameters(CISCO_WEBEX_TEAMS_PASSWORD_STORE_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("cisco_webex_teams", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


MKEVENTD_RULE_CONFIG: Final = [
    EventRuleFactory.build(
        notify_plugin=(
            "mkeventd",
            MKEventdPluginModel(
                facility=5,
                remote="1.1.1.1",
            ),
        ),
    )
]


def test_migrate_mkeventd_notification_parameter() -> None:
    value = migrate_parameters(MKEVENTD_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_mkeventd_notification_plugin() -> None:
    migrate_parameters(MKEVENTD_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("mkeventd", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


OPSGENIE_ISSUES_RULE_CONFIG: Final = [
    EventRuleFactory.build(
        notify_plugin=(
            "opsgenie_issues",
            OpsGenieIssuesPluginModel(
                password=("password", "zhfziuofoziudfozuidouizd"),  # type: ignore[typeddict-item]
                proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
            ),
        ),
    ),
]


@patch("cmk.rulesets.v1.form_specs._migrations.uuid4", return_value="<migrate-uuid>")
def test_migrate_opsgenie_notification_parameter(_: MagicMock) -> None:
    value = migrate_parameters(OPSGENIE_ISSUES_RULE_CONFIG)
    expected = {
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
                        ("<migrate-uuid>", "zhfziuofoziudfozuidouizd"),
                    ),
                    "proxy_url": (
                        "cmk_postprocessed",
                        "no_proxy",
                        "",
                    ),
                },
            }
        }
    }
    assert value == expected


def test_migrate_opsgenie_notification_plugin() -> None:
    migrate_parameters(OPSGENIE_ISSUES_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("opsgenie_issues", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


ILERT_RULE_CONFIG: Final = [
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
]


def test_migrate_ilert_notification_parameter() -> None:
    value = migrate_parameters(ILERT_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_ilert_notification_plugin() -> None:
    migrate_parameters(ILERT_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("ilert", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


JIRA_ISSUES_RULE_CONFIG: Final = [
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
]


def test_migrate_jira_issues_notification_parameter() -> None:
    value = migrate_parameters(JIRA_ISSUES_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_jira_issues_notification_plugin() -> None:
    migrate_parameters(JIRA_ISSUES_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("jira_issues", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


MSTEAMS_RULE_CONFIG: Final = [
    EventRuleFactory.build(
        notify_plugin=(
            "msteams",
            MicrosoftTeamsPluginModel(
                webhook_url=("webhook_url", "https://mywebhook.url"),
                proxy_url=("no_proxy", None),  # type: ignore[typeddict-item]
            ),
        ),
    )
]


def test_migrate_msteams_notification_parameter() -> None:
    value = migrate_parameters(MSTEAMS_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_msteams_notification_plugin() -> None:
    migrate_parameters(MSTEAMS_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("msteams", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


PAGERDUTY_RULE_CONFIG: Final = [
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
]


@patch(
    "cmk.gui.wato._notification_parameter._pagerduty.password_store.ad_hoc_password_id",
    return_value="<migrate-uuid>",
)
def test_migrate_pagerduty_notification_parameter(_: MagicMock) -> None:
    value = migrate_parameters(PAGERDUTY_RULE_CONFIG)
    expected = {
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
                        ("<migrate-uuid>", "zhfziuofoziudfozuidouizd"),
                    ),
                    "webhook_url": "https://events.pagerduty.com/v2/enqueue",
                    "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                },
            }
        }
    }
    assert value == expected


def test_migrate_pagerduty_notification_plugin() -> None:
    migrate_parameters(PAGERDUTY_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("pagerduty", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


PUSHOVER_RULE_CONFIG: Final = [
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
]


def test_migrate_pushover_notification_parameter() -> None:
    value = migrate_parameters(PUSHOVER_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_pushover_notification_plugin() -> None:
    migrate_parameters(PUSHOVER_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("pushover", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


SERVICENOW_RULE_CONFIG: Final = [
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
]


def test_migrate_servicenow_notification_parameter() -> None:
    value = migrate_parameters(SERVICENOW_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_servicenow_notification_plugin() -> None:
    migrate_parameters(SERVICENOW_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("servicenow", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


SIGNL4_RULE_CONFIG: Final = [
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
]


@patch("cmk.rulesets.v1.form_specs._migrations.uuid4", return_value="<migrate-uuid>")
def test_migrate_signl4_notification_parameter(_: MagicMock) -> None:
    value = migrate_parameters(SIGNL4_RULE_CONFIG)
    expected = {
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
                        ("<migrate-uuid>", "gaergerag"),
                    ),
                    "url_prefix": ("automatic_https", None),
                    "proxy_url": ("cmk_postprocessed", "no_proxy", ""),
                },
            }
        }
    }
    assert value == expected


def test_migrate_signl4_notification_plugin() -> None:
    migrate_parameters(SIGNL4_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("signl4", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


SLACK_RULE_CONFIG: Final = [
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
]


def test_migrate_slack_notification_parameter() -> None:
    value = migrate_parameters(SLACK_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_slack_notification_plugin() -> None:
    migrate_parameters(SLACK_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("slack", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


SMS_API_RULE_CONFIG: Final = [
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
]


def test_migrate_sms_api_notification_parameter() -> None:
    value = migrate_parameters(SMS_API_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_sms_api_notification_plugin() -> None:
    migrate_parameters(SMS_API_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("sms_api", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


SPLUNK_RULE_CONFIG: Final = [
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
]


def test_migrate_splunk_notification_parameter() -> None:
    value = migrate_parameters(SPLUNK_RULE_CONFIG)
    expected = {
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
    }
    assert value == expected


def test_migrate_splunk_notification_plugin() -> None:
    migrate_parameters(SPLUNK_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [("victorops", "<uuid-1>")]

    assert all(got == want for got, want in zip(value, expected))


MIXED_NOTIFICATION_PARAMS_RULE_CONFIG: Final = [
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
]


def test_migrate_mixed_notification_parameters() -> None:
    value = migrate_parameters(MIXED_NOTIFICATION_PARAMS_RULE_CONFIG)
    expected = {
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
                    "description": "Migrated from notification rules #3, #4",
                    "comment": "Auto migrated on update",
                    "docu_url": "",
                },
                "parameter_properties": {"facility": 5, "remote": "1.1.1.1"},
            }
        },
    }
    assert value == expected


def test_migrate_mixed_notification_plugins() -> None:
    migrate_parameters(MIXED_NOTIFICATION_PARAMS_RULE_CONFIG)

    value = [rule["notify_plugin"] for rule in NotificationRuleConfigFile().load_for_reading()]
    expected = [
        ("opsgenie_issues", "<uuid-1>"),
        ("mail", "<uuid-2>"),
        ("mail", "<uuid-3>"),
        ("mkeventd", "<uuid-4>"),
        ("mkeventd", "<uuid-4>"),
        ("mkeventd", None),
    ]

    assert all(got == want for got, want in zip(value, expected))


def test_migrate_with_already_migrated_rules() -> None:
    # Note: `None` and UUID are considered migrated.
    config = [
        EventRuleFactory.build(notify_plugin=("mail", "2e61d376-7226-42b8-a98c-d41dc5585bcf")),
        EventRuleFactory.build(notify_plugin=("mail", None)),
    ]
    assert migrate_parameters(config) == {}


def test_migrate_with_partially_migrated_rules() -> None:
    config = [
        EventRuleFactory.build(notify_plugin=("mail", "2e61d376-7226-42b8-a98c-d41dc5585bcf")),
        ASCII_RULE_CONFIG[0],  # rule to migrate
    ]
    assert migrate_parameters(config)


@pytest.mark.xfail(
    reason="Need to find a way create a notification parameter as a fixture.",
    raises=cmk.gui.exceptions.MKUserError,
)
def test_migrate_with_list_parameter_for_custom_plugin_does_not_raise_validation_error() -> None:
    config = [EventRuleFactory.build(notify_plugin=("custom_pigeon_notifier", ["foo", "bar"]))]
    assert migrate_parameters(config)
