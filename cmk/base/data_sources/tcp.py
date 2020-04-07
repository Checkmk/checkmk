#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from logging import Logger  # pylint: disable=unused-import
import socket
from types import TracebackType  # pylint: disable=unused-import
from typing import Dict, List, Optional, Tuple, Type  # pylint: disable=unused-import
from hashlib import sha256, md5
from Cryptodome.Cipher import AES

import cmk.utils.debug
import cmk.utils.werks

from cmk.base.exceptions import MKAgentError, MKEmptyAgentData
from cmk.utils.type_defs import (  # pylint: disable=unused-import
    HostName, HostAddress,
)
from cmk.base.check_utils import RawAgentData  # pylint: disable=unused-import

from .abstract import CheckMKAgentDataSource, verify_ipaddress

#.
#   .--Agent---------------------------------------------------------------.
#   |                        _                    _                        |
#   |                       / \   __ _  ___ _ __ | |_                      |
#   |                      / _ \ / _` |/ _ \ '_ \| __|                     |
#   |                     / ___ \ (_| |  __/ | | | |_                      |
#   |                    /_/   \_\__, |\___|_| |_|\__|                     |
#   |                            |___/                                     |
#   +----------------------------------------------------------------------+
#   | Real communication with the target system.                           |
#   '----------------------------------------------------------------------'


class TCPDataFetcher(object):  # pylint: disable=useless-object-inheritance
    def __init__(self, family, address, timeout, encryption_settings, logger):
        super(TCPDataFetcher, self).__init__()
        self._family = family  # type: socket.AddressFamily
        self._address = address  # type: Tuple[HostAddress, int]
        self._timeout = timeout  # type: float
        self._encryption_settings = encryption_settings  # type: Dict[str, str]
        self._logger = logger  # type: Logger
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


class TCPDataSource(CheckMKAgentDataSource):
    _use_only_cache = False

    def __init__(self, hostname, ipaddress):
        # type: (HostName, Optional[HostAddress]) -> None
        super(TCPDataSource, self).__init__(hostname, ipaddress)
        self._port = None  # type: Optional[int]
        self._timeout = None  # type: Optional[float]

    def id(self):
        # type: () -> str
        return "agent"

    @property
    def port(self):
        # type: () -> int
        if self._port is None:
            return self._host_config.agent_port
        return self._port

    @port.setter
    def port(self, value):
        # type: (Optional[int]) -> None
        self._port = value

    @property
    def timeout(self):
        # type: () -> float
        if self._timeout is None:
            return self._host_config.tcp_connect_timeout
        return self._timeout

    @timeout.setter
    def timeout(self, value):
        # type: (Optional[float]) -> None
        self._timeout = value

    def _execute(self):
        # type: () -> RawAgentData
        if self._use_only_cache:
            raise MKAgentError("Got no data: No usable cache file present at %s" %
                               self._cache_file_path())

        verify_ipaddress(self._ipaddress)

        with TCPDataFetcher(
                socket.AF_INET6 if self._host_config.is_ipv6_primary else socket.AF_INET,
            (self._ipaddress, self.port),
                self.timeout,
                self._host_config.agent_encryption,
                self._logger,
        ) as fetcher:
            output = fetcher.data()

        if len(output) < 16:
            raise MKAgentError("Too short output from agent: %r" % output)

        return output

    def describe(self):
        # type: () -> str
        """Return a short textual description of the agent"""
        return "TCP: %s:%d" % (self._ipaddress, self._host_config.agent_port)

    @classmethod
    def use_only_cache(cls):
        # type: () -> None
        cls._use_only_cache = True
