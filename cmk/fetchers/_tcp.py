#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
import enum
import logging
import socket
import ssl
from collections.abc import Mapping
from typing import Any, assert_never, Final
from uuid import UUID

import cmk.utils.debug
from cmk.utils import paths
from cmk.utils.agent_registration import get_uuid_link_manager
from cmk.utils.certs import write_cert_store
from cmk.utils.encryption import decrypt_by_agent_protocol, TransportProtocol
from cmk.utils.exceptions import MKFetcherError
from cmk.utils.type_defs import AgentRawData, HostAddress, HostName

from cmk.fetchers import Fetcher, Mode

from ._agentctl import AgentCtlMessage

__all__ = ["TCPEncryptionHandling", "TCPFetcher"]


class TCPEncryptionHandling(enum.Enum):
    TLS_ENCRYPTED_ONLY = enum.auto()
    ANY_ENCRYPTED = enum.auto()
    ANY_AND_PLAIN = enum.auto()


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
        super().__init__(logger=logging.getLogger("cmk.helper.tcp"))
        self.family: Final = socket.AddressFamily(family)
        # json has no builtin tuple, we have to convert
        self.address: Final[tuple[HostAddress, int]] = (address[0], address[1])
        self.timeout: Final = timeout
        self.host_name: Final = host_name
        self.encryption_handling: Final = encryption_handling
        self.pre_shared_secret: Final = pre_shared_secret
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
        agent_data, protocol = self._get_agent_data()
        return self._validate_decrypted_data(self._decrypt(protocol, agent_data))

    def _get_agent_data(self) -> tuple[AgentRawData, TransportProtocol]:
        try:
            raw_protocol = self._socket.recv(2, socket.MSG_WAITALL)
        except OSError as e:
            raise MKFetcherError(f"Communication failed: {e}") from e

        protocol = self._detect_transport_protocol(
            raw_protocol, empty_msg="Empty output from host %s:%d" % self.address
        )

        controller_uuid = get_uuid_link_manager().get_uuid(self.host_name)
        self._validate_protocol(protocol, is_registered=controller_uuid is not None)

        if protocol is TransportProtocol.TLS:
            with self._wrap_tls(controller_uuid) as ssock:
                raw_agent_data = self._recvall(ssock)
            try:
                agent_data = AgentCtlMessage.from_bytes(raw_agent_data).payload
            except ValueError as e:
                raise MKFetcherError(f"Failed to deserialize versioned agent data: {e!r}") from e
            return AgentRawData(agent_data[2:]), self._detect_transport_protocol(
                agent_data[:2], empty_msg="Empty payload from controller at %s:%d" % self.address
            )

        return AgentRawData(self._recvall(self._socket, socket.MSG_WAITALL)), protocol

    def _detect_transport_protocol(self, raw_protocol: bytes, empty_msg: str) -> TransportProtocol:
        try:
            protocol = TransportProtocol(raw_protocol)
            self._logger.debug(f"Detected transport protocol: {protocol} ({raw_protocol!r})")
            return protocol
        except ValueError:
            if raw_protocol:
                raise MKFetcherError(f"Unknown transport protocol: {raw_protocol!r}")
            raise MKFetcherError(empty_msg)

    def _validate_protocol(self, protocol: TransportProtocol, is_registered: bool) -> None:
        if protocol is TransportProtocol.TLS:
            return

        if is_registered:
            raise MKFetcherError("Refused: Host is registered for TLS but not using it")

        match self.encryption_handling:
            case TCPEncryptionHandling.TLS_ENCRYPTED_ONLY:
                raise MKFetcherError("Refused: TLS is enforced but host is not using it")
            case TCPEncryptionHandling.ANY_ENCRYPTED:
                if protocol is TransportProtocol.PLAIN:
                    raise MKFetcherError(
                        "Refused: Encryption is enforced but agent output is plaintext"
                    )
            case TCPEncryptionHandling.ANY_AND_PLAIN:
                pass
            case never:
                assert_never(never)

    def _wrap_tls(self, controller_uuid: UUID | None) -> ssl.SSLSocket:
        if controller_uuid is None:
            raise MKFetcherError("Agent controller not registered")

        self._logger.debug("Reading data from agent via TLS socket")
        if not paths.agent_cert_store.exists():
            # agent cert store should be written on agent receiver startup.
            # However, if it's missing for some reason, we have to write it.
            write_cert_store(source_dir=paths.agent_cas_dir, store_path=paths.agent_cert_store)
        try:
            ctx = ssl.create_default_context(cafile=str(paths.agent_cert_store))
            ctx.load_cert_chain(certfile=paths.site_cert_file)
            return ctx.wrap_socket(self._socket, server_hostname=str(controller_uuid))
        except ssl.SSLError as e:
            raise MKFetcherError("Error establishing TLS connection") from e

    def _recvall(self, sock: socket.socket, flags: int = 0) -> bytes:
        self._logger.debug("Reading data from agent")
        buffer: list[bytes] = []
        try:
            while True:
                data = sock.recv(4096, flags)
                if not data:
                    break
                buffer.append(data)
        except OSError as e:
            if cmk.utils.debug.enabled():
                raise
            raise MKFetcherError("Communication failed: %s" % e)

        return b"".join(buffer)

    def _decrypt(self, protocol: TransportProtocol, output: AgentRawData) -> AgentRawData:
        if not output:
            return output  # nothing to to, validation will fail

        if protocol is TransportProtocol.PLAIN:
            return protocol.value + output  # bring back stolen bytes

        if (secret := self.pre_shared_secret) is None:
            raise MKFetcherError("Data is encrypted but no secret is known")

        self._logger.debug("Try to decrypt output")
        try:
            return AgentRawData(decrypt_by_agent_protocol(secret, protocol, output))
        except Exception as e:
            raise MKFetcherError("Failed to decrypt agent output: %s" % e) from e

    def _validate_decrypted_data(self, output: AgentRawData) -> AgentRawData:
        if len(output) < 16:
            raise MKFetcherError(
                f"Too short payload from agent at {self.address[0]}:{self.address[1]}: {output!r}"
            )
        return output
