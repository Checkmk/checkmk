#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Mapping, Sequence

from livestatus import SiteId

from cmk.utils.agent_registration import get_uuid_link_manager
from cmk.utils.hostaddress import HostAddress, HostName

from cmk.gui.config import active_config
from cmk.gui.http import request
from cmk.gui.log import logger
from cmk.gui.site_config import get_site_config, site_is_local
from cmk.gui.watolib.automation_commands import AutomationCommand
from cmk.gui.watolib.automations import do_remote_automation


def remove_tls_registration(hosts_by_site: Mapping[SiteId, Sequence[HostName]]) -> None:
    for site_id, host_names in hosts_by_site.items():
        if not host_names:
            continue

        if site_is_local(active_config, site_id):
            _remove_tls_registration(host_names)
            return

        do_remote_automation(
            get_site_config(active_config, site_id),
            "remove-tls-registration",
            [("host_names", json.dumps(host_names))],
        )


class AutomationRemoveTLSRegistration(AutomationCommand[Sequence[HostName]]):
    def command_name(self) -> str:
        return "remove-tls-registration"

    def get_request(self) -> Sequence[HostName]:
        return json.loads(request.get_ascii_input_mandatory("host_names", "[]"))

    def execute(self, api_request: Sequence[HostName]) -> None:
        valid_hosts = [hostname for hostname in api_request if HostAddress.is_valid(hostname)]
        if len(valid_hosts) < len(api_request):
            logger.warning(
                "remove-tls-registration called with the following invalid host names: %s",
                ", ".join(
                    hostname for hostname in api_request if not HostAddress.is_valid(hostname)
                ),
            )
        _remove_tls_registration(valid_hosts)


def _remove_tls_registration(host_names: Sequence[HostName]) -> None:
    get_uuid_link_manager().unlink(host_names)
