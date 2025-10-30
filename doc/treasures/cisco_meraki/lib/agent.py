#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# enhancements by thl-cmk[at]outlook[dot]com, https://thl-cmk.hopto.org
# - moved section name to utils/cisco_meraki.py (reuse with WATO)
# - added option to adjust piggyback names with prefix, suffix, upper/lower case
# - added section _SEC_NAME_DEVICE_UPLINKS_INFO (inventory of uplink information)
# - added section _SEC_NAME_APPLIANCE_UPLINKS (status and usage of appliance uplinks)
# - updated Cisco meraki dashboard SDK from version 1.27.0 to 1.38.0 (needed for appliance uplinks)
# - added section _SEC_NAME_APPLIANCE_VPNS (status and usage of appliance uplinks)
#
# 2023-11-09: removed nonworking original datacache (cleanup before reimplementing)
#             added new Cacheing code based on AWS agent - works this time ;-)
# 2023-11-10: a bit of cleanup, removed oneliner API calls, moved to the calling function
#             moved add networks to MerakiOrganisation.query
#             added cisco_meraki_org_networks output section (base to create networks inventory)
# 2023-10-11: fixed _get_device_piggyback drop hosts without names -> can be changed to use serial instead
#             fixed in device info drop hosts without names -> can be changed to use serial instead
#             fixed do nit access organisations where the API is not enabled
#             added organisation overview section _SEC_NAME_ORGANISATIONS to discover orgs with API not enabled
# 2023-11-12: added --no-cache option
#             re-added appliance uplink usage
# 2023-11-13: optimized API request: don't ask for device information's if there are no devices in an organisation
#             API requests by product type: don't ask for products that are not available in the organisation
# 2023-11-17: changed to always get organisations instead of organisation_by_id
# 2023-11-18: changed from include sections to exclude sections
# 2023-11-19: changed if no hostname (piggyback) to use serial+device type
# 2024-04-05: fixed min SDK version for MerakiGetOrganizationApplianceUplinksUsageByNetwork and
#                                       MerakiGetOrganizationWirelessDevicesEthernetStatuses
# 2024-05-12: added MerakiGetOrganizationApiRequestsOverviewResponseCodesByInterval and
#             MerakiGetOrganizationSwitchPortsStatusesBySwitch (Early Access, not in SDK)
# 2024-05-17: fixed crash on missing network id (KeyError)
#             added basic proxy support for Early Access requests
# 2024-05-19: fixed proxy usage (NO_PROXY, FROM_ENVIRONMENT)
# 2024-05-20: made appliance uplinks usage user selectable
#             made API requests per org user selectable
# 2024-06-23: added cache time per section -> not nice but should work.
# 2024-09-12: added version check for min. Meraki SDK version
# 2024-09-15: fixed MerakiGetOrganizationSwitchPortsStatusesBySwitch -> return only list of switches
# 2024-11-16: fixed crash on missing items in MerakiGetOrganizationSwitchPortsStatusesBySwitch (ThX to Stephan Bergfeld)
# 2024-11-23: added appliance port api call -> not yet active
# 2024-12-13: fixed crash in SwitchPortStatus if response has no data (>Response [503}>)
# 2025-01-04: added "use network as prefix" option
# 2025-03-03: completely removed APPLIANCE_PORT section -> fixed per section cache
#             removed lldp_cdp section
# 2025-03-30: moved all components to cmk_addons/plugins/meraki -> in the legacy directory's and under cmk/plugins are only dummy's left
# 2025-05-30: added support for Meraki Cloud regions (World, Canada, China, India, US Gov)
# 2024-06-14: added __init__.py files to enable shadowing in CMK2.4 (https://forum.checkmk.com/t/can-not-shadow-built-in-agent-ruleset-meraki-extended-agent/54244/7)
# 2025-06-22: updated Meraki SDK to v2.0.3

# Deprecation information
# https://developer.cisco.com/meraki/api-v1/deprecated-operations/#deprecated-operations
#

# ToDo: create inventory from Networks, is per organisation, not sure where/how to put this in the inventory
# ToDo: list Connected Datacenters like Umbrella https://developer.cisco.com/meraki/api-v1/list-data-centers/
# ToDo: https://developer.cisco.com/meraki/api-v1/list-tunnels/
# ToDo: https://developer.cisco.com/meraki/api-v1/get-organization-wireless-clients-overview-by-device/
# ToDo: https://developer.cisco.com/meraki/api-v1/get-device-lldp-cdp/

# if the following is available (right now only with early access enabled)
# ToDO: https://developer.cisco.com/meraki/api-v1/get-organization-switch-ports-statuses-by-switch/ # (done)
# ToDo: https://developer.cisco.com/meraki/api-v1/get-organization-switch-ports-overview/
# TODo: https://developer.cisco.com/meraki/api-v1/get-organization-certificates/
# ToDo: https://developer.cisco.com/meraki/api-v1/api-reference-early-access-api-platform-configure-firmwareupgrades-get-network-firmware-upgrades/

# ToDo: check proxy handling FROM_ENVIRONMENT, NO_PROXY, GLOBAL_SETTINGS/EXPLICIT, NONE
#
# Meraki SDK on GitHub: https://github.com/meraki/dashboard-api-python
#

from __future__ import annotations

from argparse import Namespace
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from enum import auto, Enum
from json import JSONDecodeError
from logging import getLogger
from os import environ
from pathlib import Path
from requests import request, RequestException
from time import strftime, gmtime, time as now_time
from time import time_ns
from typing import Final, TypedDict, Any, List

import meraki  # type: ignore[import]

from cmk.utils.paths import tmp_dir

from cmk.special_agents.v0_unstable.agent_common import (
    ConditionalPiggybackSection,
    SectionWriter,
    special_agent_main,
)
from cmk.special_agents.v0_unstable.argument_parsing import create_default_argument_parser  # , Args
from cmk.special_agents.v0_unstable.misc import DataCache

from cmk_addons.plugins.meraki.lib.utils import (
    MerakiNetwork,

    # parameter names
    SEC_NAME_APPLIANCE_UPLINKS,
    SEC_NAME_APPLIANCE_UPLINKS_USAGE,
    SEC_NAME_APPLIANCE_VPNS,
    SEC_NAME_APPLIANCE_PERFORMANCE,
    SEC_NAME_CELLULAR_UPLINKS,
    SEC_NAME_DEVICE_INFO,
    SEC_NAME_DEVICE_STATUSES,
    SEC_NAME_DEVICE_UPLINKS_INFO,
    SEC_NAME_LICENSES_OVERVIEW,
    SEC_NAME_NETWORKS,
    SEC_NAME_ORGANISATIONS,
    SEC_NAME_ORG_API_REQUESTS,
    SEC_NAME_SENSOR_READINGS,
    SEC_NAME_SWITCH_PORTS_STATUSES,
    SEC_NAME_WIRELESS_DEVICE_STATUS,
    SEC_NAME_WIRELESS_ETHERNET_STATUSES,
    # SEC_NAME_DEVICE_LLDP_CDP,
    # Early Access
    SEC_NAME_ORG_SWITCH_PORTS_STATUSES,

    # api cache defaults per section
    SEC_CACHE_APPLIANCE_PERFORMANCE,
    SEC_CACHE_APPLIANCE_UPLINKS_USAGE,
    SEC_CACHE_APPLIANCE_UPLINKS,
    SEC_CACHE_APPLIANCE_VPNS,
    SEC_CACHE_CELLULAR_UPLINKS,
    SEC_CACHE_DEVICE_INFO,
    SEC_CACHE_DEVICE_STATUSES,
    SEC_CACHE_DEVICE_UPLINKS_INFO,
    SEC_CACHE_LICENSES_OVERVIEW,
    SEC_CACHE_NETWORKS,
    SEC_CACHE_ORG_API_REQUESTS,
    SEC_CACHE_ORG_SWITCH_PORTS_STATUSES,
    SEC_CACHE_ORGANISATIONS,
    SEC_CACHE_SENSOR_READINGS,
    SEC_CACHE_SWITCH_PORTS_STATUSES,
    SEC_CACHE_WIRELESS_DEVICE_STATUS,
    SEC_CACHE_WIRELESS_ETHERNET_STATUSES,
)

MERAKI_REGIONS = {
    'default': 'https://api.meraki.com/api/v1',
    'canada': 'https://api.meraki.ca/api/v1',
    'china': 'https://api.meraki.cn/api/v1',
    'india': 'https://api.meraki.in/api/v1',
    'us_gov':'https://api.gov-meraki.com/api/'
}

MERAKI_SDK_MIN_VERSION: Final = '1.46.0'

LOGGER = getLogger('agent_cisco_meraki')

API_NAME_API: Final = 'api'
API_NAME_DEVICE_NAME: Final = 'name'
API_NAME_DEVICE_PRODUCT_TYPE: Final = 'productType'
API_NAME_DEVICE_SERIAL: Final = 'serial'
API_NAME_DEVICE_TYPE_APPLIANCE: Final = 'appliance'
API_NAME_DEVICE_TYPE_CAMERA: Final = 'camera'
API_NAME_DEVICE_TYPE_CELLULAR: Final = 'cellularGateway'
API_NAME_DEVICE_TYPE_SENSOR: Final = 'sensor'
API_NAME_DEVICE_TYPE_SWITCH: Final = 'switch'
API_NAME_DEVICE_TYPE_WIRELESS: Final = 'wireless'
API_NAME_ENABLED: Final = 'enabled'
API_NAME_NETWORK_ID: Final = 'networkId'
API_NAME_ORGANISATION_ID: Final = 'id'
API_NAME_ORGANISATION_NAME: Final = 'name'

# map section parameter name to python name (do we really need this, why not use the name ('-' -> '_')?
SECTION_NAME_MAP = {
    SEC_NAME_APPLIANCE_UPLINKS: 'appliance_uplinks',
    SEC_NAME_APPLIANCE_UPLINKS_USAGE: 'appliance_uplinks_usage',
    SEC_NAME_APPLIANCE_VPNS: 'appliance_vpns',
    SEC_NAME_APPLIANCE_PERFORMANCE: 'appliance_performance',
    SEC_NAME_CELLULAR_UPLINKS: 'cellular_uplinks',
    SEC_NAME_DEVICE_INFO: 'device_info',
    SEC_NAME_DEVICE_STATUSES: 'device_status',
    SEC_NAME_DEVICE_UPLINKS_INFO: 'device_uplinks_info',
    SEC_NAME_LICENSES_OVERVIEW: 'licenses_overview',
    SEC_NAME_NETWORKS: 'networks',
    SEC_NAME_ORGANISATIONS: 'organisations',
    SEC_NAME_ORG_API_REQUESTS: 'api_requests_by_organization',
    SEC_NAME_SENSOR_READINGS: 'sensor_readings',
    SEC_NAME_SWITCH_PORTS_STATUSES: 'switch_ports_statuses',
    SEC_NAME_WIRELESS_DEVICE_STATUS: 'wireless_device_status',
    SEC_NAME_WIRELESS_ETHERNET_STATUSES: 'wireless_ethernet_statuses',
    # SEC_NAME_DEVICE_LLDP_CDP: 'device_lldp_cdp',
    # Early Access
    SEC_NAME_ORG_SWITCH_PORTS_STATUSES: 'org_switch_ports_statuses',
}

# MIN_CACHE_INTERVAL = 300
# RANDOM_CACHE_INTERVAL = 300

MerakiCacheFilePath = Path(tmp_dir) / 'agents' / 'agent_cisco_meraki'
MerakiAPIData = Mapping[str, object]


#   .--dashboard-----------------------------------------------------------.
#   |              _           _     _                         _           |
#   |           __| | __ _ ___| |__ | |__   ___   __ _ _ __ __| |          |
#   |          / _` |/ _` / __| '_ \| '_ \ / _ \ / _` | '__/ _` |          |
#   |         | (_| | (_| \__ \ | | | |_) | (_) | (_| | | | (_| |          |
#   |          \__,_|\__,_|___/_| |_|_.__/ \___/ \__,_|_|  \__,_|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def configure_meraki_dashboard(
    api_key: str,
    debug: bool,
    region: str,
    proxy: str | None,
) -> meraki.DashboardAPI:
    return meraki.DashboardAPI(
        api_key=api_key,
        print_console=True,
        output_log=False,
        suppress_logging=not debug,
        requests_proxy=proxy,
        base_url=region,
    )


# .
#   .--section-------------------------------------------------------------.
#   |                                 _   _                                |
#   |                   ___  ___  ___| |_(_) ___  _ __                     |
#   |                  / __|/ _ \/ __| __| |/ _ \| '_ \                    |
#   |                  \__ \  __/ (__| |_| | (_) | | | |                   |
#   |                  |___/\___|\___|\__|_|\___/|_| |_|                   |
#   |                                                                      |
#   '----------------------------------------------------------------------'

@dataclass(frozen=True)
class MerakiConfig:
    # section_names: Sequence[str]
    api_key: str  # needed for Early Access
    dashboard: meraki.DashboardAPI
    excluded_sections: Sequence[str]
    hostname: str
    net_id_as_prefix: bool
    org_id_as_prefix: bool
    proxy: str  # needed for Early Access
    timespan: int
    use_cache: bool
    cache_per_section: CachePerSection | None = None


class MerakiAPIDataSource(Enum):
    org = auto()


@dataclass(frozen=True)
class Section:
    api_data_source: MerakiAPIDataSource
    name: str
    data: MerakiAPIData
    piggyback: str | None = None

    def get_name(self) -> str:
        return '_'.join(['cisco_meraki', self.api_data_source.name, self.name])


class _Organisation(TypedDict):
    # See https://developer.cisco.com/meraki/api-v1/#!get-organizations
    # get the latest SDK: https://github.com/meraki/dashboard-api-python
    # if you want to extend this
    id: str
    name: str


# .
#   .--caches--------------------------------------------------------------.
#   |                                  _                                   |
#   |                    ___ __ _  ___| |__   ___  ___                     |
#   |                   / __/ _` |/ __| '_ \ / _ \/ __|                    |
#   |                  | (_| (_| | (__| | | |  __/\__ \                    |
#   |                   \___\__,_|\___|_| |_|\___||___/                    |
#   |                                                                      |
#   '----------------------------------------------------------------------'
#
# --\ DataCache
#   |
#   +--\ MerakiSection
#      |  - adds cache_interval = 86400
#      |  - adds get_validity_from_args = True
#      |
#      +--> MerakiGetOrganizations                          		           -> default 86400
#      |
#      +--\ MerakiSectionOrg
#      |  |  - adds org_id parameter
#      |  |
#      |  +--> MerakiGetOrganization				                           -> default 86400
#      |  +--> MerakiGetOrganizationApiRequestsOverviewResponseCodesByInterval -> Off, allways live data
#      |  +--> MerakiGetOrganizationLicensesOverview		                   -> default 86400
#      |  +--> MerakiGetOrganizationDevices				                       -> default 86400
#      |  +--> MerakiGetOrganizationNetworks			                       -> default 86400
#      |  +--> MerakiGetOrganizationDevicesStatuses			                   -> ex. 60+
#      |  +--> MerakiGetOrganizationDevicesUplinksAddressesByDevice	           -> ex. 60+
#      |  +--> MerakiGetOrganizationApplianceUplinkStatuses		               -> ex. 60+
#      |  +--> MerakiGetOrganizationApplianceUplinksUsageByNetwork	           -> no cache
#      |  +--> MerakiGetOrganizationApplianceVpnStatuses		               -> ex. 60+
#      |  +--> MerakiGetOrganizationSensorReadingsLatest		               -> ex. 60+
#      |  +--> MerakiGetOrganizationWirelessDevicesEthernetStatuses	           -> ex. 60+
#      |  +--> MerakiGetOrganizationCellularGatewayUplinkStatuses              -> ex. 60.
#      |  +--> MerakiGetOrganizationSwitchPortsStatusesBySwitch                -> ex. 60+
#      |
#      +--\ MerakiSectionSerial
#      |  |  - adds serial as parameter
#      |  |  - sets cache_interval = 60
#      |  |
#      |  +--> MerakiGetDeviceSwitchPortsStatuses 	                           -> default 60+
#      |  +--> MerakiGetDeviceWirelessStatus	                               -> default 60+
#      |  +--> MerakiGetDeviceAppliancePerformance
#      |  +--> MerakiGetDeviceLldpCdp
#      |
#      +--\ MerakiSectionNetwork
#         | - adds network id as parameter
#         | - sets cache_interval = 60
#         |
#         +--> MerakiGetNetworkAppliancePorts
#

class MerakiSection(DataCache):
    def __init__(
            self,
            config: MerakiConfig,
            cache_interval: int = 1140,
    ):
        self._config = config
        self._received_results = {}
        self._cache_dir = MerakiCacheFilePath / self._config.hostname
        self._cache_file = MerakiCacheFilePath / self._config.hostname / self.name
        self._cache_interval = cache_interval * 60
        super().__init__(self._cache_dir, self.name)

    @property
    def name(self):
        return 'meraki_section'

    @property
    def cache_interval(self):
        return self._cache_interval

    def get_validity_from_args(self, *args: Any) -> bool:
        # always True, for now there are no changing arguments, related to the cache
        return True


class MerakiSectionOrg(MerakiSection):
    def __init__(
            self,
            config: MerakiConfig,
            org_id: str,
            cache_interval: int = 1140,
    ):
        self._org_id = org_id
        super().__init__(config=config, cache_interval=cache_interval)


class MerakiSectionSerial(MerakiSection):
    def __init__(
            self,
            config: MerakiConfig,
            serial: str,
            cache_interval: int = 1,
    ):
        self._serial = serial
        super().__init__(config=config, cache_interval=cache_interval)


class MerakiSectionNetwork(MerakiSection):
    def __init__(
            self,
            config: MerakiConfig,
            network_id: str,
            cache_interval: int = 1,
    ):
        self._network_id = network_id
        super().__init__(config=config, cache_interval=cache_interval)


class MerakiGetOrganizations(MerakiSection):
    @property
    def name(self):
        return 'getOrganizations'

    def get_live_data(self):
        try:
            return self._config.dashboard.organizations.getOrganizations(
                total_pages='all',
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Get organisations: %r', e)
            return []


class MerakiGetOrganization(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganization_{self._org_id}'

    def get_live_data(self):
        try:
            return self._config.dashboard.organizations.getOrganization(self._org_id)
        except meraki.exceptions.APIError as e:
            LOGGER.debug(f'Get organisation by id {self._org_id}: {e}')
            return {}


class MerakiGetOrganizationApiRequestsOverviewResponseCodesByInterval(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationApiRequestsOverviewResponseCodesByInterval{self._org_id}'

    def get_live_data(self):
        try:
            # gives 3 instead of only the last record :-(, switch to t0,t1
            # return self._config.dashboard.organizations.getOrganizationApiRequestsOverviewResponseCodesByInterval(
            #     self._org_id, timespan=60
            # )
            return self._config.dashboard.organizations.getOrganizationApiRequestsOverviewResponseCodesByInterval(
                self._org_id,
                total_pages='all',
                t0=strftime('%Y-%m-%dT%H:%M:%MZ', gmtime(now_time()-120)),
                t1=strftime('%Y-%m-%dT%H:%M:%MZ', gmtime())
            )

        except meraki.APIError as e:
            LOGGER.debug(f'Get API requests by id {self._org_id}: {e}')
            return {}


class MerakiGetOrganizationLicensesOverview(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationLicensesOverview_{self._org_id}'

    def get_live_data(self):
        try:
            return self._config.dashboard.organizations.getOrganizationLicensesOverview(
                self._org_id,
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get license overview: %r', self._org_id, e)
            return []


class MerakiGetOrganizationDevices(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationDevices_{self._org_id}'

    def get_live_data(self):
        try:
            return self._config.dashboard.organizations.getOrganizationDevices(
                self._org_id,
                total_pages='all',
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get devices: %r', self._org_id, e)
            return {}


class MerakiGetOrganizationNetworks(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationNetworks_{self._org_id}'

    def get_live_data(self):
        try:
            return self._config.dashboard.organizations.getOrganizationNetworks(
                self._org_id,
                total_pages='all',
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get networks: %r', self._org_id, e)
            return []


class MerakiGetOrganizationDevicesStatuses(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationDevicesStatuses_{self._org_id}'

    def get_live_data(self):
        try:
            return self._config.dashboard.organizations.getOrganizationDevicesStatuses(
                self._org_id,
                total_pages='all',
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get device statuses: %r', self._org_id, e)
            return []


class MerakiGetOrganizationDevicesUplinksAddressesByDevice(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationDevicesUplinksAddressesByDevice_{self._org_id}'

    def get_live_data(self):
        try:
            return self._config.dashboard.organizations.getOrganizationDevicesUplinksAddressesByDevice(
                self._org_id,
                total_pages='all',
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get device statuses: %r', self._org_id, e)
            return []


class MerakiGetOrganizationApplianceUplinkStatuses(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationApplianceUplinkStatuses_{self._org_id}'

    def get_live_data(self):
        try:
            return self._config.dashboard.appliance.getOrganizationApplianceUplinkStatuses(
                self._org_id,
                total_pages='all',
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get Appliance uplink status by network: %r', self._org_id, e)
            return []


class MerakiGetOrganizationApplianceUplinksUsageByNetwork(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationApplianceUplinksUsageByNetwork_{self._org_id}'

    def get_live_data(self):
        if meraki.__version__ < '1.39.0':
            LOGGER.debug(f'Meraki SDK is to old. Installed: {meraki.__version__}, excepted: 1.39.0')
            return []
        try:
            return self._config.dashboard.appliance.getOrganizationApplianceUplinksUsageByNetwork(
                organizationId=self._org_id,
                total_pages='all',
                timespan=60  # default=86400 (one day), maximum=1209600 (14 days), needs to match value in check
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get Appliance uplink usage by network: %r', self._org_id, e)
            return []


class MerakiGetOrganizationApplianceVpnStatuses(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationApplianceVpnStatuses_{self._org_id}'

    def get_live_data(self):
        try:
            return self._config.dashboard.appliance.getOrganizationApplianceVpnStatuses(
                self._org_id,
                total_pages='all',
            )

        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get Appliance VPN status by network: %r', self._org_id, e)
            return []


class MerakiGetDeviceAppliancePerformance(MerakiSectionSerial):

    @property
    def name(self):
        return f'getDeviceAppliancePerformance_{self._serial}'

    def get_live_data(self):
        try:
            return self._config.dashboard.appliance.getDeviceAppliancePerformance(
                self._serial)
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Serial: %r: Get appliance device performance: %r',
                         self._serial, e)
            return []


class MerakiGetOrganizationSensorReadingsLatest(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationSensorReadingsLatest_{self._org_id}'

    def get_live_data(self):
        try:
            return self._config.dashboard.sensor.getOrganizationSensorReadingsLatest(
                self._org_id,
                total_pages='all',
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get sensor readings: %r', self._org_id, e)
            return []


class MerakiGetDeviceSwitchPortsStatuses(MerakiSectionSerial):
    @property
    def name(self):
        return f'getDeviceSwitchPortsStatuses_{self._serial}'

    def get_live_data(self):
        try:
            return self._config.dashboard.switch.getDeviceSwitchPortsStatuses(
                self._serial,
                # total_pages='all',
                timespan=max(self._config.timespan, 900),
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Serial: %r: Get Switch Port Statuses: %r', self._serial, e)
            return []


class MerakiGetOrganizationWirelessDevicesEthernetStatuses(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationWirelessDevicesEthernetStatuses_{self._org_id}'

    def get_live_data(self):
        if meraki.__version__ < '1.39.0':
            LOGGER.debug(f'Meraki SDK is to old. Installed: {meraki.__version__}, expceted: 1.39.0')
            return []
        try:
            return self._config.dashboard.wireless.getOrganizationWirelessDevicesEthernetStatuses(
                self._org_id,
                total_pages='all',
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get wireless devices ethernet statuses: %r', self._org_id, e)
            return []


class MerakiGetDeviceWirelessStatus(MerakiSectionSerial):
    @property
    def name(self):
        return f'getDeviceWirelessStatus_{self._serial}'

    def get_live_data(self):
        try:
            return self._config.dashboard.wireless.getDeviceWirelessStatus(self._serial)
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Serial: %r: Get wireless device status: %r', self._serial, e)
            return []


# class MerakiGetDeviceLldpCdp(MerakiSectionSerial):
#     @property
#     def name(self):
#         return f'getDeviceLldpCdp_{self._serial}'
#
#     def get_live_data(self):
#         try:
#             return self._config.dashboard.devices.getDeviceLldpCdp(self._serial)
#         except meraki.exceptions.APIError as e:
#             LOGGER.debug('Serial: %r: Get LLDP/CDP data: %r', self._serial, e)
#             return []


class MerakiGetOrganizationCellularGatewayUplinkStatuses(MerakiSectionOrg):
    @property
    def name(self):
        return f'getOrganizationCellularGatewayUplinkStatuses_{self._org_id}'

    def get_live_data(self):
        try:
            return self._config.dashboard.cellularGateway.getOrganizationCellularGatewayUplinkStatuses(
                self._org_id,
                total_pages='all',
            )
        except meraki.exceptions.APIError as e:
            LOGGER.debug('Organisation ID: %r: Get cellular gateways uplink statuses: %r', self._org_id, e)
            return []


class MerakiGetOrganizationSwitchPortsStatusesBySwitch(MerakiSectionOrg):
    """
    needs Early Access enabled for the organization
    """
    @property
    def name(self):
        return f'getOrganizationSwitchPortsStatusesBySwitch{self._org_id}'

    def get_live_data(self):
        url = f'https://api.meraki.com/api/v1/organizations/{self._org_id}/switch/ports/statuses/bySwitch'
        params = {
            'timespan': max(self._config.timespan, 900),
            'total_pages': 'all',
        }
        headers = {
            'Authorization': f'Bearer {self._config.api_key}',
            'Accept': 'application/json'
        }
        proxies = {}
        if self._config.proxy not in [None, 'FROM_ENVIRONMENT', 'NO_PROXY']:
            proxies = {'https': self._config.proxy}
        # ToDo: implement correct error handling
        try:
            response = request(
                method='GET',
                url=url,
                headers=headers,
                proxies=proxies,
                params=params,
                timeout=3,
            )
        except RequestException as e:
            LOGGER.debug('Organisation ID: %r: Get Ports statuses by switch: %r', self._org_id, e)
            return []
        try:
            _response = response.json()
        except JSONDecodeError:
            LOGGER.debug('Organisation ID: %r: Get Ports statuses by switch: %r', self._org_id, response)
            return []
        if _response:
            return _response.get('items', [])
        return []


# class MerakiGetNetworkAppliancePorts(MerakiSectionNetwork):
#     @property
#     def name(self):
#         return f'getNetworkAppliancePorts_{self._network_id}'
#
#     def get_live_data(self):
#         try:
#             return self._config.dashboard.appliance.getNetworkAppliancePorts(
#                 self._network_id,
#                 # total_pages='all',
#             )
#         except meraki.exceptions.APIError as e:
#             LOGGER.debug('Network ID: %r: Get appliance ports: %r', self._network_id, e)
#             return []


#
# Main run
#
@dataclass()
class MerakiOrganisation:
    config: MerakiConfig
    organisation: _Organisation
    # _piggyback_prefix = ''
    # _piggyback_suffix = ''
    # _piggyback_case = None
    _networks: dict[str, MerakiNetwork] | None = None

    @property
    def organisation_id(self) -> str:
        return self.organisation[API_NAME_ORGANISATION_ID]

    @property
    def organisation_name(self) -> str:
        return self.organisation[API_NAME_ORGANISATION_NAME]

    def query(self) -> Iterator[Section]:
        if organisation := MerakiGetOrganization(
                config=self.config,
                org_id=self.organisation_id,
                cache_interval=self.config.cache_per_section.organisations,
        ).get_data(use_cache=self.config.use_cache):
            yield self._make_section(
                name=SEC_NAME_ORGANISATIONS,
                data=organisation,
            )
            if not organisation[API_NAME_API][API_NAME_ENABLED]:
                # stop here if API is not enabled for this organisation
                return

        if SEC_NAME_ORG_API_REQUESTS not in self.config.excluded_sections:
            if api_requests := MerakiGetOrganizationApiRequestsOverviewResponseCodesByInterval(
                    config=self.config,
                    org_id=self.organisation_id,
                    cache_interval=self.config.cache_per_section.org_api_requests,
            ).get_data(use_cache=False):  # here we want always life data
                yield self._make_section(
                    name=SEC_NAME_ORG_API_REQUESTS,
                    data={'org_id': self.organisation_id, 'requests': api_requests}
                )

        if SEC_NAME_LICENSES_OVERVIEW not in self.config.excluded_sections:
            if licenses_overview := self._get_licenses_overview():
                yield self._make_section(
                    name=SEC_NAME_LICENSES_OVERVIEW,
                    data=licenses_overview,
                )

        if networks := MerakiGetOrganizationNetworks(
            config=self.config,
            org_id=self.organisation_id,
            cache_interval=self.config.cache_per_section.networks,
        ).get_data(use_cache=self.config.use_cache):
            yield from self._add_networks(networks)

        if _need_devices(self.config.excluded_sections):
            devices_by_serial = self._get_devices_by_serial()
        else:
            devices_by_serial = {}

        # stop here if there are no devices in the organisation
        if not devices_by_serial:
            return

        devices_by_type = {}
        for _device in devices_by_serial.values():
            if not devices_by_type.get(_device[API_NAME_DEVICE_PRODUCT_TYPE]):
                devices_by_type[_device[API_NAME_DEVICE_PRODUCT_TYPE]] = []
            devices_by_type[_device[API_NAME_DEVICE_PRODUCT_TYPE]].append(_device)

        for device in devices_by_serial.values():
            yield self._make_section(
                name=SEC_NAME_DEVICE_INFO,
                data=device,
                piggyback=self._get_device_piggyback(device, devices_by_serial)
            )
            # if SEC_NAME_DEVICE_LLDP_CDP not in self.config.excluded_sections and device.get(
            #         'productType') not in [
            #     # 'appliance',  # bad data (inconsistent with switch data)
            #     'sensor',  # no data
            #     'camera',  # no data
            # ]:
            #     if device_lldp_cdp := MerakiGetDeviceLldpCdp(
            #         config=self.config,
            #         serial=str(device['serial']),
            #     ).get_data(use_cache=self.config.use_cache):
            #         yield self._make_section(
            #             name=SEC_NAME_DEVICE_LLDP_CDP,
            #             data=device_lldp_cdp,
            #             piggyback=self._get_device_piggyback(device, devices_by_serial)
            #         )

        if SEC_NAME_DEVICE_STATUSES not in self.config.excluded_sections:
            for device_status in MerakiGetOrganizationDevicesStatuses(
                    config=self.config,
                    org_id=self.organisation_id,
                    cache_interval=self.config.cache_per_section.device_statuses,
            ).get_data(use_cache=self.config.use_cache):
                if piggyback := self._get_device_piggyback(device_status, devices_by_serial):
                    yield self._make_section(
                        name=SEC_NAME_DEVICE_STATUSES,
                        data=device_status,
                        piggyback=piggyback,
                    )
        if SEC_NAME_DEVICE_UPLINKS_INFO not in self.config.excluded_sections:
            for device_uplink in MerakiGetOrganizationDevicesUplinksAddressesByDevice(
                    config=self.config,
                    org_id=self.organisation_id,
                    cache_interval=self.config.cache_per_section.device_uplinks_info,
            ).get_data(use_cache=self.config.use_cache):
                if piggyback := self._get_device_piggyback(device_uplink, devices_by_serial):
                    yield self._make_section(
                        name=SEC_NAME_DEVICE_UPLINKS_INFO,
                        data=device_uplink,
                        piggyback=piggyback,
                    )

        if devices_by_type.get(API_NAME_DEVICE_TYPE_SENSOR):
            if SEC_NAME_SENSOR_READINGS not in self.config.excluded_sections:
                for sensor_reading in MerakiGetOrganizationSensorReadingsLatest(
                        config=self.config,
                        org_id=self.organisation_id,
                        cache_interval=self.config.cache_per_section.sensor_readings,
                ).get_data(use_cache=self.config.use_cache):
                    if piggyback := self._get_device_piggyback(sensor_reading, devices_by_serial):
                        yield self._make_section(
                            name=SEC_NAME_SENSOR_READINGS,
                            data=sensor_reading,
                            piggyback=piggyback,
                        )

        if devices_by_type.get(API_NAME_DEVICE_TYPE_APPLIANCE):
            usage_by_serial = {}
            if SEC_NAME_APPLIANCE_UPLINKS_USAGE not in self.config.excluded_sections:
                uplink_usage_by_network = MerakiGetOrganizationApplianceUplinksUsageByNetwork(
                        config=self.config,
                        org_id=self.organisation_id,
                        cache_interval=self.config.cache_per_section.appliance_uplinks_usage,
                ).get_data(use_cache=False)  # here we want always life data

                # convert usage by network to usage by serial
                # usage_by_serial = {}
                for network in uplink_usage_by_network:
                    for uplink in network['byUplink']:
                        usage_by_serial[uplink[API_NAME_DEVICE_SERIAL]] = usage_by_serial.get(
                            uplink[API_NAME_DEVICE_SERIAL], {}
                        )
                        usage_by_serial[uplink[API_NAME_DEVICE_SERIAL]].update(
                            {
                                uplink['interface']: {'sent': uplink['sent'], 'received': uplink['received']},
                                API_NAME_DEVICE_SERIAL: uplink[API_NAME_DEVICE_SERIAL]
                            }
                        )

                # for appliance in usage_by_serial:
                #     if piggyback := self._get_device_piggyback(usage_by_serial[appliance], devices_by_serial):
                #         yield self._make_section(
                #             name=_SEC_NAME_APPLIANCE_UPLINKS_USAGE,
                #             data=usage_by_serial[appliance],
                #             piggyback=piggyback,
                #         )

            if SEC_NAME_APPLIANCE_UPLINKS not in self.config.excluded_sections:
                for appliance_uplinks in MerakiGetOrganizationApplianceUplinkStatuses(
                        config=self.config,
                        org_id=self.organisation_id,
                        cache_interval=self.config.cache_per_section.appliance_uplinks,
                ).get_data(use_cache=self.config.use_cache):
                    if piggyback := self._get_device_piggyback(appliance_uplinks, devices_by_serial):
                        # add network name
                        if self._networks.get(appliance_uplinks[API_NAME_NETWORK_ID]):
                            appliance_uplinks['networkName'] = self._networks[
                                appliance_uplinks[API_NAME_NETWORK_ID]].name

                        # add uplink usage
                        if appliance_usage := usage_by_serial.get(appliance_uplinks[API_NAME_DEVICE_SERIAL], None):
                            for uplink in appliance_uplinks['uplinks']:
                                uplink.update(appliance_usage.get(uplink['interface'], {}))

                        yield self._make_section(
                            name=SEC_NAME_APPLIANCE_UPLINKS,
                            data=appliance_uplinks,
                            piggyback=piggyback,
                        )

            if SEC_NAME_APPLIANCE_VPNS not in self.config.excluded_sections:
                for appliance_vpn in MerakiGetOrganizationApplianceVpnStatuses(
                        config=self.config,
                        org_id=self.organisation_id,
                        cache_interval=self.config.cache_per_section.appliance_vpns,
                ).get_data(use_cache=self.config.use_cache):
                    appliance_vpn.update({API_NAME_DEVICE_SERIAL: appliance_vpn['deviceSerial']})
                    if piggyback := self._get_device_piggyback(appliance_vpn, devices_by_serial):
                        yield self._make_section(
                            name=SEC_NAME_APPLIANCE_VPNS,
                            data=appliance_vpn,
                            piggyback=piggyback,
                        )

            if SEC_NAME_APPLIANCE_PERFORMANCE not in self.config.excluded_sections:
                for device in devices_by_type[API_NAME_DEVICE_TYPE_APPLIANCE]:
                    appliance_performance = MerakiGetDeviceAppliancePerformance(
                        config=self.config,
                        serial=device[API_NAME_DEVICE_SERIAL],
                        cache_interval=self.config.cache_per_section.appliance_performance,
                    ).get_data(use_cache=self.config.use_cache)
                    if piggyback := self._get_device_piggyback(device, devices_by_serial):
                        yield self._make_section(
                            name=SEC_NAME_APPLIANCE_PERFORMANCE,
                            data=appliance_performance,
                            piggyback=piggyback,
                            )

        if devices_by_type.get(API_NAME_DEVICE_TYPE_SWITCH):
            if SEC_NAME_SWITCH_PORTS_STATUSES not in self.config.excluded_sections:
                for switch in devices_by_type[API_NAME_DEVICE_TYPE_SWITCH]:
                    ports_statuses = MerakiGetDeviceSwitchPortsStatuses(
                        config=self.config,
                        serial=switch[API_NAME_DEVICE_SERIAL],
                        cache_interval=self.config.cache_per_section.switch_ports_statuses,
                    ).get_data(use_cache=self.config.use_cache)
                    if piggyback := self._get_device_piggyback(switch, devices_by_serial):
                        yield self._make_section(
                            name=SEC_NAME_SWITCH_PORTS_STATUSES,
                            data=ports_statuses,
                            piggyback=piggyback,
                        )

        if devices_by_type.get(API_NAME_DEVICE_TYPE_WIRELESS):
            if SEC_NAME_WIRELESS_ETHERNET_STATUSES not in self.config.excluded_sections:
                for device in MerakiGetOrganizationWirelessDevicesEthernetStatuses(
                        config=self.config,
                        org_id=self.organisation_id,
                        cache_interval=self.config.cache_per_section.wireless_ethernet_statuses,
                ).get_data(use_cache=self.config.use_cache):
                    if piggyback := self._get_device_piggyback(device, devices_by_serial):
                        yield self._make_section(
                            name=SEC_NAME_WIRELESS_ETHERNET_STATUSES,
                            data=device,
                            piggyback=piggyback,
                        )

            if SEC_NAME_WIRELESS_DEVICE_STATUS not in self.config.excluded_sections:
                for device in devices_by_type[API_NAME_DEVICE_TYPE_WIRELESS]:
                    wireless_statuses = MerakiGetDeviceWirelessStatus(
                        config=self.config,
                        serial=device[API_NAME_DEVICE_SERIAL],
                        cache_interval=self.config.cache_per_section.wireless_device_status,
                    ).get_data(use_cache=self.config.use_cache)
                    if piggyback := self._get_device_piggyback(device, devices_by_serial):
                        yield self._make_section(
                            name=SEC_NAME_WIRELESS_DEVICE_STATUS,
                            data=wireless_statuses,
                            piggyback=piggyback,
                            )

        if devices_by_type.get(API_NAME_DEVICE_TYPE_CELLULAR):
            if SEC_NAME_CELLULAR_UPLINKS not in self.config.excluded_sections:
                for gateway in MerakiGetOrganizationCellularGatewayUplinkStatuses(
                        config=self.config,
                        org_id=self.organisation_id,
                        cache_interval=self.config.cache_per_section.cellular_uplinks,
                ).get_data(use_cache=self.config.use_cache):
                    if piggyback := self._get_device_piggyback(gateway, devices_by_serial):
                        yield self._make_section(
                            name=SEC_NAME_CELLULAR_UPLINKS,
                            data=gateway,
                            piggyback=piggyback,
                        )

        # Early Access
        if SEC_NAME_ORG_SWITCH_PORTS_STATUSES not in self.config.excluded_sections:
            for switch in MerakiGetOrganizationSwitchPortsStatusesBySwitch(
                    config=self.config,
                    org_id=self.organisation_id,
                    cache_interval=self.config.cache_per_section.org_switch_ports_statuses,
            ).get_data(use_cache=self.config.use_cache):
                if piggyback := self._get_device_piggyback(switch, devices_by_serial):
                    yield self._make_section(
                        name=SEC_NAME_SWITCH_PORTS_STATUSES,
                        data=switch,
                        piggyback=piggyback,
                    )

    def _add_networks(self, networks):
        self._networks = {API_NAME_ORGANISATION_NAME: self.organisation_name}
        for network in networks:
            network.update({'organizationName': self.organisation_name})
            self._networks[network['id']] = MerakiNetwork(
                id=network['id'],
                name=network['name'],
                product_types=network['productTypes'],
                time_zone=network['timeZone'],
                tags=network['tags'],
                enrollment_string=network['enrollmentString'],
                notes=network['notes'],
                is_bound_to_config_template=network['isBoundToConfigTemplate'],
                organisation_id=network['organizationId'],
                organisation_name=self.organisation_name,
                url=network['url'],
            )
        yield self._make_section(
            name=SEC_NAME_NETWORKS,
            data=networks,
        )

    def _get_licenses_overview(self) -> MerakiAPIData | None:
        def _update_licenses_overview(
            licenses_overview: dict[str, object] | None
        ) -> MerakiAPIData | None:
            if not licenses_overview:
                return None
            licenses_overview.update(
                {
                    'organisation_id': self.organisation_id,
                    'organisation_name': self.organisation_name,
                }
            )
            return licenses_overview

        return _update_licenses_overview(
            MerakiGetOrganizationLicensesOverview(
                config=self.config,
                org_id=self.organisation_id,
                cache_interval=self.config.cache_per_section.licenses_overview,
            ).get_data(use_cache=self.config.use_cache)
        )

    def _get_devices_by_serial(self) -> Mapping[str, MerakiAPIData]:
        def _update_device(device: dict[str, object]) -> MerakiAPIData:
            device.update(
                {
                    'organisation_id': self.organisation_id,
                    'organisation_name': self.organisation_name,
                    'network_name': self._networks.get(device.get(API_NAME_NETWORK_ID)).name,
                }
            )
            return device

        return {
            str(device[API_NAME_DEVICE_SERIAL]): _update_device(device)
            for device in MerakiGetOrganizationDevices(
                config=self.config,
                org_id=self.organisation_id,
                cache_interval=self.config.cache_per_section.device_info,
            ).get_data(use_cache=self.config.use_cache)
        }

    def _get_device_piggyback(
        self, device: MerakiAPIData, devices_by_serial: Mapping[str, MerakiAPIData]
    ) -> str | None:
        LOGGER.debug(device)
        prefix = ''
        if self.config.org_id_as_prefix:
            prefix=self.organisation_id +'-'
        if self.config.net_id_as_prefix:
            try:
                prefix += device['networkId'] + '-'
            except KeyError:
                try:
                    prefix += device['network']['id'] + '-'
                except KeyError:
                    # print(device)
                    pass

        try:
            serial = device[API_NAME_DEVICE_SERIAL]
            if devices_by_serial[serial][API_NAME_DEVICE_NAME]:
                return f'{prefix}{devices_by_serial[serial][API_NAME_DEVICE_NAME]}'
            else:
                LOGGER.debug(f'Host without name _get_device_piggyback, use serial: {serial}')
                return f'{prefix}{serial}-{device[API_NAME_DEVICE_PRODUCT_TYPE]}'
        except KeyError as e:
            LOGGER.debug('Organisation ID: %r: Get device piggyback: %r', self.organisation_id, e)
            return None

    @staticmethod
    def _make_section(*, name: str, data: MerakiAPIData, piggyback: str | None = None) -> Section:
        return Section(
            api_data_source=MerakiAPIDataSource.org,
            name=SECTION_NAME_MAP[name],
            data=data,
            piggyback=piggyback,
        )


def query_meraki_objects(
        *,
        organisations: Sequence[MerakiOrganisation],
) -> Iterable[Section]:
    for organisation in organisations:
        yield from organisation.query()


def write_sections(sections: Iterable[Section]) -> None:
    sections_by_piggyback: dict = {}
    for section in sections:
        sections_by_piggyback.setdefault(section.piggyback, {}).setdefault(
            section.get_name(), []
        ).append(section.data)

    for piggyback, pb_section in sections_by_piggyback.items():
        with ConditionalPiggybackSection(piggyback):
            for section_name, section_data in pb_section.items():
                with SectionWriter(section_name) as writer:
                    writer.append_json(section_data)


# .
#   .--main----------------------------------------------------------------.
#   |                                       _                              |
#   |                       _ __ ___   __ _(_)_ __                         |
#   |                      | '_ ` _ \ / _` | | '_ \                        |
#   |                      | | | | | | (_| | | | | |                       |
#   |                      |_| |_| |_|\__,_|_|_| |_|                       |
#   |                                                                      |
#   '----------------------------------------------------------------------'


@dataclass(frozen=True)
class CachePerSection:
    appliance_performance: int
    appliance_uplinks: int
    appliance_uplinks_usage: int
    appliance_vpns: int
    cellular_uplinks: int
    device_info: int
    device_statuses: int
    device_uplinks_info: int
    licenses_overview: int
    networks: int
    org_api_requests: int
    org_switch_ports_statuses: int
    organisations: int
    sensor_readings: int
    switch_ports_statuses: int
    wireless_device_status: int
    wireless_ethernet_statuses: int


class Args(Namespace):
    apikey: str
    debug: bool
    excluded_sections: Sequence[str]
    hostname: str
    no_cache: bool
    org_id_as_prefix: bool
    net_id_as_prefix: bool
    orgs: Sequence[str]
    proxy: str
    sections: Sequence[str]
    region: str | None
    cache_per_section: List[int] | None = None


def parse_arguments(argv: Sequence[str] | None) -> Args:
    parser = create_default_argument_parser(description=__doc__)

    parser.add_argument('hostname')
    parser.add_argument(
        'apikey',
        help='API key for the Meraki API dashboard access.',
    )

    parser.add_argument('--proxy', type=str)

    # parser.add_argument(
    #     '--sections',
    #     nargs='+',
    #     choices=list(_SECTION_NAME_MAP),
    #     default=list(_SECTION_NAME_MAP),
    #     help='Explicit sections that are collected.',
    # )

    parser.add_argument(
        '--excluded-sections',
        nargs='*',
        choices=list(SECTION_NAME_MAP),
        default=[],
        help='Sections that are excluded form data collected.',
    )

    parser.add_argument(
        '--orgs',
        nargs='+',
        default=[],
        help='Explicit organisation IDs that are checked.',
    )

    # parser.add_argument(
    #     '--prefix-suffix',
    #     nargs=5,
    #     action='append',
    #     default=[],
    #     metavar=('Org-by-ID/Name', 'Organisation', 'Change Case', 'Prefix', 'Suffix')
    # )

    parser.add_argument(
        '--no-cache',
        default=False,
        action='store_const',
        const=True,
        help='Never use cached information. By default the agent will cache received data to '
             'avoid API limits and speed up the data retrieving.'
    )

    parser.add_argument(
        '--org-id-as-prefix',
        default=False,
        action='store_const',
        const=True,
        help='Use organisation ID as hostname prefix.'
    )
    parser.add_argument(
        '--net-id-as-prefix',
        default=False,
        action='store_const',
        const=True,
        help='Use network ID as hostname prefix.'
    )
    parser.add_argument(
        '--cache-per-section',
        nargs='+',
        type=int,
        help='List of cache time per section in minutes',
        default=[
            SEC_CACHE_APPLIANCE_PERFORMANCE,
            SEC_CACHE_APPLIANCE_UPLINKS,
            SEC_CACHE_APPLIANCE_UPLINKS_USAGE,
            SEC_CACHE_APPLIANCE_VPNS,
            SEC_CACHE_CELLULAR_UPLINKS,
            SEC_CACHE_DEVICE_INFO,
            SEC_CACHE_DEVICE_STATUSES,
            SEC_CACHE_DEVICE_UPLINKS_INFO,
            SEC_CACHE_LICENSES_OVERVIEW,
            SEC_CACHE_NETWORKS,
            SEC_CACHE_ORGANISATIONS,
            SEC_CACHE_ORG_API_REQUESTS,
            SEC_CACHE_ORG_SWITCH_PORTS_STATUSES,
            SEC_CACHE_SENSOR_READINGS,
            SEC_CACHE_SWITCH_PORTS_STATUSES,
            SEC_CACHE_WIRELESS_DEVICE_STATUS,
            SEC_CACHE_WIRELESS_ETHERNET_STATUSES,
        ]
    )

    parser.add_argument(
        '--region',
        choices=['default', 'canada', 'china', 'india', 'us_gov'],
        default='default',
        help='Meraki region to use.',
    )

    return parser.parse_args(argv)


def _need_devices(section_names: Sequence[str]) -> bool:
    return any(
        s not in section_names
        for s in [
            SEC_NAME_APPLIANCE_UPLINKS,
            SEC_NAME_APPLIANCE_UPLINKS_USAGE,
            SEC_NAME_APPLIANCE_VPNS,
            SEC_NAME_CELLULAR_UPLINKS,
            SEC_NAME_DEVICE_STATUSES,
            SEC_NAME_DEVICE_UPLINKS_INFO,
            SEC_NAME_SENSOR_READINGS,
            SEC_NAME_SWITCH_PORTS_STATUSES,
            SEC_NAME_WIRELESS_DEVICE_STATUS,
            SEC_NAME_WIRELESS_ETHERNET_STATUSES,
        ]
    )


def _get_organisations(config: MerakiConfig, org_ids: Sequence[str]) -> Sequence[_Organisation]:
    organisations = [
        _Organisation(
            id=organisation[API_NAME_ORGANISATION_ID],
            name=organisation[API_NAME_ORGANISATION_NAME],
        ) for organisation in MerakiGetOrganizations(
            config=config
        ).get_data(use_cache=config.use_cache)
    ]

    if org_ids:
        organisations = [
            organisation for organisation in organisations if organisation[API_NAME_ORGANISATION_ID] in org_ids
        ]

    return organisations


def get_proxy(raw_proxy: str) -> str | None:
    match raw_proxy:
        #  export https_proxy=http://192.168.10.144:3128
        #  export http_proxy=http://192.168.10.144:3128
        #  export ftp_proxy=http://192.168.10.144:3128
        case 'NO_PROXY':
            # environ['NO_PROXY'] = 'api.meraki.com'  # did not work
            environ['no_proxy'] = 'api.meraki.com'  # explicit disable proxy for meraki
            # environ['no_proxy'] = '*'  # explicit disable proxy for all
            # environ['https_proxy'] = '' # should be only true to the context of the agent
            # return None  # did not Work
            return ''  # this alone did not work
        case 'FROM_ENVIRONMENT':
            # requests uses by default urllib.request.getproxies(), so no need to fetch it here
            # return getproxies().get('https')
            return None
        case _:
            return raw_proxy


def agent_cisco_meraki_main(args: Args) -> int:
    if meraki.__version__ < MERAKI_SDK_MIN_VERSION:
        print(
            f'This Agent needs at least Meraki SDK version {MERAKI_SDK_MIN_VERSION}, installed is {meraki.__version__}'
        )
        exit(1)
    # don't remove used for runtime logging at the end
    start_time = time_ns()
    config = MerakiConfig(
        dashboard=configure_meraki_dashboard(
            api_key=args.apikey,
            debug=args.debug,
            proxy=get_proxy(args.proxy),
            region=MERAKI_REGIONS.get(args.region)
        ),
        hostname=args.hostname,
        # section_names=args.sections,
        excluded_sections=args.excluded_sections,
        use_cache=not args.no_cache,
        org_id_as_prefix=args.org_id_as_prefix,
        net_id_as_prefix=args.net_id_as_prefix,
        api_key=args.apikey,
        proxy=get_proxy(args.proxy),
        timespan=60,
        cache_per_section=CachePerSection(* args.cache_per_section) if args.cache_per_section else None
    )

    organisations = [
        MerakiOrganisation(config, organisation)
        for organisation in _get_organisations(config, args.orgs)
    ]

    sections = query_meraki_objects(
        organisations=organisations,
    )

    write_sections(sections)

    LOGGER.warning(f'Time taken: {(time_ns() - start_time) / 1e9}/s')
    LOGGER.warning(f'Meraki SDK version: {meraki.__version__}')
    return 0


def main() -> int:
    return special_agent_main(parse_arguments, agent_cisco_meraki_main)



