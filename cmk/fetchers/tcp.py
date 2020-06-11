#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import socket
from hashlib import sha256, md5
from types import TracebackType
from typing import Dict, List, Optional, Tuple, Type

from Cryptodome.Cipher import AES

import cmk.utils.debug
from cmk.utils.type_defs import HostAddress, RawAgentData

from ._base import AbstractDataFetcher, MKFetcherError


class TCPDataFetcher(AbstractDataFetcher):
    def __init__(
            self,
            family,  # type: socket.AddressFamily
            address,  # type: Tuple[HostAddress, int]
            timeout,  # type: float
            encryption_settings,  # type: Dict[str, str]
    ):
        # type (...) -> None
        super(TCPDataFetcher, self).__init__()
        self._family = socket.AddressFamily(family)
        self._address = address
        self._timeout = timeout
        self._encryption_settings = encryption_settings
        self._logger = logging.getLogger("cmk.fetchers.tcp")
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
            raise MKFetcherError("Not connected")

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
            return recvall(self._socket)
        except socket.error as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKFetcherError("Communication failed: %s" % e)

    def _decrypt(self, output):
        # type: (RawAgentData) -> RawAgentData
        if output.startswith(b"<<<"):
            self._logger.debug("Output is not encrypted")
            if self._encryption_settings["use_regular"] == "enforce":
                raise MKFetcherError(
                    "Agent output is plaintext but encryption is enforced by configuration")
            return output

        if self._encryption_settings["use_regular"] not in ["enforce", "allow"]:
            self._logger.debug("Output is not encrypted")
            return output

        try:
            self._logger.debug("Decrypt encrypted output")
            output = self._real_decrypt(output)
        except MKFetcherError:
            raise
        except Exception as e:
            if self._encryption_settings["use_regular"] == "enforce":
                raise MKFetcherError("Failed to decrypt agent output: %s" % e)

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
            raise MKFetcherError("Unsupported protocol version: %r" % output[:2])
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
