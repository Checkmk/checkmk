#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from uuid import uuid4

import pytest

from cmk.utils.notify_types import (
    MailPluginModel,
    NotificationParameterID,
    SpectrumPluginModel,
)

from cmk.gui.utils.script_helpers import application_and_request_context
from cmk.gui.watolib.notifications import (
    NotificationParameterConfigFile,
)

from cmk.update_config.plugins.actions.cleanup_duplicate_notification_parameters import (
    CleanupDuplicateNotificationParameters,
)

TEST_DATA = [
    (
        {
            "mail": {
                NotificationParameterID(str(uuid4())): {
                    "general": {
                        "description": "Default mail notification parameters",
                        "comment": "",
                        "docu_url": "",
                    },
                    "parameter_properties": MailPluginModel(
                        {
                            "url_prefix": ("automatic_https", None),
                            "from": {"address": "from@me.com"},
                            "disable_multiplexing": True,
                        }
                    ),
                },
                NotificationParameterID(str(uuid4())): {
                    "general": {
                        "description": "Default mail notification parameters",
                        "comment": "",
                        "docu_url": "",
                    },
                    "parameter_properties": MailPluginModel(
                        {
                            "url_prefix": ("automatic_https", None),
                            "from": {"address": "from@me.com"},
                            "disable_multiplexing": True,
                        }
                    ),
                },
                NotificationParameterID(str(uuid4())): {
                    "general": {
                        "description": "Mail notification parameter",
                        "comment": "",
                        "docu_url": "",
                    },
                    "parameter_properties": MailPluginModel(
                        {
                            "url_prefix": ("automatic_http", None),
                            "from": {"address": "from@me.com"},
                        }
                    ),
                },
            },
        },
        "mail",
        2,
    ),
    (
        {
            "servicenow": {
                NotificationParameterID("98c27fbe-872f-42db-a1d3-a92ad69b3dbe"): {
                    "general": {
                        "comment": "2025-09-17 "
                        "DESLONEU:Host "
                        "and "
                        "all "
                        "services "
                        "without "
                        "special "
                        "servicegroups\n",
                        "description": "Test on DEV Host/services expl. IDs",
                        "docu_url": "",
                    },
                    "parameter_properties": {
                        "auth": (
                            "auth_basic",
                            {
                                "password": (
                                    "cmk_postprocessed",
                                    "explicit_password",
                                    (
                                        "uuidc8dac82d-f028-4d6d-9b9a-ad05eff3cef9",
                                        "@D]QzZo5_mX9DXFz(keIe0-i#EzP_MM};o0!p_r-%;#PlM}e?O.51e2eQ$Y1anB?T4(.;YOKx<m4w1yBDcO9P_JICpv^X8@Bj$:E",
                                    ),
                                ),
                                "username": "sn_service_checkmk",
                            },
                        ),
                        "mgmt_type": (
                            "incident",
                            {
                                "caller": "sn_service_checkmk",
                                "custom_fields": [
                                    {
                                        "name": "assignment_group",
                                        "value": "bf7652df2b6a2610152ff373ce91bfa6",
                                    },
                                    {
                                        "name": "contact_type",
                                        "value": "event",
                                    },
                                ],
                                "impact": "low",
                                "recovery_state": {"start": ("integer", 6)},
                                "urgency": "low",
                            },
                        ),
                        "url": "https://durrdev.service-now.com",
                    },
                },
                NotificationParameterID("98c27fbe-872f-42db-a1d3-a92ad69b3dbe"): {
                    "general": {
                        "comment": "2025-09-17 "
                        "DESLONEU:Host "
                        "and "
                        "all "
                        "services "
                        "without "
                        "special "
                        "servicegroups\n",
                        "description": "Test on DEV Host/services expl. IDs",
                        "docu_url": "",
                    },
                    "parameter_properties": {
                        "auth": (
                            "auth_basic",
                            {
                                "password": (
                                    "cmk_postprocessed",
                                    "explicit_password",
                                    (
                                        "uuidc8dac82d-f028-4d6d-9b9a-ad05eff3cef9",
                                        "@D]QzZo5_mX9DXFz(keIe0-i#EzP_MM};o0!p_r-%;#PlM}e?O.51e2eQ$Y1anB?T4(.;YOKx<m4w1yBDcO9P_JICpv^X8@Bj$:E",
                                    ),
                                ),
                                "username": "sn_service_checkmk",
                            },
                        ),
                        "mgmt_type": (
                            "incident",
                            {
                                "caller": "sn_service_checkmk",
                                "custom_fields": [
                                    {
                                        "name": "assignment_group",
                                        "value": "bf7652df2b6a2610152ff373ce91bfa6",
                                    },
                                    {
                                        "name": "contact_type",
                                        "value": "event",
                                    },
                                ],
                                "impact": "low",
                                "recovery_state": {"start": ("integer", 6)},
                                "urgency": "low",
                            },
                        ),
                        "url": "https://durrdev.service-now.com",
                    },
                },
            }
        },
        "servicenow",
        1,
    ),
    (
        {
            "spectrum": {
                NotificationParameterID("87c27fbe-872f-42db-a1d3-a92ad69b3dbe"): {
                    "general": {
                        "description": "Migrated from notification rule #0",
                        "comment": "Auto migrated on update",
                        "docu_url": "",
                    },
                    "parameter_properties": SpectrumPluginModel(
                        {
                            "destination": "1.1.1.1",
                            "community": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<migrate-uuid>", "gaergerag"),
                            ),
                            "baseoid": "1.3.6.1.4.1.1234",
                        },
                    ),
                },
                NotificationParameterID("86c27fbe-872f-42db-a1d3-a92ad69b3dbe"): {
                    "general": {
                        "description": "Migrated from notification rule #1",
                        "comment": "Auto migrated on update",
                        "docu_url": "",
                    },
                    "parameter_properties": SpectrumPluginModel(
                        {
                            "destination": "1.1.1.1",
                            "community": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<migrate-uuid>", "gaergerag"),
                            ),
                            "baseoid": "1.3.6.1.4.1.1234",
                        },
                    ),
                },
                NotificationParameterID("85c27fbe-872f-42db-a1d3-a92ad69b3dbe"): {
                    "general": {
                        "description": "Migrated from notification rule #2",
                        "comment": "Auto migrated on update",
                        "docu_url": "",
                    },
                    "parameter_properties": SpectrumPluginModel(
                        {
                            "destination": "1.1.1.1",
                            "community": (
                                "cmk_postprocessed",
                                "explicit_password",
                                ("<migrate-uuid>", "gaergerag"),
                            ),
                            "baseoid": "1.3.6.1.4.1.1234",
                        },
                    ),
                },
            },
        },
        "spectrum",
        3,
    ),
]


@pytest.mark.parametrize(
    "test_params, param_name, expected_num_after_cleanup",
    TEST_DATA,
    ids=["mail_duplicate_cleanup", "servicenow_duplicate_cleanup", "spectrum_duplicate_cleanup"],
)
def test_cleanup_duplicate_notification_parameters(
    test_params: dict, param_name: str, expected_num_after_cleanup: int
) -> None:
    with application_and_request_context():
        NotificationParameterConfigFile().save(test_params)
        CleanupDuplicateNotificationParameters(
            name="cleanup_duplicate_notification_parameters",
            title="Cleanup duplicate notification parameters",
            sort_index=51,
        )(logging.getLogger())

        params_after_update = NotificationParameterConfigFile().load_for_reading()
        assert len(params_after_update[param_name]) == expected_num_after_cleanup
