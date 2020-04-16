#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger  # pylint: disable=unused-import
from types import TracebackType  # pylint: disable=unused-import
from typing import cast, Optional, Set, Type, List  # pylint: disable=unused-import

import six
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

from .abstract import AbstractDataFetcher, CheckMKAgentDataSource, management_board_ipaddress


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
        # workaround for pyghmi bug: https://bugs.launchpad.net/pyghmi/+bug/1790120
        health_txt = _handle_false_positive_warnings(reading)
    elif reading.health == ipmi_const.Health.Ok:
        health_txt = b"OK"

    return [
        b"%d" % number,
        six.ensure_binary(reading.name),
        six.ensure_binary(reading.type),
        (b"%0.2f" % reading.value) if reading.value else b"N/A",
        six.ensure_binary(reading.units) if reading.units != b"\xc2\xb0C" else b"C",
        health_txt,
    ]


class IPMIDataFetcher(AbstractDataFetcher):
    def __init__(self, ipaddress, username, password, logger):
        super(IPMIDataFetcher, self).__init__()
        self._ipaddress = ipaddress  # type: HostAddress
        self._username = username  # type: str
        self._password = password  # type: str
        self._logger = logger  # type: Logger
        self._command = None  # type: Optional[ipmi_cmd.Command]

    def __enter__(self):
        # type: () -> IPMIDataFetcher
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> bool
        self.close()
        if exc_type is IpmiException and not str(exc_value):
            # Raise a more specific exception
            raise MKAgentError("IPMI communication failed: %r" % exc_type)
        if not cmk.utils.debug.enabled():
            return False
        return True

    def data(self):
        # type: () -> RawAgentData
        if self._command is None:
            raise MKAgentError("Not connected")

        output = b""
        output += self._sensors_section()
        output += self._firmware_section()
        return output

    def open(self):
        # type: () -> None
        self._logger.debug("Connecting to %s:623 (User: %s, Privlevel: 2)", self._ipaddress,
                           self._username)
        self._command = ipmi_cmd.Command(bmc=self._ipaddress,
                                         userid=self._username,
                                         password=self._password,
                                         privlevel=2)

    def close(self):
        # type: () -> None
        if self._command is None:
            return

        self._logger.debug("Closing connection to %s:623", self._command.bmc)
        self._command.ipmi_session.logout()

    def _sensors_section(self):
        # type: () -> RawAgentData
        if self._command is None:
            raise MKAgentError("Not connected")

        self._logger.debug("Fetching sensor data via UDP from %s:623", self._command.bmc)

        try:
            sdr = ipmi_sdr.SDR(self._command)
        except NotImplementedError as e:
            self._logger.log(VERBOSE, "Failed to fetch sensor data: %r", e)
            self._logger.debug("Exception", exc_info=True)
            return b""

        sensors = []
        has_no_gpu = not self._has_gpu()
        for number in sdr.get_sensor_numbers():
            rsp = self._command.raw_command(command=0x2d, netfn=4, data=(number,))
            if 'error' in rsp:
                continue

            reading = sdr.sensors[number].decode_sensor_reading(rsp['data'])
            if reading is not None:
                # sometimes (wrong) data for GPU sensors is reported, even if
                # not installed
                if "GPU" in reading.name and has_no_gpu:
                    continue
                sensors.append(_parse_sensor_reading(number, reading))

        return b"<<<mgmt_ipmi_sensors:sep(124)>>>\n" + b"".join(
            [b"|".join(sensor) + b"\n" for sensor in sensors])

    def _firmware_section(self):
        # type: () -> RawAgentData
        if self._command is None:
            raise MKAgentError("Not connected")

        self._logger.debug("Fetching firmware information via UDP from %s:623", self._command.bmc)
        try:
            firmware_entries = self._command.get_firmware()
        except Exception as e:
            self._logger.log(VERBOSE, "Failed to fetch firmware information: %r", e)
            self._logger.debug("Exception", exc_info=True)
            return b""

        output = b"<<<mgmt_ipmi_firmware:sep(124)>>>\n"
        for entity_name, attributes in firmware_entries:
            for attribute_name, value in attributes.items():
                output += b"|".join(f.encode("utf8") for f in (entity_name, attribute_name, value))
                output += b"\n"

        return output

    def _has_gpu(self):
        # type: () -> bool
        if self._command is None:
            return False

        # helper to sort out not installed GPU components
        self._logger.debug("Fetching inventory information via UDP from %s:623", self._command.bmc)
        try:
            inventory_entries = self._command.get_inventory_descriptions()
        except Exception as e:
            self._logger.log(VERBOSE, "Failed to fetch inventory information: %r", e)
            self._logger.debug("Exception", exc_info=True)
            # in case of connection problems, we don't want to ignore possible
            # GPU entries
            return True

        return any("GPU" in line for line in inventory_entries)


# NOTE: This class is *not* abstract, even if pylint is too dumb to see that!
class IPMIManagementBoardDataSource(CheckMKAgentDataSource):
    _for_mgmt_board = True

    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(IPMIManagementBoardDataSource, self).__init__(hostname,
                                                            management_board_ipaddress(hostname))
        self._credentials = cast(IPMICredentials, self._host_config.management_credentials)

    def id(self):
        # type: () -> str
        return "mgmt_ipmi"

    def title(self):
        # type: () -> str
        return "Management board - IPMI"

    def describe(self):
        # type: () -> str
        items = []
        if self._ipaddress:
            items.append("Address: %s" % self._ipaddress)
        if self._credentials:
            items.append("User: %s" % self._credentials["username"])
        return "%s (%s)" % (self.title(), ", ".join(items))

    def _cpu_tracking_id(self):
        # type: () -> str
        return self.id()

    def _gather_check_plugin_names(self):
        # type: () -> Set[CheckPluginName]
        return {"mgmt_ipmi_sensors"}

    def _execute(self):
        # type: () -> RawAgentData
        if not self._credentials:
            raise MKAgentError("Missing credentials")

        if self._ipaddress is None:
            raise MKAgentError("Missing IP address")

        with IPMIDataFetcher(self._ipaddress, self._credentials["username"],
                             self._credentials["password"], self._logger) as fetcher:
            return fetcher.data()
        raise MKAgentError("Failed to read data")

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
