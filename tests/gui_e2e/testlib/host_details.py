#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class Property(Enum):
    def __init__(self, ui_name: str, api_name: str):
        self._ui_name = ui_name
        self._api_name = api_name

    def __str__(self) -> str:
        return str(self._ui_name)

    @property
    def api_name(self) -> str:
        return str(self._api_name)


class SNMP(Property):
    """Represent SNMP options.

    On UI: 'Properties of host' / 'Add host' page -> 'Monitoring agents' section -> 'SNMP' field.
    """

    no_snmp = ("No SNMP", "no-snmp")
    snmp_v2_v3 = ("SNMP v2 or v3", "snmp-v2")
    snmp_v1 = ("SNMP v1", "snmp-v1")


class AgentAndApiIntegration(Property):
    """Represent agent and API integration options.

    On UI: 'Properties of host' / 'Add host' page -> 'Monitoring agents' section ->
    'Checkmk agent / API integrations' field.
    """

    cmk_agent = ("API integrations if configured, else Checkmk agent", "cmk-agent")
    all_agents = ("Configured API integrations and Checkmk agent", "all-agents")
    special_agents = ("Configured API integrations, no Checkmk agent", "special-agents")
    no_agent = ("No API integrations, no Checkmk agent", "no-agent")


class AddressFamily(Property):
    """Represent IP address families.

    On UI: 'Properties of host' / 'Add host' page -> 'Network address' section ->
    'IP address family' field.
    """

    ip_v4_only = ("IPv4 only", "ip-v4-only")
    ip_v6_only = ("IPv6 only", "ip-v6-only")
    ip_v4v6 = ("IPv4 / IPv6 dual - stack", "ip-v4v6")
    no_ip = ("No IP", "no-ip")


class HostDetails:
    def __init__(
        self,
        name: str,
        ip: str | None = None,
        site: str | None = None,
        agent_and_api_integration: AgentAndApiIntegration | None = None,
        address_family: AddressFamily | None = None,
        labels: dict | None = None,
        snmp: SNMP | None = None,
    ) -> None:
        self.name = name
        self.ip = ip
        self.site = site
        self._agent_and_api_integration = agent_and_api_integration
        self._address_family = address_family
        self.labels = labels
        self._snmp = snmp

    @property
    def snmp(self) -> str | None:
        return str(self._snmp) if self._snmp else None

    @snmp.setter
    def snmp(self, value: SNMP) -> None:
        self._snmp = value

    @property
    def agent_and_api_integration(self) -> str | None:
        return str(self._agent_and_api_integration) if self._agent_and_api_integration else None

    @agent_and_api_integration.setter
    def agent_and_api_integration(self, value: AgentAndApiIntegration) -> None:
        self._agent_and_api_integration = value

    @property
    def address_family(self) -> str | None:
        return str(self._address_family) if self._address_family else None

    @address_family.setter
    def address_family(self, value: AddressFamily) -> None:
        self._address_family = value

    def rest_api_attributes(self) -> dict[str, str]:
        """Return host attributes as a dictionary.

        Convert host attributes (except for 'name') into a dictionary,
        which can be used for creating the host through the REST API.
        """
        attr_to_api_request_keys = {
            "ip": "ipaddress",
            "site": "site",
            "_agent_and_api_integration": "tag_agent",
            "_address_family": "tag_address_family",
            "labels": "labels",
            "_snmp": "tag_snmp_ds",
        }

        result = {}
        for key, value in vars(self).items():
            if value is not None and key in attr_to_api_request_keys:
                if isinstance(value, Property):
                    result[attr_to_api_request_keys[key]] = value.api_name
                else:
                    result[attr_to_api_request_keys[key]] = value
        return result
