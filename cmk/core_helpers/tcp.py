#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import socket
from hashlib import md5, sha256
from typing import Any, Dict, Final, List, Mapping, Optional, Tuple

from Cryptodome.Cipher import AES

import cmk.utils.debug
from cmk.utils.exceptions import MKFetcherError
from cmk.utils.type_defs import AgentRawData, HostAddress

from ._base import verify_ipaddress
from .agent import AgentFetcher, DefaultAgentFileCache
from .type_defs import Mode


class TCPFetcher(AgentFetcher):
    def __init__(
        self,
        file_cache: DefaultAgentFileCache,
        *,
        family: socket.AddressFamily,
        address: Tuple[Optional[HostAddress], int],
        timeout: float,
        encryption_settings: Mapping[str, str],
        use_only_cache: bool,
    ) -> None:
        super().__init__(file_cache, logging.getLogger("cmk.helper.tcp"))
        self.family: Final = socket.AddressFamily(family)
        # json has no builtin tuple, we have to convert
        self.address: Final[Tuple[Optional[HostAddress], int]] = (address[0], address[1])
        self.timeout: Final = timeout
        self.encryption_settings: Final = encryption_settings
        self.use_only_cache: Final = use_only_cache
        self._socket: Optional[socket.socket] = None

    @classmethod
    def _from_json(cls, serialized: Dict[str, Any]) -> "TCPFetcher":
        address: Tuple[Optional[HostAddress], int] = serialized.pop("address")
        return cls(
            DefaultAgentFileCache.from_json(serialized.pop("file_cache")),
            address=address,
            **serialized,
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "file_cache": self.file_cache.to_json(),
            "family": self.family,
            "address": self.address,
            "timeout": self.timeout,
            "encryption_settings": self.encryption_settings,
            "use_only_cache": self.use_only_cache,
        }

    def open(self) -> None:
        verify_ipaddress(self.address[0])
        self._logger.debug(
            "Connecting via TCP to %s:%d (%ss timeout)",
            self.address[0],
            self.address[1],
            self.timeout,
        )
        self._socket = socket.socket(self.family, socket.SOCK_STREAM)
        try:
            self._socket.settimeout(self.timeout)
            self._socket.connect(self.address)
            self._socket.settimeout(None)
        except socket.error as e:
            self._socket.close()
            self._socket = None

            if cmk.utils.debug.enabled():
                raise
            raise MKFetcherError("Communication failed: %s" % e)

    def close(self) -> None:
        self._logger.debug("Closing TCP connection to %s:%d", self.address[0], self.address[1])
        if self._socket is not None:
            self._socket.close()
        self._socket = None

    def _is_cache_read_enabled(self, mode: Mode) -> bool:
        return mode not in (Mode.CHECKING, Mode.FORCE_SECTIONS)

    def _is_cache_write_enabled(self, mode: Mode) -> bool:
        return True

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        if self.use_only_cache:
            raise MKFetcherError("Got no data: No usable cache file present at %s" %
                                 self.file_cache.path)
        if self._socket is None:
            raise MKFetcherError("Not connected")

        return self._validate_decrypted_data(self._decrypt(self._raw_data()))

    def _raw_data(self) -> AgentRawData:
        self._logger.debug("Reading data from agent")
        if not self._socket:
            return AgentRawData(b"")

        def recvall(sock: socket.socket) -> bytes:
            buffer: List[bytes] = []
            while True:
                data = sock.recv(4096, socket.MSG_WAITALL)
                if not data:
                    break
                buffer.append(data)
            return b"".join(buffer)

        try:
            return AgentRawData(recvall(self._socket))
        except socket.error as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKFetcherError("Communication failed: %s" % e)

    def _decrypt(self, output: AgentRawData) -> AgentRawData:
        if not output:
            return output  # nothing to to, validation will fail

        if output.startswith(b"<<<"):
            self._logger.debug("Output is not encrypted")
            if self.encryption_settings["use_regular"] == "enforce":
                raise MKFetcherError(
                    "Agent output is plaintext but encryption is enforced by configuration")
            return output

        self._logger.debug("Output is encrypted or invalid")
        if self.encryption_settings["use_regular"] == "disable":
            raise MKFetcherError(
                "Agent output is either invalid or encrypted but encryption is disabled by configuration"
            )

        try:
            self._logger.debug("Try to decrypt output")
            output = self._real_decrypt(output)
        except MKFetcherError:
            raise
        except Exception as e:
            if self.encryption_settings["use_regular"] == "enforce":
                raise MKFetcherError("Failed to decrypt agent output: %s" % e)

        # of course the package might indeed have been encrypted but
        # in an incorrect format, but how would we find that out?
        # In this case processing the output will fail
        return output

    def _validate_decrypted_data(self, output: AgentRawData) -> AgentRawData:
        if not output:  # may be caused by xinetd not allowing our address
            raise MKFetcherError("Empty output from agent at %s:%d" % self.address)
        if len(output) < 16:
            raise MKFetcherError("Too short output from agent: %r" % output)
        return output

    # TODO: Sync with real_type_checks._decrypt_rtc_package
    def _real_decrypt(self, output: AgentRawData) -> AgentRawData:
        try:
            # simply check if the protocol is an actual number
            protocol = int(output[:2])
        except ValueError:
            raise MKFetcherError("Unsupported protocol version: %r" % output[:2])
        encrypted_pkg = output[2:]
        encryption_key = self.encryption_settings["passphrase"]

        encrypt_digest = sha256 if protocol == 2 else md5

        # Adapt OpenSSL handling of key and iv
        def derive_key_and_iv(password: bytes, key_length: int,
                              iv_length: int) -> Tuple[bytes, bytes]:
            d = d_i = b''
            while len(d) < key_length + iv_length:
                d_i = encrypt_digest(d_i + password).digest()
                d += d_i
            return d[:key_length], d[key_length:key_length + iv_length]

        key, iv = derive_key_and_iv(encryption_key.encode("utf-8"), 32, AES.block_size)
        decryption_suite = AES.new(key, AES.MODE_CBC, iv)
        decrypted_pkg = decryption_suite.decrypt(encrypted_pkg)
        # Strip of fill bytes of openssl
        return AgentRawData(decrypted_pkg[0:-decrypted_pkg[-1]])
