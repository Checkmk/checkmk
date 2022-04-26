#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from typing import Mapping, Sequence

from livestatus import SiteId

import cmk.utils.regex
from cmk.utils.agent_registration import get_uuid_link_manager
from cmk.utils.type_defs import HostName

from cmk.gui.exceptions import MKGeneralException
from cmk.gui.globals import request
from cmk.gui.sites import get_site_config, site_is_local
from cmk.gui.watolib import automation_command_registry, AutomationCommand, do_remote_automation


def remove_tls_registration(hosts_by_site: Mapping[SiteId, Sequence[HostName]]) -> None:
    for site_id, host_names in hosts_by_site.items():
        if not host_names:
            continue

        if site_is_local(site_id):
            _remove_tls_registration(host_names)
            return

        do_remote_automation(
            get_site_config(site_id),
            "remove-tls-registration",
            [("host_names", json.dumps(host_names))],
        )


@automation_command_registry.register
class AutomationRemoveTLSRegistration(AutomationCommand):
    def command_name(self):
        return "remove-tls-registration"

    def get_request(self) -> Sequence[HostName]:
        raw_host_names = json.loads(request.get_ascii_input_mandatory("host_names", "[]"))
        return [
            HostName(raw_host_name)
            for raw_host_name in raw_host_names
            if self._validate_host_name(raw_host_name)
        ]

    @staticmethod
    def _validate_host_name(raw_host_name: str) -> None:
        if cmk.utils.regex.regex(cmk.utils.regex.REGEX_HOST_NAME).match(str(raw_host_name)):
            return
        raise MKGeneralException("Invalid host name %s" % raw_host_name)

    def execute(self, api_request: Sequence[HostName]) -> None:
        _remove_tls_registration(api_request)


def _remove_tls_registration(host_names: Sequence[HostName]) -> None:
    get_uuid_link_manager().unlink_sources(host_names)
