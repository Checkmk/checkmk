#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.gui.watolib.automation_commands import automation_command_registry


@pytest.mark.usefixtures("load_gui_plugins")
def test_registered_automation_commands() -> None:
    expected_automation_commands = [
        "activate-changes",
        "agent-download-token-create",
        "agent-registration-token-create",
        "check-analyze-config",
        "checkmk-remote-automation-get-status",
        "checkmk-remote-automation-start",
        "clear-site-changes",
        "create-broker-certs",
        "diagnostics-dump-get-file",
        "diagnostics-dump-os-walk",
        "discovered-host-label-sync",
        "fetch-agent-output-get-file",
        "fetch-agent-output-get-status",
        "fetch-agent-output-start",
        "fetch-background-job-snapshot",
        "fetch-quick-setup-stage-action-result",
        "finalize-site-ca-certificate-rotation",
        "get-agent-receiver-port",
        "get-config-sync-state",
        "hosts-for-auto-removal",
        "kubernetes-push-registration",
        "network-scan",
        "notification-test",
        "ping",
        "push-profiles",
        "receive-config-sync",
        "remove-tls-registration",
        "rename-hosts-uuid-link",
        "service-discovery-job",
        "service-discovery-job-snapshot",
        "site-certificate-rotation",
        "stage-site-ca-certificate-rotation",
        "start-quick-setup-stage-action",
        "store-broker-certs",
        "sync-remote-site",
    ]

    registered = sorted(automation_command_registry.keys())
    assert registered == sorted(expected_automation_commands)
