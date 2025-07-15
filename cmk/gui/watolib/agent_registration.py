#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Sequence

from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName

from cmk.utils.agent_registration import get_uuid_link_manager

from cmk.gui.http import request
from cmk.gui.log import logger
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import (
    do_remote_automation,
    LocalAutomationConfig,
    RemoteAutomationConfig,
)


def remove_tls_registration(
    hosts_by_site: Sequence[
        tuple[LocalAutomationConfig | RemoteAutomationConfig, Sequence[HostName]]
    ],
    *,
    debug: bool,
) -> None:
    for automation_config, host_names in hosts_by_site:
        if not host_names:
            continue

        if isinstance(automation_config, LocalAutomationConfig):
            _remove_tls_registration(host_names)
            continue

        do_remote_automation(
            automation_config,
            "remove-tls-registration",
            [("host_names", json.dumps(host_names))],
            debug=debug,
        )


class AutomationRemoveTLSRegistration(AutomationCommand[Sequence[HostName]]):
    def command_name(self) -> str:
        return "remove-tls-registration"

    def get_request(self) -> Sequence[HostName]:
        value = json.loads(request.get_ascii_input_mandatory("host_names", "[]"))
        if not isinstance(value, list):
            raise MKGeneralException(f"Not a list of host names: {value}")
        valid_hostnames, invalid_hostnames = [], []
        for hostname in value:
            try:
                valid_hostnames.append(HostName(hostname))
            except ValueError:
                invalid_hostnames.append(hostname)
        if invalid_hostnames:
            logger.warning(
                "remove-tls-registration called with the following invalid host names: %s",
                ", ".join(invalid_hostnames),
            )
        return valid_hostnames

    def execute(self, api_request: Sequence[HostName]) -> None:
        _remove_tls_registration(api_request)


def _remove_tls_registration(host_names: Sequence[HostName]) -> None:
    get_uuid_link_manager().unlink(host_names)
