#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import copy
import logging
from typing import Any, Final, List, Mapping, Optional, Sequence, TYPE_CHECKING

import pyghmi.constants as ipmi_const  # type: ignore[import]
from pyghmi.exceptions import IpmiException  # type: ignore[import]

if TYPE_CHECKING:
    # The remaining pyghmi imports are expensive (60 ms for all of them together).
    import pyghmi.ipmi.command as ipmi_cmd  # type: ignore[import]
    import pyghmi.ipmi.sdr as ipmi_sdr  # type: ignore[import]

from six import ensure_binary

from cmk.utils.check_utils import ActiveCheckResult
from cmk.utils.exceptions import MKFetcherError
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import AgentRawData, HostAddress

from .agent import AgentFetcher, AgentRawDataSection, AgentSummarizer, DefaultAgentFileCache
from .host_sections import HostSections
from .type_defs import Mode


class IPMIFetcher(AgentFetcher):
    """Fetch IPMI data using `pyghmi`.

    Note:
        The arguments `address`, `username`, and `password` are used
        to instantiate the `pyghmi.ipmi.command.Command` where every
        argument is defaulted.  We therefore make them optional
        here as well.

    """

    def __init__(
        self,
        file_cache: DefaultAgentFileCache,
        *,
        address: HostAddress,  # Could actually be HostName as well.
        username: Optional[str],
        password: Optional[str],
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.helper.ipmi"))
        self.address: Final = address
        self.username: Final = username
        self.password: Final = password
        self._command: Optional[ipmi_cmd.Command] = None

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"{type(self.file_cache).__name__}",
                    f"address={self.address!r}",
                    f"username={self.username!r}",
                    f"password={self.password!r}",
                )
            )
            + ")"
        )

    @classmethod
    def _from_json(cls, serialized: Mapping[str, Any]) -> IPMIFetcher:
        serialized_ = copy.deepcopy(dict(serialized))
        return cls(
            DefaultAgentFileCache.from_json(serialized_.pop("file_cache")),
            **serialized_,
        )

    def to_json(self) -> Mapping[str, Any]:
        return {
            "file_cache": self.file_cache.to_json(),
            "address": self.address,
            "username": self.username,
            "password": self.password,
        }

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        if self._command is None:
            raise MKFetcherError("Not connected")

        return AgentRawData(b"" + self._sensors_section() + self._firmware_section())

    def open(self) -> None:
        self._logger.debug(
            "Connecting to %s:623 (User: %s, Privlevel: 2)",
            self.address or "local",
            self.username or "no user",
        )

        # Performance: See header.
        import pyghmi.ipmi.command as ipmi_cmd  # type: ignore[import]

        try:
            self._command = ipmi_cmd.Command(
                bmc=self.address,
                userid=self.username,
                password=self.password,
                privlevel=2,
            )
        except IpmiException as exc:
            raise MKFetcherError("IPMI connection failed") from exc

    def close(self) -> None:
        if self._command is None:
            return

        self._logger.debug("Closing connection to %s:623", self._command.bmc)

        # This should not be our task, but seems pyghmi is not cleaning up good enough.
        # There are some module and class level caches in pyghmi.ipmi.private.session that
        # are kept after logout which should not be kept.
        # These session objects and sockets lead to problems in our keepalive helper processes
        # because they make the process reuse invalid sessions.  Instead of reusing, we want to
        # initialize a new session every cycle.
        # We also don't want to reuse sockets or other things from previous calls.

        import pyghmi.ipmi.private.session as ipmi_session  # type: ignore[import]

        ipmi_session.iothread.join()
        ipmi_session.iothread = None
        ipmi_session.iothreadready = False
        ipmi_session.iothreadwaiters.clear()

        for socket in ipmi_session.iosockets:
            socket.close()
        ipmi_session.iosockets.clear()

        ipmi_session.Session.socketpool.clear()
        ipmi_session.Session.initting_sessions.clear()
        ipmi_session.Session.bmc_handlers.clear()
        ipmi_session.Session.waiting_sessions.clear()
        ipmi_session.Session.initting_sessions.clear()
        ipmi_session.Session.keepalive_sessions.clear()
        ipmi_session.Session.peeraddr_to_nodes.clear()
        ipmi_session.Session.iterwaiters.clear()

        self._command = None

    def _sensors_section(self) -> AgentRawData:
        if self._command is None:
            raise MKFetcherError("Not connected")

        self._logger.debug("Fetching sensor data via UDP from %s:623", self._command.bmc)

        # Performance: See header.
        import pyghmi.ipmi.sdr as ipmi_sdr  # type: ignore[import]

        try:
            sdr = ipmi_sdr.SDR(self._command)
        except NotImplementedError as e:
            self._logger.log(VERBOSE, "Failed to fetch sensor data: %r", e)
            self._logger.debug("Exception", exc_info=True)
            return AgentRawData(b"")

        sensors = []
        has_no_gpu = not self._has_gpu()
        for ident in sdr.get_sensor_numbers():
            sensor = sdr.sensors[ident]
            rsp = self._command.raw_command(
                command=0x2D, netfn=4, rslun=sensor.sensor_lun, data=(sensor.sensor_number,)
            )
            if "error" in rsp:
                continue

            reading = sensor.decode_sensor_reading(rsp["data"])
            if reading is not None:
                # sometimes (wrong) data for GPU sensors is reported, even if
                # not installed
                if "GPU" in reading.name and has_no_gpu:
                    continue
                sensors.append(self._parse_sensor_reading(sensor.sensor_number, reading))

        return AgentRawData(
            b"<<<ipmi_sensors:sep(124)>>>\n"
            + b"".join(b"|".join(sensor) + b"\n" for sensor in sensors)
        )

    def _firmware_section(self) -> AgentRawData:
        if self._command is None:
            raise MKFetcherError("Not connected")

        self._logger.debug("Fetching firmware information via UDP from %s:623", self._command.bmc)
        try:
            firmware_entries = self._command.get_firmware()
        except Exception as e:
            self._logger.log(VERBOSE, "Failed to fetch firmware information: %r", e)
            self._logger.debug("Exception", exc_info=True)
            return AgentRawData(b"")

        output = b"<<<ipmi_firmware:sep(124)>>>\n"
        for entity_name, attributes in firmware_entries:
            for attribute_name, value in attributes.items():
                output += b"|".join(f.encode("utf8") for f in (entity_name, attribute_name, value))
                output += b"\n"

        return AgentRawData(output)

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

    def _parse_sensor_reading(
        self, number: int, reading: ipmi_sdr.SensorReading
    ) -> List[AgentRawData]:
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
            health_txt = self._handle_false_positive_warnings(reading)
        elif reading.health == ipmi_const.Health.Ok:
            health_txt = b"OK"
        # ? would that be correct: SensorReading.name:str, SensorReading.type:str, SensorReading.units: bytes/str ?
        return [
            AgentRawData(_)
            for _ in (
                b"%d" % number,
                ensure_binary(reading.name),  # pylint: disable= six-ensure-str-bin-call
                ensure_binary(reading.type),  # pylint: disable= six-ensure-str-bin-call
                (b"%0.2f" % reading.value) if reading.value else b"N/A",
                ensure_binary(reading.units)  # pylint: disable= six-ensure-str-bin-call
                if reading.units != b"\xc2\xb0C"
                else b"C",
                health_txt,
            )
        ]

    def _handle_false_positive_warnings(self, reading: ipmi_sdr.SensorReading) -> AgentRawData:
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
        self._logger.debug("Raw reading states of %s: %s", reading.name, reading.states)

        states = [s.encode("utf-8") for s in reading.states if not s.startswith("Unknown state ")]

        if not states:
            return AgentRawData(b"no state reported")

        # just keep all the available info. It should be dealt with in
        # ipmi_sensors.include (freeipmi_status_txt_mapping),
        # where it will default to 2(CRIT)
        return AgentRawData(b", ".join(states))


class IPMISummarizer(AgentSummarizer):
    def summarize_success(
        self,
        host_sections: HostSections[AgentRawDataSection],
        *,
        mode: Mode,
    ) -> Sequence[ActiveCheckResult]:
        return [ActiveCheckResult(0, "Success")]
