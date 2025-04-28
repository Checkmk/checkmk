#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.plugins.azure.rulesets.azure import CCE_AZURE_SERVICES, RAW_AZURE_SERVICES
from cmk.plugins.azure.special_agent.agent_azure import ALL_METRICS


def test_all_services_present_in_gui():
    # Test that all services fetched by the agent are selectable in the GUI.
    # This is to avoid to forget to add a new service in the GUI when adding it to the agent.
    all_gui_services = [
        service_id for service_id, _service_name in RAW_AZURE_SERVICES + CCE_AZURE_SERVICES
    ]
    all_agent_metrics = [metric_id for metric_id, metric_data in ALL_METRICS.items()]
    # "users_count", "ad_connect", "usage_details" and "Microsoft.Compute/virtualMachines" are
    # handled in a custom way by the agent so we are manually adding them
    all_agent_services = [
        "users_count",
        "ad_connect",
        "app_registrations",
        "usage_details",
        "Microsoft.RecoveryServices/vaults",
        *all_agent_metrics,
    ]
    assert sorted(all_gui_services) == sorted(all_agent_services)
