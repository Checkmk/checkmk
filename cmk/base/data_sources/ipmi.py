#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast, Optional, Set, List  # pylint: disable=unused-import
import pyghmi.ipmi.command as ipmi_cmd  # type: ignore[import]
import pyghmi.ipmi.sdr as ipmi_sdr  # type: ignore[import]
import pyghmi.constants as ipmi_const  # type: ignore[import]
from pyghmi.exceptions import IpmiException  # type: ignore[import]

import cmk.utils.debug
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import HostAddress, HostName  # pylint: disable=unused-import

from cmk.base.exceptions import MKAgentError
from cmk.base.config import IPMICredentials  # pylint: disable=unused-import
from cmk.base.check_utils import (  # pylint: disable=unused-import
    CheckPluginName, ServiceCheckResult, RawAgentData, ServiceDetails,
)

from .abstract import CheckMKAgentDataSource, ManagementBoardDataSource


def _handle_false_positive_warnings(reading):
    # type: (ipmi_sdr.SensorReading) -> RawAgentData
    """This is a workaround for a pyghmi bug
    (bug report: https://bugs.launchpad.net/pyghmi/+bug/1790120)

    For some sensors undefined states are looked up, which results in readings of the form
    {'states': ['Present',
                'Unknown state 8 for reading type 111/sensor type 8',
                'Unknown state 9 for reading type 111/sensor type 8',
                'Unknown state 10 for reading type 111/sensor type 8',
                'Unknown state 11 for reading type 111/sensor type 8',
                'Unknown state 12 for reading type 111/sensor type 8', ...],
     'health': 1, 'name': 'PS Status', 'imprecision': None, 'units': '',
     'state_ids': [552704, 552712, 552713, 552714, 552715, 552716, 552717, 552718],
     'type': 'Power Supply', 'value': None, 'unavailable': 0}

    The health warning is set, but only due to the lookup errors. We remove the lookup
    errors, and see whether the remaining states are meaningful.
    """
    states = [s.encode("utf-8") for s in reading.states if not s.startswith("Unknown state ")]

    if not states:
        return b"no state reported"

    if any(b"non-critical" in s for s in states):
        return b"WARNING"

    # just keep all the available info. It should be dealt with in
    # ipmi_sensors.include (freeipmi_status_txt_mapping),
    # where it will default to 2(CRIT)
    return b', '.join(states)


class IPMIManagementBoardDataSource(ManagementBoardDataSource, CheckMKAgentDataSource):
    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(IPMIManagementBoardDataSource, self).__init__(hostname, ipaddress)
        self._credentials = cast(IPMICredentials, self._host_config.management_credentials)

    def id(self):
        # type: () -> str
        return "mgmt_ipmi"

    def title(self):
        # type: () -> str
        return "Management board - IPMI"

    def describe(self):
        # type: () -> str
        return "%s (Address: %s, User: %s)" % (
            self.title(),
            self._ipaddress,
            self._credentials["username"],
        )

    def _cpu_tracking_id(self):
        # type: () -> str
        return self.id()

    def _gather_check_plugin_names(self):
        # type: () -> Set[CheckPluginName]
        return {"mgmt_ipmi_sensors"}

    def _execute(self):
        # type: () -> RawAgentData
        connection = None
        try:
            connection = self._create_ipmi_connection()

            output = b""
            output += self._fetch_ipmi_sensors_section(connection)
            output += self._fetch_ipmi_firmware_section(connection)

            return output
        except Exception as e:
            if cmk.utils.debug.enabled():
                raise

            # Improve bad exceptions thrown by pyghmi e.g. in case of connection issues
            if isinstance(e, IpmiException) and "%s" % e == "None":
                raise MKAgentError("IPMI communication failed: %r" % e)
            raise
        finally:
            if connection:
                connection.ipmi_session.logout()

    def _create_ipmi_connection(self):
        # type: () -> ipmi_cmd.Command
        # Do not use the (custom) ipaddress for the host. Use the management board
        # address instead
        credentials = self._credentials

        self._logger.debug("Connecting to %s:623 (User: %s, Privlevel: 2)" %
                           (self._ipaddress, credentials["username"]))
        return ipmi_cmd.Command(bmc=self._ipaddress,
                                userid=credentials["username"],
                                password=credentials["password"],
                                privlevel=2)

    def _fetch_ipmi_sensors_section(self, connection):
        # type: (ipmi_cmd.Command) -> RawAgentData
        self._logger.debug("Fetching sensor data via UDP from %s:623" % (self._ipaddress))

        try:
            sdr = ipmi_sdr.SDR(connection)
        except NotImplementedError as e:
            self._logger.log(VERBOSE, "Failed to fetch sensor data: %r", e)
            self._logger.debug("Exception", exc_info=True)
            return b""

        sensors = []
        for number in sdr.get_sensor_numbers():
            rsp = connection.raw_command(command=0x2d, netfn=4, data=(number,))
            if 'error' in rsp:
                continue

            reading = sdr.sensors[number].decode_sensor_reading(rsp['data'])
            if reading is not None:
                # sometimes (wrong) data for GPU sensors is reported, even if
                # not installed
                if "GPU" in reading.name and self._has_gpu(connection):
                    continue
                sensors.append(self._parse_sensor_reading(number, reading))

        return b"<<<mgmt_ipmi_sensors:sep(124)>>>\n" + b"".join(
            [b"|".join(sensor) + b"\n" for sensor in sensors])

    @staticmethod
    def _parse_sensor_reading(number, reading):
        # type: (int, ipmi_sdr.SensorReading) -> List[RawAgentData]
        # {'states': [], 'health': 0, 'name': 'CPU1 Temp', 'imprecision': 0.5,
        #  'units': '\xc2\xb0C', 'state_ids': [], 'type': 'Temperature',
        #  'value': 25.0, 'unavailable': 0}]]
        health_txt = b"N/A"
        if reading.health >= ipmi_const.Health.Failed:
            health_txt = b"FAILED"
        elif reading.health >= ipmi_const.Health.Critical:
            health_txt = b"CRITICAL"
        elif reading.health >= ipmi_const.Health.Warning:
            health_txt = b"WARNING"
            # workaround for pyghmi bug: https://bugs.launchpad.net/pyghmi/+bug/1790120
            health_txt = _handle_false_positive_warnings(reading)
        elif reading.health == ipmi_const.Health.Ok:
            health_txt = b"OK"

        return [
            b"%d" % number,
            reading.name,
            reading.type,
            (b"%0.2f" % reading.value) if reading.value else b"N/A",
            reading.units if reading.units != b"\xc2\xb0C" else b"C",
            health_txt,
        ]

    def _fetch_ipmi_firmware_section(self, connection):
        # type: (ipmi_cmd.Command) -> RawAgentData
        self._logger.debug("Fetching firmware information via UDP from %s:623" % (self._ipaddress))
        try:
            firmware_entries = connection.get_firmware()
        except Exception as e:
            self._logger.log(VERBOSE, "Failed to fetch firmware information: %r", e)
            self._logger.debug("Exception", exc_info=True)
            return b""

        output = b"<<<mgmt_ipmi_firmware:sep(124)>>>\n"
        for entity_name, attributes in firmware_entries:
            for attribute_name, value in attributes.items():
                output += b"%s|%s|%s\n" % (entity_name, attribute_name, value)

        return output

    # helper to sort out not installed GPU components
    def _has_gpu(self, connection):
        self._logger.debug("Fetching inventory information via UDP from %s:623" % (self._ipaddress))
        try:
            inventory_entries = connection.get_inventory_descriptions()
        except Exception as e:
            self._logger.verbose("Failed to fetch inventory information: %r" % e)
            self._logger.debug("Exception", exc_info=True)
            return ""

        for line in inventory_entries:
            if "GPU" in line:
                return False

        return True

    def _summary_result(self, for_checking):
        # type: (bool) -> ServiceCheckResult
        return 0, "Version: %s" % self._get_ipmi_version(), []

    def _get_ipmi_version(self):
        # type: () -> ServiceDetails
        if self._host_sections is None:
            return "unknown"

        section = self._host_sections.sections.get("mgmt_ipmi_firmware")
        if not section:
            return "unknown"

        for line in section:
            if line[0] == "BMC Version" and line[1] == "version":
                return line[2]

        return "unknown"
