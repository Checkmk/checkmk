#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest
from polyfactory.factories import TypedDictFactory
from pytest import MonkeyPatch

from cmk.utils.notify_types import (
    AsciiMailPluginModel,
    CiscoPluginModel,
    EventRule,
    MailPluginModel,
    MKEventdPluginModel,
    NotificationParameterID,
    NotificationParameterSpecs,
    OpsGenieIssuesPluginModel,
    SpectrumPluginModel,
)

from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib import sample_config
from cmk.gui.watolib.notifications import (
    NotificationParameterConfigFile,
    NotificationRuleConfigFile,
)

from cmk.update_config.plugins.actions.migrate_notification_parameters import (
    MigrateNotificationParameters,
)


class EventRuleFactory(TypedDictFactory[EventRule]): ...


PARAMETER_UUID: NotificationParameterID = sample_config.new_notification_parameter_id()


@pytest.mark.parametrize(
    ["rule_config", "notification_parameter"],
    [
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "spectrum",
                        SpectrumPluginModel(
                            destination="1.1.1.1",
                            community="gaergerag",
                            baseoid="1.3.6.1.4.1.1234",
                        ),
                    ),
                )
            ],
            {
                "spectrum": {
                    str(PARAMETER_UUID): {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "destination": "1.1.1.1",
                            "community": "gaergerag",
                            "baseoid": "1.3.6.1.4.1.1234",
                        },
                    }
                }
            },
            id="Spectrum",
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
                    str(PARAMETER_UUID): {
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
            id="ASCII Email",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "cisco_webex_teams",
                        CiscoPluginModel(
                            webhook_url=("webhook_url", "https://www.mywebhook.url"),
                            url_prefix={"automatic": "https"},
                            ignore_ssl=True,
                            proxy_url=("no_proxy", None),
                        ),
                    ),
                )
            ],
            {
                "cisco_webex_teams": {
                    str(PARAMETER_UUID): {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "webhook_url": ("webhook_url", "https://www.mywebhook.url"),
                            "url_prefix": {"automatic": "https"},
                            "ignore_ssl": True,
                            "proxy_url": ("no_proxy", None),
                        },
                    }
                }
            },
            id="Cisco Webex Teams",
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
                    str(PARAMETER_UUID): {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {"facility": 5, "remote": "1.1.1.1"},
                    }
                }
            },
            id="Forward notification to Event Console",
        ),
        pytest.param(
            [
                EventRuleFactory.build(
                    notify_plugin=(
                        "opsgenie_issues",
                        OpsGenieIssuesPluginModel(
                            password=("password", "zhfziuofoziudfozuidouizd"),
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
                                "url_prefix": {"automatic": "https"},
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
                                "url_prefix": {"automatic": "https"},
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
            ],
            {
                "opsgenie_issues": {
                    str(PARAMETER_UUID): {
                        "general": {
                            "description": "Migrated from notification rule #0",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "password": ("password", "zhfziuofoziudfozuidouizd"),
                            "host_desc": "Host: $HOSTNAME$\nEvent:    $EVENT_TXT$\nOutput:   $HOSTOUTPUT$\nPerfdata: $HOSTPERFDATA$\n$LONGHOSTOUTPUT$\n",
                            "actions": ["MY_ACTION"],
                            "tags": ["MY_TAG"],
                        },
                    }
                },
                "mail": {
                    str(PARAMETER_UUID): {
                        "general": {
                            "description": "Migrated from notification rule #1",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "url_prefix": {"automatic": "https"},
                            "disable_multiplexing": True,
                        },
                    },
                    str(PARAMETER_UUID): {
                        "general": {
                            "description": "Migrated from notification rule #2",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {
                            "url_prefix": {"automatic": "https"},
                            "from": {"address": "from@me.com"},
                            "disable_multiplexing": True,
                        },
                    },
                },
                "mkeventd": {
                    str(PARAMETER_UUID): {
                        "general": {
                            "description": "Migrated from notification rule #3",
                            "comment": "Auto migrated on update",
                            "docu_url": "",
                        },
                        "parameter_properties": {"facility": 5, "remote": "1.1.1.1"},
                    }
                },
            },
            id="Mixed notification rules",
        ),
    ],
)
def test_migrate_notification_parameters(
    rule_config: list[EventRule],
    notification_parameter: NotificationParameterSpecs,
    monkeypatch: MonkeyPatch,
) -> None:
    # TODO How to handle multiple UUIDs?
    monkeypatch.setattr(
        sample_config,
        "new_notification_parameter_id",
        lambda: str(PARAMETER_UUID),
    )

    with gui_context():
        NotificationRuleConfigFile().save(rule_config)

        MigrateNotificationParameters(
            name="migrate_notification_parameters",
            title="Migrate notification parameters",
            sort_index=50,
        )(logging.getLogger())

    assert NotificationParameterConfigFile().load_for_reading() == notification_parameter
