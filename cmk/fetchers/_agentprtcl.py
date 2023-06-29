#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
import hashlib
import sys
import zlib
from collections.abc import Callable, Iterator
from enum import Enum
from typing import assert_never, Final, Self

from cmk.utils.crypto.deprecated import AesCbcCipher
from cmk.utils.exceptions import MKFetcherError
from cmk.utils.serializertype import Deserializer, Serializer

if sys.version_info < (3, 12):
    from typing_extensions import Buffer
else:
    from collections.abc import Buffer

OPENSSL_SALTED_MARKER = "Salted__"


class TCPEncryptionHandling(enum.Enum):
    TLS_ENCRYPTED_ONLY = enum.auto()
    ANY_ENCRYPTED = enum.auto()
    ANY_AND_PLAIN = enum.auto()


class TransportProtocol(Enum):
    PLAIN = b"<<"
    MD5 = b"00"
    SHA256 = b"02"
    PBKDF2 = b"03"
    TLS = b"16"
    NONE = b"99"

    @classmethod
    def from_bytes(cls, data: bytes) -> Self:
        return cls(data[:2])


class Version(Enum):
    V1 = 0

    def __bytes__(self) -> bytes:
        return self.value.to_bytes(self._length(), "big")

    @classmethod
    def from_bytes(cls, data: bytes) -> Version:
        return cls(int.from_bytes(data[: cls._length()], "big"))

    @staticmethod
    def _length() -> int:
        return 2


class CompressionType(Enum):
    UNCOMPRESSED = 0
    ZLIB = 1

    def __bytes__(self) -> bytes:
        return self.value.to_bytes(self._length(), "big")

    @classmethod
    def from_bytes(cls, data: bytes) -> CompressionType:
        return cls(int.from_bytes(data[: cls._length()], "big"))

    @staticmethod
    def _length() -> int:
        return 1


class AgentCtlMessage(Deserializer):
    def __init__(
        self,
        version: Version,
        payload: bytes,
    ) -> None:
        self.version: Final = version
        self.payload: Final = payload

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
    ) -> AgentCtlMessage:
        version = Version.from_bytes(data)
        remaining_data = data[len(bytes(version)) :]
        if version is Version.V1:
            return cls(
                version,
                MessageV1.from_bytes(remaining_data).payload,
            )
        # unreachable
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash(
            (
                hash(self.version),
                hash(self.payload),
            )
        )

    def __eq__(self, __o: object) -> bool:
        if isinstance(
            __o,
            AgentCtlMessage,
        ):
            return self.version == __o.version and self.payload == __o.payload
        return False


class HeaderV1(Serializer, Deserializer):
    def __init__(
        self,
        compression_type: CompressionType,
    ) -> None:
        self.compression_type: Final = compression_type

    def __iter__(self) -> Iterator[bytes]:
        yield bytes(self.compression_type)

    @classmethod
    def from_bytes(
        cls,
        data: bytes,
    ) -> HeaderV1:
        return cls(CompressionType.from_bytes(data))


class MessageV1(Deserializer):
    def __init__(
        self,
        header: HeaderV1,
        payload: bytes,
    ) -> None:
        self.header: Final = header
        self.payload: Final = payload

    @classmethod
    def from_bytes(cls, data: bytes) -> MessageV1:
        return cls(
            header := HeaderV1.from_bytes(data),
            # TODO: remove `bytes()` conversion
            bytes(_decompress(header.compression_type, data[len(header) :])),
        )

    def __hash__(self) -> int:
        return hash(
            (
                hash(self.header),
                hash(self.payload),
            )
        )

    def __eq__(self, __o: object) -> bool:
        if isinstance(
            __o,
            MessageV1,
        ):
            return self.header == __o.header and self.payload == __o.payload
        return False


def _decompress(compression_type: CompressionType, data: Buffer) -> Buffer:
    if compression_type is CompressionType.ZLIB:
        try:
            return zlib.decompress(data)
        except zlib.error as e:
            raise ValueError(f"Decompression with zlib failed: {e!r}") from e
    return data


def validate_agent_protocol(
    protocol: TransportProtocol, encryption_handling: TCPEncryptionHandling, is_registered: bool
) -> None:
    if protocol is TransportProtocol.TLS:
        return

    if is_registered:
        raise MKFetcherError("Refused: Host is registered for TLS but not using it")

    match encryption_handling:
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


def decrypt_by_agent_protocol(
    password: str,
    protocol: TransportProtocol,
    encrypted_pkg: Buffer,
) -> bytes:
    """select the decryption algorithm based on the agent header

    Support encrypted agent data with "99" header.
    This was not intended, but the Windows agent accidentally sent this header
    instead of "00" up to 2.0.0p1, so we keep this for a while.

    Warning:
        "99" for real-time check data means "unencrypted"!
    """

    if protocol is TransportProtocol.PBKDF2:
        return _decrypt_aes_256_cbc_pbkdf2(
            ciphertext=memoryview(encrypted_pkg)[len(OPENSSL_SALTED_MARKER) :],
            password=password,
        )

    if protocol is TransportProtocol.SHA256:
        return _decrypt_aes_256_cbc_legacy(
            ciphertext=encrypted_pkg,
            password=password,
            digest=hashlib.sha256,
        )

    return _decrypt_aes_256_cbc_legacy(
        ciphertext=encrypted_pkg,
        password=password,
        digest=hashlib.md5,
    )


def _decrypt_aes_256_cbc_pbkdf2(ciphertext: Buffer, password: str) -> bytes:
    """Decrypt an openssl encrypted bytestring:
    Cipher: AES256-CBC
    Salted: yes
    Key Derivation: PKBDF2, with SHA256 digest, 10000 cycles
    """
    SALT_LENGTH = 8
    KEY_LENGTH = 32
    IV_LENGTH = 16
    PBKDF2_CYCLES = 10_000

    key_iv = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        memoryview(ciphertext)[:SALT_LENGTH],
        PBKDF2_CYCLES,
        KEY_LENGTH + IV_LENGTH,
    )
    key, iv = key_iv[:KEY_LENGTH], key_iv[KEY_LENGTH:]

    cipher = AesCbcCipher("decrypt", key, iv)
    decrypted = cipher.update(bytes(memoryview(ciphertext)[SALT_LENGTH:])) + cipher.finalize()

    return AesCbcCipher.unpad_block(decrypted)


def _decrypt_aes_256_cbc_legacy(
    ciphertext: Buffer,
    password: str,
    digest: Callable[..., hashlib._Hash],
) -> bytes:
    """Decrypt an openssl encrypted bytesting:
    Cipher: AES256-CBC
    Salted: no
    Key derivation: Simple OpenSSL Key derivation
    """
    KEY_LENGTH = 32
    IV_LENGTH = 16

    key, iv = _derive_openssl_key_and_iv(password.encode("utf-8"), digest, KEY_LENGTH, IV_LENGTH)

    cipher = AesCbcCipher("decrypt", key, iv)
    decrypted = cipher.update(bytes(ciphertext)) + cipher.finalize()

    return AesCbcCipher.unpad_block(decrypted)


def _derive_openssl_key_and_iv(
    password: bytes,
    digest: Callable[..., hashlib._Hash],
    key_length: int,
    iv_length: int,
) -> tuple[bytes, bytes]:
    """Simple and completely insecure OpenSSL Key derivation function"""
    d, d_i = bytearray(b""), b""
    while len(d) < key_length + iv_length:
        d_i = digest(d_i + password).digest()
        d += d_i
    return bytes(memoryview(d)[:key_length]), bytes(
        memoryview(d)[key_length : key_length + iv_length]
    )
