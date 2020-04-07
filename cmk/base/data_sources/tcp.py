#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging  # pylint: disable=unused-import
import socket
from typing import Dict, List, Tuple, Optional  # pylint: disable=unused-import
from hashlib import sha256, md5
from Cryptodome.Cipher import AES

import cmk.utils.debug
import cmk.utils.werks

from cmk.base.exceptions import MKAgentError, MKEmptyAgentData
from cmk.utils.type_defs import (  # pylint: disable=unused-import
    HostName, HostAddress,
)
from cmk.base.check_utils import RawAgentData  # pylint: disable=unused-import

from .abstract import CheckMKAgentDataSource

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

        self._verify_ipaddress()

        output = self._fetch_raw_data(
            socket.socket(socket.AF_INET6 if self._host_config.is_ipv6_primary else socket.AF_INET,
                          socket.SOCK_STREAM), (
                              self._ipaddress,
                              self.port,
                          ), self.timeout, self._logger)

        if not output:  # may be caused by xinetd not allowing our address
            raise MKEmptyAgentData("Empty output from agent at TCP port %s" % self.port)

        if len(output) < 16:
            raise MKAgentError("Too short output from agent: %r" % output)

        output = self._decrypt(output, self._host_config.agent_encryption)
        return output

    @staticmethod
    def _fetch_raw_data(sock, address, timeout, logger):
        # type: (socket.socket, Tuple[Optional[str], int], float, logging.Logger) -> RawAgentData
        output_lines = []  # type: List[bytes]
        logger.debug("Connecting via TCP to %s:%d (%ss timeout)", address[0], address[1], timeout)
        try:
            sock.settimeout(timeout)
            sock.connect(address)
            sock.settimeout(None)

            logger.debug("Reading data from agent")

            while True:
                data = sock.recv(4096, socket.MSG_WAITALL)
                if not data:
                    break
                output_lines.append(data)

        except socket.error as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKAgentError("Communication failed: %s" % e)
        finally:
            sock.close()

        return b''.join(output_lines)

    @staticmethod
    def _decrypt(output, encryption_settings):
        # type: (RawAgentData, Dict[str, str]) -> RawAgentData
        if output.startswith(b"<<<"):
            # The output is not encrypted.
            if encryption_settings["use_regular"] == "enforce":
                raise MKAgentError(
                    "Agent output is plaintext but encryption is enforced by configuration")
            return output

        if encryption_settings["use_regular"] not in ["enforce", "allow"]:
            return output

        try:
            # simply check if the protocol is an actual number
            protocol = int(output[0:2])

            output = TCPDataSource._decrypt_package(output[2:], encryption_settings["passphrase"],
                                                    protocol)
        except ValueError:
            raise MKAgentError("Unsupported protocol version: %s" % str(output[:2]))
        except Exception as e:
            if encryption_settings["use_regular"] == "enforce":
                raise MKAgentError("Failed to decrypt agent output: %s" % e)

            # of course the package might indeed have been encrypted but
            # in an incorrect format, but how would we find that out?
            # In this case processing the output will fail

        return output

    # TODO: Sync with real_type_checks._decrypt_rtc_package
    @staticmethod
    def _decrypt_package(encrypted_pkg, encryption_key, protocol):
        # type: (bytes, str, int) -> RawAgentData
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

    def describe(self):
        # type: () -> str
        """Return a short textual description of the agent"""
        return "TCP: %s:%d" % (self._ipaddress, self._host_config.agent_port)

    @classmethod
    def use_only_cache(cls):
        # type: () -> None
        cls._use_only_cache = True
