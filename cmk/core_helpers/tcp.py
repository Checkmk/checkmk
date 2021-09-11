#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import logging
import socket
from typing import Any, Final, List, Mapping, Optional, Tuple

import cmk.utils.debug
from cmk.utils.encryption import decrypt_by_agent_protocol, DigestType
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

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"{type(self.file_cache).__name__}",
                    f"family={self.family!r}",
                    f"timeout={self.timeout!r}",
                    f"encryption_settings={self.encryption_settings!r}",
                    f"use_only_cache={self.use_only_cache!r}",
                )
            )
            + ")"
        )

    @classmethod
    def _from_json(cls, serialized: Mapping[str, Any]) -> "TCPFetcher":
        serialized_ = copy.deepcopy(dict(serialized))
        address: Tuple[Optional[HostAddress], int] = serialized_.pop("address")
        return cls(
            DefaultAgentFileCache.from_json(serialized_.pop("file_cache")),
            address=address,
            **serialized_,
        )

    def to_json(self) -> Mapping[str, Any]:
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

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        if self.use_only_cache:
            raise MKFetcherError(
                "Got no data: No usable cache file present at %s" % self.file_cache.base_path
            )
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
                    "Agent output is plaintext but encryption is enforced by configuration"
                )
            return output

        self._logger.debug("Output is encrypted or invalid")
        if self.encryption_settings["use_regular"] == "disable":
            raise MKFetcherError(
                "Agent output is either invalid or encrypted but encryption is disabled by configuration"
            )

        try:
            self._logger.debug("Try to decrypt output")
            output = self._decrypt_agent_data(output=output)
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

    def _decrypt_agent_data(self, output: AgentRawData) -> AgentRawData:
        try:
            protocol = DigestType(output[:2])
        except ValueError as exc:
            raise MKFetcherError from exc

        return AgentRawData(
            decrypt_by_agent_protocol(
                self.encryption_settings["passphrase"],
                protocol,
                output[2:],
            )
        )
