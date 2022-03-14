#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from zlib import compress

import pytest

from cmk.core_helpers.tcp_agent_ctl import (
    AgentCtlMessage,
    CompressionType,
    HeaderV1,
    MessageV1,
    Version,
)


@pytest.fixture(name="uncompressed_data")
def fixture_uncompressed_data() -> bytes:
    return b"abc"


@pytest.fixture(name="zlib_compressed_data")
def fixture_zlib_compressed_data(uncompressed_data: bytes) -> bytes:
    return compress(uncompressed_data)


class TestVersion:
    def test_members(self):
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
        assert hash(AgentCtlMessage(Version.V1, uncompressed_data,)) == hash(
            AgentCtlMessage(
                Version.V1,
                uncompressed_data,
            )
        )
        assert hash(AgentCtlMessage(Version.V1, uncompressed_data,)) != hash(
            AgentCtlMessage(
                Version.V1,
                uncompressed_data + b"blablub",
            )
        )

    def test_eq(
        self,
        uncompressed_data: bytes,
    ) -> None:
        assert AgentCtlMessage(Version.V1, uncompressed_data,) == AgentCtlMessage(
            Version.V1,
            uncompressed_data,
        )
        assert AgentCtlMessage(Version.V1, uncompressed_data,) != AgentCtlMessage(
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
        assert hash(MessageV1(HeaderV1(CompressionType.UNCOMPRESSED), uncompressed_data,)) == hash(
            MessageV1(
                HeaderV1(CompressionType.UNCOMPRESSED),
                uncompressed_data,
            )
        )
        assert hash(MessageV1(HeaderV1(CompressionType.UNCOMPRESSED), uncompressed_data,)) != hash(
            MessageV1(
                HeaderV1(CompressionType.UNCOMPRESSED),
                uncompressed_data + b"hallo",
            )
        )
        assert hash(MessageV1(HeaderV1(CompressionType.UNCOMPRESSED), uncompressed_data,)) != hash(
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
        assert MessageV1(HeaderV1(CompressionType.UNCOMPRESSED), uncompressed_data,) == MessageV1(
            HeaderV1(CompressionType.UNCOMPRESSED),
            uncompressed_data,
        )
        assert MessageV1(HeaderV1(CompressionType.UNCOMPRESSED), uncompressed_data,) != MessageV1(
            HeaderV1(CompressionType.UNCOMPRESSED),
            uncompressed_data + b"hallo",
        )
        assert MessageV1(HeaderV1(CompressionType.UNCOMPRESSED), uncompressed_data,) != MessageV1(
            HeaderV1(CompressionType.ZLIB),
            zlib_compressed_data,
        )
