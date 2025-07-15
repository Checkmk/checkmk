#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import errno
import logging
import os
from collections.abc import Iterable
from dataclasses import astuple, dataclass
from typing import Final, Self, TYPE_CHECKING, TypedDict

import pyghmi.constants as ipmi_const
from pyghmi.exceptions import IpmiException

if TYPE_CHECKING:
    # The remaining pyghmi imports are expensive (60 ms for all of them together).
    import pyghmi.ipmi.command as ipmi_cmd
    import pyghmi.ipmi.sdr as ipmi_sdr

from cmk.ccc.exceptions import MKFetcherError, MKTimeout
from cmk.ccc.hostaddress import HostAddress

from cmk.utils.agentdatatype import AgentRawData

from ._abstract import Fetcher, Mode

__all__ = ["IPMICredentials", "IPMIFetcher"]


# Keep in sync with cmk.gui.watolib.host_attributes.IPMICredentials
class IPMICredentials(TypedDict, total=False):
    username: str
    password: str


@dataclass(frozen=True)
class IPMISensor:
    id: bytes
    name: bytes
    type: bytes
    value: bytes
    unit: bytes
    health: bytes

    @classmethod
    def from_reading(cls, number: int, reading: ipmi_sdr.SensorReading) -> Self:
        # {'states': [], 'health': 0, 'name': 'CPU1 Temp', 'imprecision': 0.5,
        #  'units': '\xc2\xb0C', 'state_ids': [], 'type': 'Temperature',
        #  'value': 25.0, 'unavailable': 0}]]
        return cls(
            id=b"%d" % number,
            name=reading.name.encode("utf-8"),
            type=reading.type.encode("utf-8"),
            value=(b"%0.2f" % reading.value) if reading.value else b"N/A",
            unit=(reading.units.encode("utf-8") if reading.units != b"\xc2\xb0C" else b"C"),
            health=cls._parse_health_txt(reading),
        )

    @classmethod
    def _parse_health_txt(cls, reading: ipmi_sdr.SensorReading) -> bytes:
        if reading.health >= ipmi_const.Health.Failed:
            return b"FAILED"
        if reading.health >= ipmi_const.Health.Critical:
            return b"CRITICAL"
        if reading.health >= ipmi_const.Health.Warning:
            # workaround for pyghmi bug: https://bugs.launchpad.net/pyghmi/+bug/1790120
            return cls._handle_false_positive_warnings(reading)
        if reading.health == ipmi_const.Health.Ok:
            return b"OK"
        return b"N/A"

    @staticmethod
    def _handle_false_positive_warnings(reading: ipmi_sdr.SensorReading) -> bytes:
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
        # just keep all the available info. It should be dealt with in
        # ipmi_sensors.include (freeipmi_status_txt_mapping),
        # where it will default to 2(CRIT)
        return (
            b", ".join(
                s.encode("utf-8") for s in reading.states if not s.startswith("Unknown state ")
            )
            or b"no state reported"
        )


class IPMIFetcher(Fetcher[AgentRawData]):
    """Fetch IPMI data using `pyghmi`.

    Note:
        The arguments `address`, `username`, and `password` are used
        to instantiate the `pyghmi.ipmi.command.Command` where every
        argument is defaulted.  We therefore make them optional
        here as well.

    """

    def __init__(
        self,
        *,
        address: HostAddress,  # Could actually be HostName as well.
        username: str | None,
        password: str | None,
    ) -> None:
        super().__init__()
        self.address: Final = address
        self.username: Final = username
        self.password: Final = password
        self._logger: Final = logging.getLogger("cmk.helper.ipmi")
        self._command: ipmi_cmd.Command | None = None

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"address={self.address!r}",
                    f"username={self.username!r}",
                    f"password={self.password!r}",
                )
            )
            + ")"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, IPMIFetcher):
            return False
        return (
            self.address == other.address
            and self.username == other.username
            and self.password == other.password
        )

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        self._logger.debug("Get IPMI data")
        if self._command is None:
            raise OSError(errno.ENOTCONN, os.strerror(errno.ENOTCONN))

        return AgentRawData(b"" + self._sensors_section() + self._firmware_section())

    def open(self) -> None:
        self._logger.debug(
            "Connecting to %s:623 (User: %s, Privlevel: 2)",
            self.address or "local",
            self.username or "no user",
        )

        # Performance: See header.
        import pyghmi.ipmi.command as ipmi_cmd

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

        import pyghmi.ipmi.private.session as ipmi_session

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
            raise OSError(errno.ENOTCONN, os.strerror(errno.ENOTCONN))

        self._logger.debug("Fetching sensor data via UDP from %s:623", self._command.bmc)

        # Performance: See header.
        import pyghmi.ipmi.sdr as ipmi_sdr

        try:
            sdr = ipmi_sdr.SDR(self._command)
        except NotImplementedError as e:
            self._logger.debug("Failed to fetch sensor data: %r", e)
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

            reading = sensor.decode_sensor_reading(self._command, rsp["data"])
            if reading is not None:
                # sometimes (wrong) data for GPU sensors is reported, even if
                # not installed
                if "GPU" in reading.name and has_no_gpu:
                    continue
                self._logger.debug("Raw reading states of %s: %s", reading.name, reading.states)
                sensors.append(IPMISensor.from_reading(sensor.sensor_number, reading))

        return AgentRawData(
            b"<<<ipmi_sensors:sep(124)>>>\n"
            + b"".join(self._make_line(astuple(sensor)) for sensor in sensors)
        )

    def _firmware_section(self) -> AgentRawData:
        if self._command is None:
            raise OSError(errno.ENOTCONN, os.strerror(errno.ENOTCONN))

        self._logger.debug("Fetching firmware information via UDP from %s:623", self._command.bmc)
        try:
            firmware_entries = self._command.get_firmware()
        except MKTimeout:
            raise
        except Exception as e:
            self._logger.debug("Failed to fetch firmware information: %r", e)
            self._logger.debug("Exception", exc_info=True)
            return AgentRawData(b"")

        return AgentRawData(
            b"<<<ipmi_firmware:sep(124)>>>\n"
            + b"".join(
                self._make_line(str(f).encode("utf8") for f in (entity_name, attribute_name, value))
                for entity_name, attributes in firmware_entries
                for attribute_name, value in attributes.items()
            )
        )

    @staticmethod
    def _make_line(words: Iterable[bytes]) -> bytes:
        return b"|".join(words) + b"\n"

    def _has_gpu(self) -> bool:
        if self._command is None:
            return False

        # helper to sort out not installed GPU components
        self._logger.debug("Fetching inventory information via UDP from %s:623", self._command.bmc)
        try:
            inventory_entries = self._command.get_inventory_descriptions()
        except MKTimeout:
            raise
        except Exception as e:
            self._logger.debug("Failed to fetch inventory information: %r", e)
            self._logger.debug("Exception", exc_info=True)
            # in case of connection problems, we don't want to ignore possible
            # GPU entries
            return True

        return any("GPU" in line for line in inventory_entries)
