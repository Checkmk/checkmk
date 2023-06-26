#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from binascii import unhexlify
from itertools import product as cartesian_product
from zlib import compress

import pytest

from cmk.utils.exceptions import MKFetcherError

from cmk.fetchers._agentctl import (
    AgentCtlMessage,
    CompressionType,
    decrypt_by_agent_protocol,
    HeaderV1,
    MessageV1,
    TCPEncryptionHandling,
    TransportProtocol,
    validate_agent_protocol,
    Version,
)


@pytest.fixture(name="uncompressed_data")
def fixture_uncompressed_data() -> bytes:
    return b"abc"


@pytest.fixture(name="zlib_compressed_data")
def fixture_zlib_compressed_data(uncompressed_data: bytes) -> bytes:
    return compress(uncompressed_data)


class TestVersion:
    def test_members(self) -> None:
        for member in Version:
            assert Version.from_bytes(bytes(member)) is member


class TestAgentCtlMessage:
    def test_from_bytes(self) -> None:
        assert AgentCtlMessage.from_bytes(
            b"%b%b%b"
            % (
                bytes(Version.V1),
                bytes(CompressionType.UNCOMPRESSED),
                b"some data",
            )
        ) == AgentCtlMessage(
            Version.V1,
            b"some data",
        )

    def test_hash(
        self,
        uncompressed_data: bytes,
    ) -> None:
        assert hash(
            AgentCtlMessage(
                Version.V1,
                uncompressed_data,
            )
        ) == hash(
            AgentCtlMessage(
                Version.V1,
                uncompressed_data,
            )
        )
        assert hash(
            AgentCtlMessage(
                Version.V1,
                uncompressed_data,
            )
        ) != hash(
            AgentCtlMessage(
                Version.V1,
                uncompressed_data + b"blablub",
            )
        )

    def test_eq(
        self,
        uncompressed_data: bytes,
    ) -> None:
        assert AgentCtlMessage(
            Version.V1,
            uncompressed_data,
        ) == AgentCtlMessage(
            Version.V1,
            uncompressed_data,
        )
        assert AgentCtlMessage(
            Version.V1,
            uncompressed_data,
        ) != AgentCtlMessage(
            Version.V1,
            uncompressed_data + b"blablub",
        )


class TestHeaderV1:
    def test_from_bytes(self) -> None:
        assert HeaderV1.from_bytes(bytes(CompressionType.ZLIB)) == HeaderV1(CompressionType.ZLIB)

    def test_iter(self) -> None:
        assert list(HeaderV1(CompressionType.ZLIB)) == [bytes(CompressionType.ZLIB)]


class TestMessageV1:
    def test_from_bytes_ok(
        self,
        uncompressed_data: bytes,
        zlib_compressed_data: bytes,
    ) -> None:
        agent_data_with_header = MessageV1.from_bytes(
            b"%b%b"
            % (
                bytes(CompressionType.ZLIB),
                zlib_compressed_data,
            )
        )
        assert agent_data_with_header.header == HeaderV1(CompressionType.ZLIB)
        assert agent_data_with_header.payload == uncompressed_data

    def test_from_bytes_err(
        self,
        uncompressed_data: bytes,
    ) -> None:
        with pytest.raises(
            ValueError,
            match="Decompression with zlib failed",
        ):
            MessageV1.from_bytes(
                b"%b%b"
                % (
                    bytes(CompressionType.ZLIB),
                    uncompressed_data,
                )
            )

    def test_hash(
        self,
        uncompressed_data: bytes,
        zlib_compressed_data: bytes,
    ) -> None:
        assert hash(
            MessageV1(
                HeaderV1(CompressionType.UNCOMPRESSED),
                uncompressed_data,
            )
        ) == hash(
            MessageV1(
                HeaderV1(CompressionType.UNCOMPRESSED),
                uncompressed_data,
            )
        )
        assert hash(
            MessageV1(
                HeaderV1(CompressionType.UNCOMPRESSED),
                uncompressed_data,
            )
        ) != hash(
            MessageV1(
                HeaderV1(CompressionType.UNCOMPRESSED),
                uncompressed_data + b"hallo",
            )
        )
        assert hash(
            MessageV1(
                HeaderV1(CompressionType.UNCOMPRESSED),
                uncompressed_data,
            )
        ) != hash(
            MessageV1(
                HeaderV1(CompressionType.ZLIB),
                zlib_compressed_data,
            )
        )

    def test_eq(
        self,
        uncompressed_data: bytes,
        zlib_compressed_data: bytes,
    ) -> None:
        assert MessageV1(
            HeaderV1(CompressionType.UNCOMPRESSED),
            uncompressed_data,
        ) == MessageV1(
            HeaderV1(CompressionType.UNCOMPRESSED),
            uncompressed_data,
        )
        assert MessageV1(
            HeaderV1(CompressionType.UNCOMPRESSED),
            uncompressed_data,
        ) != MessageV1(
            HeaderV1(CompressionType.UNCOMPRESSED),
            uncompressed_data + b"hallo",
        )
        assert MessageV1(
            HeaderV1(CompressionType.UNCOMPRESSED),
            uncompressed_data,
        ) != MessageV1(
            HeaderV1(CompressionType.ZLIB),
            zlib_compressed_data,
        )


@pytest.mark.parametrize(
    "protocol,encrypted",
    [
        (
            TransportProtocol.PBKDF2,
            # printf "<<<cmk_test>>>" | openssl enc -aes-256-cbc -md sha256 -iter 10000 -k "cmk"
            b"53616c7465645f5f5474944b9c6f675a14a8c05ca120a284c4f04760ad60e8f2",
        ),
        (
            TransportProtocol.SHA256,
            # printf "<<<cmk_test>>>" |  openssl enc -aes-256-cbc -md sha256 -k "cmk" -nosalt
            b"1a6fabbab6d89aeb410d920b04d8f917",
        ),
        (
            TransportProtocol.MD5,
            # printf "<<<cmk_test>>>" | openssl enc -aes-256-cbc -md md5 -k "cmk" -nosalt
            b"0ce5f41d8c9440f8a4291f43110fb025",
        ),
    ],
)
def test_characterization_legacy_encryption(protocol: TransportProtocol, encrypted: bytes) -> None:
    """A characterization test to ensure we can still decrypt the deprecated encrypted agent output"""
    assert decrypt_by_agent_protocol("cmk", protocol, unhexlify(encrypted)) == b"<<<cmk_test>>>"


class TestValidateAgentProtocol:
    def test_validate_protocol_plaintext_with_enforce_raises(self) -> None:
        with pytest.raises(MKFetcherError):
            validate_agent_protocol(
                TransportProtocol.PLAIN, TCPEncryptionHandling.ANY_ENCRYPTED, is_registered=False
            )

    def test_validate_protocol_no_tls_with_registered_host_raises(self) -> None:
        for p in TransportProtocol:
            if p is TransportProtocol.TLS:
                continue
            with pytest.raises(MKFetcherError):
                validate_agent_protocol(p, TCPEncryptionHandling.ANY_AND_PLAIN, is_registered=True)

    def test_validate_protocol_tls_always_ok(self) -> None:
        for encryption_handling, is_registered in cartesian_product(
            TCPEncryptionHandling, (True, False)
        ):
            validate_agent_protocol(
                TransportProtocol.TLS,
                encryption_handling,
                is_registered=is_registered,
            )

    def test_validate_protocol_tls_required(self) -> None:
        for p in TransportProtocol:
            if p is TransportProtocol.TLS:
                continue
            with pytest.raises(MKFetcherError, match="TLS"):
                validate_agent_protocol(
                    p,
                    TCPEncryptionHandling.TLS_ENCRYPTED_ONLY,
                    is_registered=False,
                )


class TestTransportProtocol:
    @pytest.mark.parametrize("bad_payload", [b"abc", b""])
    def test_detect_transport_protocol_error(self, bad_payload) -> None:
        with pytest.raises(ValueError):
            TransportProtocol(bad_payload)
