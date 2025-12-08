#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

AGENT = "cisco_meraki"
APIKEY_OPTION_NAME: Final = "apikey"

SEC_NAME_API_RESPONSE_CODES: Final = "api-response-codes"
SEC_NAME_LICENSES_OVERVIEW: Final = "licenses-overview"
SEC_NAME_DEVICE_STATUSES: Final = "device-statuses"
SEC_NAME_DEVICE_UPLINKS_INFO: Final = "device-uplinks-info"
SEC_NAME_SENSOR_READINGS: Final = "sensor-readings"
SEC_NAME_APPLIANCE_PERFORMANCE: Final = "appliance-performance"
SEC_NAME_APPLIANCE_UPLINKS: Final = "appliance-uplinks"
SEC_NAME_APPLIANCE_VPNS: Final = "appliance-vpns"
SEC_NAME_SWITCH_PORT_STATUSES: Final = "switch-port-statuses"
SEC_NAME_WIRELESS_ETHERNET_STATUSES: Final = "wireless-ethernet-statuses"

OPTIONAL_SECTIONS_CHOICES: Final = (
    SEC_NAME_API_RESPONSE_CODES,
    SEC_NAME_APPLIANCE_PERFORMANCE,
    SEC_NAME_APPLIANCE_UPLINKS,
    SEC_NAME_APPLIANCE_VPNS,
    SEC_NAME_DEVICE_STATUSES,
    SEC_NAME_DEVICE_UPLINKS_INFO,
    SEC_NAME_LICENSES_OVERVIEW,
    SEC_NAME_SENSOR_READINGS,
    SEC_NAME_SWITCH_PORT_STATUSES,
    SEC_NAME_WIRELESS_ETHERNET_STATUSES,
)

OPTIONAL_SECTIONS_DEFAULT: Final = (
    SEC_NAME_API_RESPONSE_CODES,
    SEC_NAME_APPLIANCE_UPLINKS,
    SEC_NAME_APPLIANCE_VPNS,
    SEC_NAME_DEVICE_STATUSES,
    SEC_NAME_DEVICE_UPLINKS_INFO,
    SEC_NAME_LICENSES_OVERVIEW,
    SEC_NAME_SENSOR_READINGS,
    SEC_NAME_WIRELESS_ETHERNET_STATUSES,
)

DEFAULT_TIMESPAN: Final = 60
