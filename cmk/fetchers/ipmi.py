#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from typing import Any, Dict, Final, List, Optional

import pyghmi.constants as ipmi_const  # type: ignore[import]
import pyghmi.ipmi.command as ipmi_cmd  # type: ignore[import]
import pyghmi.ipmi.sdr as ipmi_sdr  # type: ignore[import]
from six import ensure_binary

from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import AgentRawData, HostAddress

from . import MKFetcherError
from .agent import AgentFetcher, DefaultAgentFileCache
from .type_defs import Mode


class IPMIFetcher(AgentFetcher):
    def __init__(
        self,
        file_cache: DefaultAgentFileCache,
        *,
        address: HostAddress,
        username: str,
        password: str,
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.fetchers.ipmi"))
        self.address: Final = address
        self.username: Final = username
        self.password: Final = password
        self._command: Optional[ipmi_cmd.Command] = None

    @classmethod
    def from_json(cls, serialized: Dict[str, Any]) -> "IPMIFetcher":
        return cls(
            DefaultAgentFileCache.from_json(serialized.pop("file_cache")),
            **serialized,
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "file_cache": self.file_cache.to_json(),
            "address": self.address,
            "username": self.username,
            "password": self.password,
        }

    def _is_cache_enabled(self, mode: Mode) -> bool:
        return mode is not Mode.CHECKING

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        if self._command is None:
            raise MKFetcherError("Not connected")

        output = b""
        output += self._sensors_section()
        output += self._firmware_section()
        return output

    def open(self) -> None:
        self._logger.debug(
            "Connecting to %s:623 (User: %s, Privlevel: 2)",
            self.address,
            self.username,
        )
        self._command = ipmi_cmd.Command(
            bmc=self.address,
            userid=self.username,
            password=self.password,
            privlevel=2,
        )

    def close(self) -> None:
        if self._command is None:
            return

        self._logger.debug("Closing connection to %s:623", self._command.bmc)
        self._command.ipmi_session.logout()

    def _sensors_section(self) -> AgentRawData:
        if self._command is None:
            raise MKFetcherError("Not connected")

        self._logger.debug("Fetching sensor data via UDP from %s:623", self._command.bmc)

        try:
            sdr = ipmi_sdr.SDR(self._command)
        except NotImplementedError as e:
            self._logger.log(VERBOSE, "Failed to fetch sensor data: %r", e)
            self._logger.debug("Exception", exc_info=True)
            return b""

        sensors = []
        has_no_gpu = not self._has_gpu()
        for ident in sdr.get_sensor_numbers():
            sensor = sdr.sensors[ident]
            rsp = self._command.raw_command(command=0x2d,
                                            netfn=4,
                                            rslun=sensor.sensor_lun,
                                            data=(sensor.sensor_number,))
            if 'error' in rsp:
                continue

            reading = sensor.decode_sensor_reading(rsp['data'])
            if reading is not None:
                # sometimes (wrong) data for GPU sensors is reported, even if
                # not installed
                if "GPU" in reading.name and has_no_gpu:
                    continue
                sensors.append(IPMIFetcher._parse_sensor_reading(sensor.sensor_number, reading))

        return b"<<<mgmt_ipmi_sensors:sep(124)>>>\n" + b"".join(
            [b"|".join(sensor) + b"\n" for sensor in sensors])

    def _firmware_section(self) -> AgentRawData:
        if self._command is None:
            raise MKFetcherError("Not connected")

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

    def _has_gpu(self) -> bool:
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

    @staticmethod
    def _parse_sensor_reading(number: int, reading: ipmi_sdr.SensorReading) -> List[AgentRawData]:
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
            health_txt = IPMIFetcher._handle_false_positive_warnings(reading)
        elif reading.health == ipmi_const.Health.Ok:
            health_txt = b"OK"

        return [
            b"%d" % number,
            ensure_binary(reading.name),
            ensure_binary(reading.type),
            (b"%0.2f" % reading.value) if reading.value else b"N/A",
            ensure_binary(reading.units) if reading.units != b"\xc2\xb0C" else b"C",
            health_txt,
        ]

    @staticmethod
    def _handle_false_positive_warnings(reading: ipmi_sdr.SensorReading) -> AgentRawData:
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
