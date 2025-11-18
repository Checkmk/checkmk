#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

AGENT = "cisco_meraki"
APIKEY_OPTION_NAME: Final = "apikey"

API_NAME_DEVICE_SERIAL: Final = "serial"
API_NAME_DEVICE_NAME: Final = "name"

SEC_NAME_LICENSES_OVERVIEW: Final = "licenses-overview"
SEC_NAME_DEVICE_STATUSES: Final = "device-statuses"
SEC_NAME_SENSOR_READINGS: Final = "sensor-readings"

OPTIONAL_SECTIONS_CHOICES: Final = (
    SEC_NAME_DEVICE_STATUSES,
    SEC_NAME_LICENSES_OVERVIEW,
    SEC_NAME_SENSOR_READINGS,
)

OPTIONAL_SECTIONS_DEFAULT: Final = (
    SEC_NAME_DEVICE_STATUSES,
    SEC_NAME_LICENSES_OVERVIEW,
    SEC_NAME_SENSOR_READINGS,
)
