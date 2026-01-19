#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from polyfactory.factories import TypedDictFactory

from cmk.plugins.cisco_meraki.lib import schema


class RawOrganizationFactory(TypedDictFactory[schema.RawOrganisation]):
    __check_model__ = False


class RawApiResponseCodesFactory(TypedDictFactory[schema.RawApiResponseCodes]):
    __check_model__ = False


class RawLicensesOverviewFactory(TypedDictFactory[schema.RawLicensesOverview]):
    __check_model__ = False


class RawDeviceFactory(TypedDictFactory[schema.RawDevice]):
    __check_model__ = False


class DeviceFactory(TypedDictFactory[schema.Device]):
    __check_model__ = False


class RawDevicesStatusFactory(TypedDictFactory[schema.RawDevicesStatus]):
    __check_model__ = False


class RawDevicesUplinksAddressFactory(TypedDictFactory[schema.RawDeviceUplinksAddress]):
    __check_model__ = False


class RawNetworkFactory(TypedDictFactory[schema.RawNetwork]):
    __check_model__ = False


class RawSensorReadingsFactory(TypedDictFactory[schema.RawSensorReadings]):
    __check_model__ = False


class RawSwitchPortStatusFactory(TypedDictFactory[schema.RawSwitchPortStatus]):
    __check_model__ = False


class RawUplinkStatusesFactory(TypedDictFactory[schema.RawUplinkStatuses]):
    __check_model__ = False


class RawUplinkVpnStatusesFactory(TypedDictFactory[schema.RawUplinkVpnStatuses]):
    __check_model__ = False


class RawUplinkUsageFactory(TypedDictFactory[schema.RawUplinkUsage]):
    __check_model__ = False


class RawWirelessDeviceStatusFactory(TypedDictFactory[schema.RawWirelessDeviceStatus]):
    __check_model__ = False


class RawWirelessEthernetStatusFactory(TypedDictFactory[schema.RawWirelessEthernetStatus]):
    __check_model__ = False
