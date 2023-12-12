#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import logging
import socket
import ssl
import sys
from collections.abc import Mapping
from typing import Any, Final

import cmk.utils.debug
from cmk.utils import paths
from cmk.utils.agent_registration import get_uuid_link_manager
from cmk.utils.agentdatatype import AgentRawData
from cmk.utils.certs import write_cert_store
from cmk.utils.exceptions import MKFetcherError, MKTimeout
from cmk.utils.hostaddress import HostAddress, HostName

from ._abstract import Fetcher, Mode
from ._agentprtcl import (
    AgentCtlMessage,
    decrypt_by_agent_protocol,
    TCPEncryptionHandling,
    TransportProtocol,
    validate_agent_protocol,
)

if sys.version_info < (3, 12):
    from typing_extensions import Buffer
else:
    from collections.abc import Buffer


__all__ = ["TCPFetcher"]


def recvall(sock: socket.socket, flags: int = 0) -> bytes:
    buffer = bytearray()
    try:
        while True:
            data = sock.recv(4096, flags)
            if not data:
                break
            buffer += data
    except OSError as e:
        if cmk.utils.debug.enabled():
            raise
        raise MKFetcherError("Communication failed: %s" % e)

    return bytes(buffer)


def wrap_tls(sock: socket.socket, server_hostname: str) -> ssl.SSLSocket:
    if not paths.agent_cert_store.exists():
        # agent cert store should be written on agent receiver startup.
        # However, if it's missing for some reason, we have to write it.
        write_cert_store(source_dir=paths.agent_cas_dir, store_path=paths.agent_cert_store)
    try:
        ctx = ssl.create_default_context(cafile=str(paths.agent_cert_store))
        ctx.load_cert_chain(certfile=paths.site_cert_file)
        return ctx.wrap_socket(sock, server_hostname=server_hostname)
    except ssl.SSLError as e:
        raise MKFetcherError("Error establishing TLS connection") from e


class TCPFetcher(Fetcher[AgentRawData]):
    def __init__(
        self,
        *,
        family: socket.AddressFamily,
        address: tuple[HostAddress, int],
        timeout: float,
        host_name: HostName,
        encryption_handling: TCPEncryptionHandling,
        pre_shared_secret: str | None,
    ) -> None:
        super().__init__()
        self.family: Final = socket.AddressFamily(family)
        # json has no builtin tuple, we have to convert
        self.address: Final[tuple[HostAddress, int]] = (address[0], address[1])
        self.timeout: Final = timeout
        self.host_name: Final = host_name
        self.encryption_handling: Final = encryption_handling
        self.pre_shared_secret: Final = pre_shared_secret
        self._logger: Final = logging.getLogger("cmk.helper.tcp")
        self._opt_socket: socket.socket | None = None

    @property
    def _socket(self) -> socket.socket:
        if self._opt_socket is None:
            raise MKFetcherError("Not connected")
        return self._opt_socket

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}("
            + ", ".join(
                (
                    f"family={self.family!r}",
                    f"timeout={self.timeout!r}",
                    f"host_name={self.host_name!r}",
                    f"encryption_handling={self.encryption_handling!r}",
                    f"pre_shared_secret={self.pre_shared_secret!r}",
                )
            )
            + ")"
        )

    @classmethod
    def _from_json(cls, serialized: Mapping[str, Any]) -> "TCPFetcher":
        serialized_ = copy.deepcopy(dict(serialized))
        address: tuple[HostAddress, int] = serialized_.pop("address")
        host_name = HostName(serialized_.pop("host_name"))
        encryption_handling = TCPEncryptionHandling(serialized_.pop("encryption_handling"))
        return cls(
            address=address,
            host_name=host_name,
            encryption_handling=encryption_handling,
            **serialized_,
        )

    def to_json(self) -> Mapping[str, Any]:
        return {
            "family": self.family,
            "address": self.address,
            "timeout": self.timeout,
            "host_name": str(self.host_name),
            "encryption_handling": self.encryption_handling.value,
            "pre_shared_secret": self.pre_shared_secret,
        }

    def open(self) -> None:
        self._logger.debug(
            "Connecting via TCP to %s:%d (%ss timeout)",
            self.address[0],
            self.address[1],
            self.timeout,
        )
        self._opt_socket = socket.socket(self.family, socket.SOCK_STREAM)
        # For an explanation on these options have a look at tcp(7) (man tcp)
        self._opt_socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        self._opt_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 120)  # start after
        self._opt_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)  # wait between
        self._opt_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)  # how many tries
        try:
            self._socket.settimeout(self.timeout)
            self._socket.connect(self.address)
            # We can't set a specific timeout here, because we don't use the sockets in
            # "non-blocking" mode. However, we want to prevent a completely dead connection,
            # so we set the KEEPALIVE settings above.
            self._socket.settimeout(None)
        except OSError as e:
            self._close_socket()

            if cmk.utils.debug.enabled():
                raise
            raise MKFetcherError("Communication failed: %s" % e)

    def close(self) -> None:
        self._close_socket()

    def _close_socket(self) -> None:
        if self._opt_socket is None:
            return
        self._logger.debug("Closing TCP connection to %s:%d", self.address[0], self.address[1])
        self._opt_socket.close()
        self._opt_socket = None

    def _fetch_from_io(self, mode: Mode) -> AgentRawData:
        controller_uuid = get_uuid_link_manager().get_uuid(self.host_name)
        agent_data = self._get_agent_data(
            str(controller_uuid) if controller_uuid is not None else None
        )
        return agent_data

    def _from_tls(self, server_hostname: str) -> tuple[TransportProtocol, Buffer]:
        self._logger.debug("Reading data from agent via TLS socket")
        with wrap_tls(self._socket, server_hostname) as ssock:
            self._logger.debug("Reading data from agent")
            raw_agent_data = recvall(ssock)
        try:
            agent_data = AgentCtlMessage.from_bytes(raw_agent_data).payload
        except ValueError as e:
            raise MKFetcherError(f"Failed to deserialize versioned agent data: {e!r}") from e

        if len(memoryview(agent_data)) <= 2:
            raise MKFetcherError("Empty payload from controller at %s:%d" % self.address)

        try:
            # I don't understand that recursive protocol thing.
            protocol = TransportProtocol.from_bytes(agent_data)
        except ValueError:
            raise MKFetcherError(
                f"Unknown transport protocol: {bytes(memoryview(agent_data)[:2])!r}"
            )

        self._logger.debug("Detected transport protocol: %s", protocol)
        return protocol, memoryview(agent_data)[2:]

    def _get_agent_data(self, server_hostname: str | None) -> AgentRawData:
        try:
            raw_protocol = self._socket.recv(2, socket.MSG_WAITALL)
        except OSError as e:
            raise MKFetcherError(f"Communication failed: {e}") from e

        if not raw_protocol:
            raise MKFetcherError("Empty output from host %s:%d" % self.address)

        try:
            protocol = TransportProtocol.from_bytes(raw_protocol)
        except ValueError:
            raise MKFetcherError(f"Unknown transport protocol: {raw_protocol!r}")

        self._logger.debug("Detected transport protocol: %s", protocol)
        validate_agent_protocol(
            protocol, self.encryption_handling, is_registered=server_hostname is not None
        )

        if protocol is TransportProtocol.TLS:
            if server_hostname is None:
                raise MKFetcherError("Agent controller not registered")

            protocol, output = self._from_tls(server_hostname)
        else:
            self._logger.debug("Reading data from agent")
            output = recvall(self._socket, socket.MSG_WAITALL)

        if not output:
            return AgentRawData(b"")  # nothing to to, validation will fail

        if protocol is TransportProtocol.PLAIN:
            return AgentRawData(protocol.value + output)  # bring back stolen bytes

        if (secret := self.pre_shared_secret) is None:
            raise MKFetcherError("Data is encrypted but no secret is known")

        self._logger.debug("Try to decrypt output")
        try:
            return AgentRawData(decrypt_by_agent_protocol(secret, protocol, output))
        except MKTimeout:
            raise
        except Exception as e:
            raise MKFetcherError("Failed to decrypt agent output: %r" % e) from e
