#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""In-process LDAP mock for the user identity & auth composition tests.

A lightweight stand-in for the ``osixia/openldap`` container that serves the
shared :class:`Directory`, so the LDAP-backed tests run without Docker. Mirrors
:class:`LdapContainer`'s public surface so fixtures stay backend-agnostic.
"""

from __future__ import annotations

import logging
import socket
import socketserver
import threading
from types import TracebackType
from typing import cast, Self

from tests.system.multisite.identity.directory import Directory

logger = logging.getLogger("identity-tests")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _encode_length(n: int) -> bytes:
    if n < 0x80:
        return bytes([n])
    body = n.to_bytes((n.bit_length() + 7) // 8, "big")
    return bytes([0x80 | len(body)]) + body


def _decode_length(data: bytes, offset: int) -> tuple[int, int]:
    """Decode an ASN.1 BER length; return (length, new_offset)."""
    first = data[offset]
    offset += 1
    if first < 0x80:
        return first, offset
    n_bytes = first & 0x7F
    length = int.from_bytes(data[offset : offset + n_bytes], "big")
    return length, offset + n_bytes


def _read_full_ldap_message(sock: socket.socket) -> bytes | None:
    """Read one LDAPMessage (ASN.1 SEQUENCE 0x30 + length + body) from ``sock``; None on EOF."""
    header = b""
    while len(header) < 2:
        chunk = sock.recv(2 - len(header))
        if not chunk:
            return None
        header += chunk
    if header[0] != 0x30:
        logger.debug("mock-ldap: unexpected leading byte %#x", header[0])
        return None
    first_len = header[1]
    if first_len & 0x80:  # long-form length
        n_bytes = first_len & 0x7F
        more = b""
        while len(more) < n_bytes:
            chunk = sock.recv(n_bytes - len(more))
            if not chunk:
                return None
            more += chunk
        header += more
        body_len = int.from_bytes(more, "big")
    else:
        body_len = first_len
    body = b""
    while len(body) < body_len:
        chunk = sock.recv(body_len - len(body))
        if not chunk:
            return None
        body += chunk
    return header + body


def _extract_message_id(pdu: bytes) -> int:
    """Pull the messageID INTEGER out of an LDAPMessage SEQUENCE."""
    _length, offset = _decode_length(pdu, 1)
    assert pdu[offset] == 0x02, f"expected INTEGER tag at offset {offset}, got {pdu[offset]:#x}"
    int_len, int_off = _decode_length(pdu, offset + 1)
    return int.from_bytes(pdu[int_off : int_off + int_len], "big", signed=False)


def _build_bind_response(message_id: int) -> bytes:
    """Build an LDAP BindResponse (APPLICATION 1) with resultCode = success."""
    msg_id = _encode_integer(message_id)
    bind_response_body = (
        bytes([0x0A, 0x01, 0x00])  # ENUMERATED success
        + bytes([0x04, 0x00])  # OCTET STRING ""
        + bytes([0x04, 0x00])  # OCTET STRING ""
    )
    bind_response = bytes([0x61]) + _encode_length(len(bind_response_body)) + bind_response_body
    body = msg_id + bind_response
    return bytes([0x30]) + _encode_length(len(body)) + body


def _build_search_done(message_id: int) -> bytes:
    """Build a SearchResultDone (APPLICATION 5) with resultCode = success."""
    msg_id = _encode_integer(message_id)
    result_body = (
        bytes([0x0A, 0x01, 0x00])  # ENUMERATED success
        + bytes([0x04, 0x00])  # OCTET STRING ""
        + bytes([0x04, 0x00])  # OCTET STRING ""
    )
    search_done = bytes([0x65]) + _encode_length(len(result_body)) + result_body
    body = msg_id + search_done
    return bytes([0x30]) + _encode_length(len(body)) + body


def _encode_integer(value: int) -> bytes:
    """Encode an INTEGER ASN.1 BER value (positive only — sufficient for messageIDs)."""
    n_bytes = max(1, (value.bit_length() + 7) // 8)
    raw = value.to_bytes(n_bytes, "big")
    if raw[0] & 0x80:  # pad so it doesn't encode as negative
        raw = b"\x00" + raw
    return bytes([0x02]) + _encode_length(len(raw)) + raw


def _encode_octet_string(value: str) -> bytes:
    raw = value.encode("utf-8")
    return bytes([0x04]) + _encode_length(len(raw)) + raw


def _encode_attribute(attr_type: str, values: list[str]) -> bytes:
    """Encode a PartialAttribute: SEQUENCE { type OCTET STRING, vals SET OF OCTET STRING }."""
    vals_body = b"".join(_encode_octet_string(v) for v in values)
    vals_set = bytes([0x31]) + _encode_length(len(vals_body)) + vals_body  # SET OF (0x31)
    body = _encode_octet_string(attr_type) + vals_set
    return bytes([0x30]) + _encode_length(len(body)) + body


def _build_search_entry(message_id: int, dn: str, attributes: list[tuple[str, list[str]]]) -> bytes:
    """Build a SearchResultEntry (APPLICATION 4) for ``dn`` with ``attributes``."""
    attrs_body = b"".join(_encode_attribute(t, v) for t, v in attributes)
    attrs_seq = bytes([0x30]) + _encode_length(len(attrs_body)) + attrs_body  # PartialAttributeList
    entry_body = _encode_octet_string(dn) + attrs_seq
    search_entry = bytes([0x64]) + _encode_length(len(entry_body)) + entry_body  # APPLICATION 4
    body = _encode_integer(message_id) + search_entry
    return bytes([0x30]) + _encode_length(len(body)) + body


def _directory_entries(directory: Directory) -> list[tuple[str, list[tuple[str, list[str]]]]]:
    """Render ``directory``'s users as (dn, attributes) pairs for SearchResultEntry."""
    entries: list[tuple[str, list[tuple[str, list[str]]]]] = []
    for user in directory.users:
        attrs: list[tuple[str, list[str]]] = [
            ("objectClass", ["inetOrgPerson", "organizationalPerson", "person", "top"]),
            ("uid", [user.uid]),
            ("cn", [user.common_name]),
            ("sn", [user.surname]),
        ]
        if user.given_name:
            attrs.append(("givenName", [user.given_name]))
        if user.email:
            attrs.append(("mail", [user.email]))
        entries.append((user.dn, attrs))
    return entries


class _LdapRequestHandler(socketserver.BaseRequestHandler):
    """Handle one LDAP connection: Bind/Search get success replies, Unbind closes, rest ignored."""

    request: socket.socket

    def handle(self) -> None:
        client = self.request
        while True:
            pdu = _read_full_ldap_message(client)
            if pdu is None:
                return
            try:
                message_id = _extract_message_id(pdu)
            except Exception:
                logger.exception("mock-ldap: failed to parse messageID")
                return
            # protocolOp = first byte after the SEQUENCE header and the messageID INTEGER
            _len, after_seq_header = _decode_length(pdu, 1)
            assert pdu[after_seq_header] == 0x02
            int_len, after_int_len = _decode_length(pdu, after_seq_header + 1)
            protocol_op = pdu[after_int_len + int_len]

            if protocol_op == 0x60:  # BindRequest
                client.sendall(_build_bind_response(message_id))
            elif protocol_op == 0x63:  # SearchRequest
                server = cast(_ThreadingTCPServer, self.server)
                if server.serve_entries:
                    for dn, attrs in _directory_entries(server.directory):
                        client.sendall(_build_search_entry(message_id, dn, attrs))
                client.sendall(_build_search_done(message_id))
            elif protocol_op == 0x42:  # UnbindRequest
                return
            else:
                logger.debug(
                    "mock-ldap: silently ignoring protocolOp %#x for messageID %d",
                    protocol_op,
                    message_id,
                )


class _ThreadingTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True
    directory: Directory
    serve_entries: bool = False


class MockLdapServer:
    """In-process stand-in for :class:`LdapContainer`."""

    NETWORK_ALIAS = "comp-ldap-srv"
    INTERNAL_PORT = 389

    def __init__(
        self,
        directory: Directory,
        name: str = "mock-ldap",
        serve_entries: bool = False,
    ) -> None:
        self.directory = directory
        self.name = name
        # When True, SearchRequests return the directory's users (an active LDAP
        # connection's sync imports them); when False the search is empty, keeping
        # a SAML-dormant LDAP connection from provisioning anyone.
        self.serve_entries = serve_entries
        self.host_port: int = _free_port()
        self._server: _ThreadingTCPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> Self:
        logger.info(
            "Starting mock LDAP server %s on 127.0.0.1:%d (directory: %d users)",
            self.name,
            self.host_port,
            len(list(self.directory.users)),
        )
        self._server = _ThreadingTCPServer(("127.0.0.1", self.host_port), _LdapRequestHandler)
        self._server.directory = self.directory
        self._server.serve_entries = self.serve_entries
        self._thread = threading.Thread(target=self._server.serve_forever, name=self.name)
        self._thread.daemon = True
        self._thread.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        logger.info("Stopping mock LDAP server %s", self.name)
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    @property
    def host_url(self) -> str:
        return f"ldap://127.0.0.1:{self.host_port}"

    @property
    def network_url(self) -> str:
        """Informational in-Docker LDAP URL; the mock runs on the host so nothing dials it."""
        return f"ldap://{self.NETWORK_ALIAS}:{self.INTERNAL_PORT}"
