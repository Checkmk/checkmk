#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import json
import logging  # pylint: disable=unused-import
import os
import signal
import socket
import subprocess
from hashlib import sha256, md5
from types import TracebackType
from typing import Dict, List, Optional, Text, Tuple, Type, Union

from Cryptodome.Cipher import AES
import pyghmi.constants as ipmi_const  # type: ignore[import]
import pyghmi.ipmi.command as ipmi_cmd  # type: ignore[import]
import pyghmi.ipmi.sdr as ipmi_sdr  # type: ignore[import]
from pyghmi.exceptions import IpmiException  # type: ignore[import]
import six

import cmk.base.config as config  # pylint: disable=cmk-module-layer-violation
import cmk.utils
import cmk.utils.debug
# pylint: disable=cmk-module-layer-violation
import cmk.base.snmp as snmp
from cmk.base.api.agent_based.section_types import SNMPTree
from cmk.base.check_utils import section_name_of, RawAgentData, ServiceCheckResult
from cmk.base.exceptions import MKAgentError, MKEmptyAgentData
from cmk.base.snmp_utils import OIDInfo, RawSNMPData, SNMPHostConfig, SNMPTable
# pylint: enable=cmk-module-layer-violation
from cmk.utils.encoding import ensure_bytestr
from cmk.utils.exceptions import MKTimeout
from cmk.utils.log import VERBOSE
from cmk.utils.piggyback import (
    get_piggyback_raw_data,
    PiggybackRawDataInfo,
    PiggybackTimeSettings,
)
from cmk.utils.type_defs import HostName, HostAddress


class AbstractDataFetcher(six.with_metaclass(abc.ABCMeta, object)):
    """Interface to the data fetchers."""
    @abc.abstractmethod
    def __enter__(self):
        # type: () -> AbstractDataFetcher
        """Prepare the data source."""

    @abc.abstractmethod
    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> Optional[bool]
        """Destroy the data source."""

    @abc.abstractmethod
    def data(self):
        # type: () -> RawAgentData
        """Return the data from the source."""


class IPMIDataFetcher(AbstractDataFetcher):
    def __init__(
        self,
        ipaddress,  # type: HostAddress
        username,  # type: str
        password,  # type: str
        logger,  # type: logging.Logger
    ):
        # type: (...) -> None
        super(IPMIDataFetcher, self).__init__()
        self._ipaddress = ipaddress
        self._username = username
        self._password = password
        self._logger = logger
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
                sensors.append(IPMIDataFetcher._parse_sensor_reading(number, reading))

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
            # workaround for pyghmi bug: https://bugs.launchpad.net/pyghmi/+bug/1790120
            health_txt = IPMIDataFetcher._handle_false_positive_warnings(reading)
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

    @staticmethod
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


class PiggyBackDataFetcher(AbstractDataFetcher):
    def __init__(
        self,
        hostname,  # type: HostName
        ipaddress,  # type: Optional[HostAddress]
        time_settings  # type: List[Tuple[Optional[str], str, int]]
    ):
        # type: (...) -> None
        super(PiggyBackDataFetcher, self).__init__()
        self._hostname = hostname
        self._ipaddress = ipaddress
        self._time_settings = time_settings
        self._sources = []  # type: List[PiggybackRawDataInfo]

    def __enter__(self):
        # type: () -> PiggyBackDataFetcher
        for origin in (self._hostname, self._ipaddress):
            self._sources.extend(PiggyBackDataFetcher._raw_data(origin, self._time_settings))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None
        self._sources.clear()

    def data(self):
        # type: () -> RawAgentData
        raw_data = b""
        raw_data += self._get_main_section()
        raw_data += self._get_source_labels_section()
        return raw_data

    def summary(self):
        # type: () -> ServiceCheckResult
        states = [0]
        infotexts = set()
        for src in self._sources:
            states.append(src.reason_status)
            infotexts.add(src.reason)
        return max(states), ", ".join(infotexts), []

    def _get_main_section(self):
        # type: () -> RawAgentData
        raw_data = b""
        for src in self._sources:
            if src.successfully_processed:
                # !! Important for Check_MK and Check_MK Discovery service !!
                #   - sources contains ALL file infos and is not filtered
                #     in cmk/base/piggyback.py as in previous versions
                #   - Check_MK gets the processed file info reasons and displays them in
                #     it's service details
                #   - Check_MK Discovery: Only shows vanished/new/... if raw data is not
                #     added; ie. if file_info is not successfully processed
                raw_data += src.raw_data
        return raw_data

    def _get_source_labels_section(self):
        # type: () -> RawAgentData
        """Return a <<<labels>>> agent section which adds the piggyback sources
        to the labels of the current host"""
        if not self._sources:
            return b""

        labels = {"cmk/piggyback_source_%s" % src.source_hostname: "yes" for src in self._sources}
        return b'<<<labels:sep(0)>>>\n%s\n' % json.dumps(labels).encode("utf-8")

    @staticmethod
    def _raw_data(hostname, time_settings):
        # type: (Optional[str], PiggybackTimeSettings) -> List[PiggybackRawDataInfo]
        return get_piggyback_raw_data(hostname if hostname else "", time_settings)


class SNMPDataFetcher:
    def __init__(
        self,
        oid_infos,  # type: Dict[str, Union[OIDInfo, List[SNMPTree]]]
        use_snmpwalk_cache,  # type: bool
        snmp_config,  # type: SNMPHostConfig
        logger,  # type: logging.Logger
    ):
        # type (...) -> None
        super(SNMPDataFetcher, self).__init__()
        self._oid_infos = oid_infos
        self._use_snmpwalk_cache = use_snmpwalk_cache
        self._snmp_config = snmp_config
        self._logger = logger

    def __enter__(self):
        # type: () -> SNMPDataFetcher
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None
        pass

    def data(self):
        # type: () -> RawSNMPData
        info = {}  # type: RawSNMPData
        for check_plugin_name, oid_info in self._oid_infos.items():
            section_name = section_name_of(check_plugin_name)
            # Prevent duplicate data fetching of identical section in case of SNMP sub checks
            if section_name in info:
                self._logger.debug("%s: Skip fetching data (section already fetched)",
                                   check_plugin_name)
                continue

            self._logger.debug("%s: Fetching data", check_plugin_name)

            # oid_info can now be a list: Each element  of that list is interpreted as one real oid_info
            # and fetches a separate snmp table.
            get_snmp = snmp.get_snmp_table_cached if self._use_snmpwalk_cache else snmp.get_snmp_table
            if isinstance(oid_info, list):
                check_info = []  # type: List[SNMPTable]
                for entry in oid_info:
                    check_info_part = get_snmp(self._snmp_config, check_plugin_name, entry)
                    check_info.append(check_info_part)
                info[section_name] = check_info
            else:
                info[section_name] = get_snmp(self._snmp_config, check_plugin_name, oid_info)
        return info


class ProgramDataFetcher(AbstractDataFetcher):
    def __init__(
        self,
        cmdline,  # type: Union[bytes, Text]
        stdin,  # type: Optional[str]
        logger,  # type: logging.Logger
    ):
        # type: (...) -> None
        super(ProgramDataFetcher, self).__init__()
        self._cmdline = cmdline
        self._stdin = stdin
        self._logger = logger
        self._process = None  # type: Optional[subprocess.Popen]

    def __enter__(self):
        # type: () -> ProgramDataFetcher
        if config.monitoring_core == "cmc":
            # Warning:
            # The preexec_fn parameter is not safe to use in the presence of threads in your
            # application. The child process could deadlock before exec is called. If you
            # must use it, keep it trivial! Minimize the number of libraries you call into.
            #
            # Note:
            # If you need to modify the environment for the child use the env parameter
            # rather than doing it in a preexec_fn. The start_new_session parameter can take
            # the place of a previously common use of preexec_fn to call os.setsid() in the
            # child.
            self._process = subprocess.Popen(
                self._cmdline,
                shell=True,
                stdin=subprocess.PIPE if self._stdin else open(os.devnull),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                close_fds=True,
            )
        else:
            # We can not create a separate process group when running Nagios
            # Upon reaching the service_check_timeout Nagios only kills the process
            # group of the active check.
            self._process = subprocess.Popen(
                self._cmdline,
                shell=True,
                stdin=subprocess.PIPE if self._stdin else open(os.devnull),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                close_fds=True,
            )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None
        if self._process is None:
            return
        if exc_type is MKTimeout:
            # On timeout exception try to stop the process to prevent child process "leakage"
            os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
            self._process.wait()
        # The stdout and stderr pipe are not closed correctly on a MKTimeout
        # Normally these pipes getting closed after p.communicate finishes
        # Closing them a second time in a OK scenario won't hurt neither..
        if self._process.stdout is None or self._process.stderr is None:
            raise Exception("stdout needs to be set")
        self._process.stdout.close()
        self._process.stderr.close()
        self._process = None

    def data(self):
        # type: () -> RawAgentData
        if self._process is None:
            raise MKAgentError("No process")
        stdout, stderr = self._process.communicate(
            input=ensure_bytestr(self._stdin) if self._stdin else None)
        if self._process.returncode == 127:
            exepath = self._cmdline.split()[0]  # for error message, hide options!
            raise MKAgentError("Program '%s' not found (exit code 127)" % six.ensure_str(exepath))
        if self._process.returncode:
            raise MKAgentError("Agent exited with code %d: %s" %
                               (self._process.returncode, six.ensure_str(stderr)))
        return stdout


class TCPDataFetcher(AbstractDataFetcher):
    def __init__(
        self,
        family,  # type: socket.AddressFamily
        address,  # type: Tuple[HostAddress, int]
        timeout,  # type: float
        encryption_settings,  # type: Dict[str, str]
        logger,  # type: logging.Logger
    ):
        # type (...) -> None
        super(TCPDataFetcher, self).__init__()
        self._family = family
        self._address = address
        self._timeout = timeout
        self._encryption_settings = encryption_settings
        self._logger = logger
        self._socket = None  # type: Optional[socket.socket]

    def __enter__(self):
        # type: () -> TCPDataFetcher
        self._logger.debug("Connecting via TCP to %s:%d (%ss timeout)", self._address[0],
                           self._address[1], self._timeout)
        self._socket = socket.socket(self._family, socket.SOCK_STREAM)
        try:
            self._socket.settimeout(self._timeout)
            self._socket.connect(self._address)
            self._socket.settimeout(None)
        except socket.error:
            self._socket.close()
            self._socket = None
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # type: (Optional[Type[BaseException]], Optional[BaseException], Optional[TracebackType]) -> None
        self._logger.debug("Closing TCP connection to %s:%d", self._address[0], self._address[1])
        if self._socket is not None:
            self._socket.close()
        self._socket = None

    def data(self):
        # type: () -> RawAgentData
        if self._socket is None:
            raise MKAgentError("Not connected")

        return self._decrypt(self._raw_data())

    def _raw_data(self):
        # type: () -> RawAgentData
        self._logger.debug("Reading data from agent")
        if not self._socket:
            return b""

        def recvall(sock):
            # type: (socket.socket) -> bytes
            buffer = []  # type: List[bytes]
            while True:
                data = sock.recv(4096, socket.MSG_WAITALL)
                if not data:
                    break
                buffer.append(data)
            return b"".join(buffer)

        try:
            output = recvall(self._socket)
            if not output:  # may be caused by xinetd not allowing our address
                raise MKEmptyAgentData("Empty output from agent at %s:%d" % self._address)
            return output
        except socket.error as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKAgentError("Communication failed: %s" % e)

    def _decrypt(self, output):
        # type: (RawAgentData) -> RawAgentData
        if output.startswith(b"<<<"):
            self._logger.debug("Output is not encrypted")
            if self._encryption_settings["use_regular"] == "enforce":
                raise MKAgentError(
                    "Agent output is plaintext but encryption is enforced by configuration")
            return output

        if self._encryption_settings["use_regular"] not in ["enforce", "allow"]:
            self._logger.debug("Output is not encrypted")
            return output

        try:
            self._logger.debug("Decrypt encrypted output")
            output = self._real_decrypt(output)
        except MKAgentError:
            raise
        except Exception as e:
            if self._encryption_settings["use_regular"] == "enforce":
                raise MKAgentError("Failed to decrypt agent output: %s" % e)

            # of course the package might indeed have been encrypted but
            # in an incorrect format, but how would we find that out?
            # In this case processing the output will fail

        return output

    # TODO: Sync with real_type_checks._decrypt_rtc_package
    def _real_decrypt(self, output):
        # type: (RawAgentData) -> RawAgentData
        try:
            # simply check if the protocol is an actual number
            protocol = int(output[:2])
        except ValueError:
            raise MKAgentError("Unsupported protocol version: %r" % output[:2])
        encrypted_pkg = output[2:]
        encryption_key = self._encryption_settings["passphrase"]

        encrypt_digest = sha256 if protocol == 2 else md5

        # Adapt OpenSSL handling of key and iv
        def derive_key_and_iv(password, key_length, iv_length):
            # type: (bytes, int, int) -> Tuple[bytes, bytes]
            d = d_i = b''
            while len(d) < key_length + iv_length:
                d_i = encrypt_digest(d_i + password).digest()
                d += d_i
            return d[:key_length], d[key_length:key_length + iv_length]

        key, iv = derive_key_and_iv(encryption_key.encode("utf-8"), 32, AES.block_size)
        decryption_suite = AES.new(key, AES.MODE_CBC, iv)
        decrypted_pkg = decryption_suite.decrypt(encrypted_pkg)
        # Strip of fill bytes of openssl
        return decrypted_pkg[0:-decrypted_pkg[-1]]
