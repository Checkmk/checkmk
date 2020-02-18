#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import socket
from typing import Tuple, List, Optional  # pylint: disable=unused-import
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

    def set_port(self, port):
        # type: (int) -> None
        self._port = port

    def _get_port(self):
        # type: () -> int
        if self._port is not None:
            return self._port

        return self._host_config.agent_port

    def set_timeout(self, timeout):
        # type: (float) -> None
        self._timeout = timeout

    def _get_timeout(self):
        # type: () -> float
        if self._timeout:
            return self._timeout

        return self._host_config.tcp_connect_timeout

    def _execute(self):
        # type: () -> RawAgentData
        if self._use_only_cache:
            raise MKAgentError("Got no data: No usable cache file present at %s" %
                               self._cache_file_path())

        self._verify_ipaddress()

        port = self._get_port()

        encryption_settings = self._host_config.agent_encryption

        socktype = (socket.AF_INET6 if self._host_config.is_ipv6_primary else socket.AF_INET)
        s = socket.socket(socktype, socket.SOCK_STREAM)

        timeout = self._get_timeout()

        output_lines = []  # type: List[bytes]
        self._logger.debug("Connecting via TCP to %s:%d (%ss timeout)" %
                           (self._ipaddress, port, timeout))
        try:
            s.settimeout(timeout)
            s.connect((self._ipaddress, port))
            s.settimeout(None)

            self._logger.debug("Reading data from agent")

            while True:
                data = s.recv(4096, socket.MSG_WAITALL)

                if data and len(data) > 0:
                    output_lines.append(data)
                else:
                    break

        except socket.error as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKAgentError("Communication failed: %s" % e)
        finally:
            s.close()

        output = b''.join(output_lines)

        if len(output) == 0:  # may be caused by xinetd not allowing our address
            raise MKEmptyAgentData("Empty output from agent at TCP port %d" % port)

        if len(output) < 16:
            raise MKAgentError("Too short output from agent: %r" % output)

        output_is_plaintext = output.startswith(b"<<<")
        if encryption_settings["use_regular"] == "enforce" and output_is_plaintext:
            raise MKAgentError(
                "Agent output is plaintext but encryption is enforced by configuration")
        if not output_is_plaintext and encryption_settings["use_regular"] in ["enforce", "allow"]:
            try:
                # simply check if the protocol is an actual number
                protocol = int(output[0:2])

                output = self._decrypt_package(output[2:], encryption_settings["passphrase"],
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
    def _decrypt_package(self, encrypted_pkg, encryption_key, protocol):
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
        return decrypted_pkg[0:-ord(str(decrypted_pkg[-1]))]

    def describe(self):
        # type: () -> str
        """Return a short textual description of the agent"""
        return "TCP: %s:%d" % (self._ipaddress, self._host_config.agent_port)

    @classmethod
    def use_only_cache(cls):
        # type: () -> None
        cls._use_only_cache = True
