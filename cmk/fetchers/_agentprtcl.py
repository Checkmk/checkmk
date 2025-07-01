#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
import hashlib
import hmac
import zlib
from collections.abc import Buffer, Callable, Iterator
from enum import Enum
from typing import assert_never, Final, Self

from cmk.ccc.exceptions import MKFetcherError

from cmk.fetchers.serializertype import Deserializer, Serializer

from cmk.crypto.deprecated import AesCbcCipher

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
    SHA256_MAC = b"04"
    PBKDF2_MAC = b"05"
    TLS = b"16"
    NONE = b"99"

    @classmethod
    def from_bytes(cls, data: Buffer) -> Self:
        return cls(memoryview(data)[:2])


class Version(Enum):
    V1 = 0

    def __bytes__(self) -> bytes:
        return self.value.to_bytes(Version.length(), "big")

    @classmethod
    def from_bytes(cls, data: Buffer) -> Version:
        return cls(int.from_bytes(memoryview(data)[: Version.length()], "big"))

    @staticmethod
    def length() -> int:
        return 2


class CompressionType(Enum):
    UNCOMPRESSED = 0
    ZLIB = 1

    def __bytes__(self) -> bytes:
        return self.value.to_bytes(self._length(), "big")

    @classmethod
    def from_bytes(cls, data: Buffer) -> CompressionType:
        return cls(int.from_bytes(memoryview(data)[: cls._length()], "big"))

    @staticmethod
    def _length() -> int:
        return 1


class AgentCtlMessage(Deserializer):
    def __init__(
        self,
        version: Version,
        payload: Buffer,
    ) -> None:
        self.version: Final = version
        self.payload: Final = payload

    @classmethod
    def from_bytes(cls, data: Buffer) -> AgentCtlMessage:
        version = Version.from_bytes(data)
        message = memoryview(data)[version.length() :]
        if version is Version.V1:
            return cls(version, MessageV1.from_bytes(message).payload)
        # unreachable
        raise NotImplementedError

    def __hash__(self) -> int:
        return hash((hash(self.version), hash(self.payload)))

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, AgentCtlMessage):
            return self.version == __o.version and self.payload == __o.payload
        return False


class HeaderV1(Serializer, Deserializer):
    def __init__(self, compression_type: CompressionType) -> None:
        self.compression_type: Final = compression_type

    def __iter__(self) -> Iterator[Buffer]:
        yield bytes(self.compression_type)

    @classmethod
    def from_bytes(cls, data: Buffer) -> HeaderV1:
        return cls(CompressionType.from_bytes(data))


class MessageV1(Deserializer):
    def __init__(self, header: HeaderV1, payload: Buffer) -> None:
        self.header: Final = header
        self.payload: Final = payload

    @classmethod
    def from_bytes(cls, data: Buffer) -> MessageV1:
        return cls(
            header := HeaderV1.from_bytes(data),
            _decompress(header.compression_type, memoryview(data)[len(header) :]),
        )

    def __hash__(self) -> int:
        return hash((hash(self.header), hash(self.payload)))

    def __eq__(self, __o: object) -> bool:
        if isinstance(__o, MessageV1):
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
        raise MKFetcherError(
            "Refused: A TLS connection is registered on the monitoring server "
            "but the agent is not providing it"
        )

    match encryption_handling:
        case TCPEncryptionHandling.TLS_ENCRYPTED_ONLY:
            raise MKFetcherError(
                "Refused: TLS is enforced on the monitoring server "
                "but the agent is not providing it"
            )
        case TCPEncryptionHandling.ANY_ENCRYPTED:
            if protocol is TransportProtocol.PLAIN:
                raise MKFetcherError(
                    "Refused: Encryption is enforced on the monitoring server "
                    "but agent is only providing plaintext"
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

    if protocol is TransportProtocol.PBKDF2_MAC:
        return _decrypt_aes_256_cbc_pbkdf2_mac(
            cipherblob=memoryview(encrypted_pkg),
            password=password,
        )

    if protocol is TransportProtocol.SHA256_MAC:
        return _decrypt_aes_256_cbc_sha256_mac(
            cipherblob=memoryview(encrypted_pkg),
            password=password,
        )

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


def _check_mac_and_decrypt(
    key: bytes, iv: bytes, ciphertext: Buffer, expected_mac: Buffer
) -> bytes:
    """
    Check the MAC and decrypt.

    The MAC is calculated based on IV+ciphertext. If it matches the expected_mac, AES-256-CBC is
    used to decrypt the ciphertext with the given key and IV.
    Finally, PKCS#7 padding is removed.
    """
    check = hmac.HMAC(key, digestmod=hashlib.sha256)
    check.update(iv)
    check.update(ciphertext)
    if not hmac.compare_digest(check.digest(), expected_mac):
        raise ValueError("Decryption failed: MAC mismatch")

    cipher = AesCbcCipher("decrypt", key, iv)
    decrypted = cipher.update(bytes(ciphertext)) + cipher.finalize()

    return AesCbcCipher.unpad_block(decrypted)


def _unpack_cipher_blob(blob: Buffer) -> tuple[memoryview, memoryview, memoryview]:
    """
    Split the cipher package used by PBKDF2_MAC and SHA256_MAC.

    The package is expected to have the form [ salt : mac : ciphertext ].
    A tuple of the three components is returned.
    """
    SALT_LENGTH = 8
    MAC_LENGTH = 32
    salt = memoryview(blob)[:SALT_LENGTH]
    mac = memoryview(blob)[SALT_LENGTH : SALT_LENGTH + MAC_LENGTH]
    ciphertext = memoryview(blob)[SALT_LENGTH + MAC_LENGTH :]

    return (salt, mac, ciphertext)


def _decrypt_aes_256_cbc_pbkdf2_mac(cipherblob: Buffer, password: str) -> bytes:
    """
    Decrypt version 05, PBKDF2_MAC.

    Decryption scheme:
      [salt:mac:ciphertext], password <- args
      key, IV <- pbkdf2( salt, password, cycles=600000 )
      validate_hmac_sha256( key, iv+ciphertext, mac )
      result <- aes_256_cbc_decrypt( key, IV, ciphertext )

    """
    salt, mac, ciphertext = _unpack_cipher_blob(cipherblob)
    key, iv = _derive_key_and_iv_pbkdf2(
        password.encode("utf-8"),
        salt,
        cycles=600_000,
        key_length=32,
        iv_length=16,
    )

    return _check_mac_and_decrypt(key, iv, ciphertext, mac)


def _decrypt_aes_256_cbc_sha256_mac(
    cipherblob: Buffer,
    password: str,
) -> bytes:
    """
    Decrypt version 04, SHA256_MAC.

    See _decrypt_aes_256_cbc_pbkdf2. The only differenc is that _derive_openssl_key_and_iv
    (aka EVP_BytesToKey) is used for key derivation.
    """
    salt, mac, ciphertext = _unpack_cipher_blob(cipherblob)
    key, iv = _derive_openssl_key_and_iv(
        password.encode("utf-8"),
        hashlib.sha256,
        key_length=32,
        iv_length=16,
        salt=bytes(salt),
    )

    return _check_mac_and_decrypt(key, iv, ciphertext, mac)


def _decrypt_aes_256_cbc_pbkdf2(ciphertext: Buffer, password: str) -> bytes:
    """Decrypt an openssl encrypted bytestring:
    Cipher: AES256-CBC
    Salted: yes
    Key Derivation: PBKDF2, with SHA256 digest, 10000 cycles
    """
    SALT_LENGTH = 8
    KEY_LENGTH = 32
    IV_LENGTH = 16
    PBKDF2_CYCLES = 10_000

    key, iv = _derive_key_and_iv_pbkdf2(
        password.encode("utf-8"),
        memoryview(ciphertext)[:SALT_LENGTH],
        cycles=PBKDF2_CYCLES,
        key_length=KEY_LENGTH,
        iv_length=IV_LENGTH,
    )

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

    key, iv = _derive_openssl_key_and_iv(
        password.encode("utf-8"),
        digest,
        key_length=KEY_LENGTH,
        iv_length=IV_LENGTH,
    )

    cipher = AesCbcCipher("decrypt", key, iv)
    decrypted = cipher.update(bytes(ciphertext)) + cipher.finalize()

    return AesCbcCipher.unpad_block(decrypted)


def _derive_key_and_iv_pbkdf2(
    password: bytes,
    salt: Buffer,
    *,
    cycles: int,
    key_length: int,
    iv_length: int,
) -> tuple[bytes, bytes]:
    key_iv = hashlib.pbkdf2_hmac(
        "sha256",
        password,
        salt,
        cycles,
        key_length + iv_length,
    )
    return (key_iv[:key_length], key_iv[key_length:])


def _derive_openssl_key_and_iv(
    password: bytes,
    digest: Callable[..., hashlib._Hash],
    *,
    key_length: int,
    iv_length: int,
    salt: bytes = b"",
) -> tuple[bytes, bytes]:
    """
    Simple and completely insecure OpenSSL Key derivation function.

    See EVP_BytesToKey.
    """
    d, d_i = bytearray(b""), b""
    while len(d) < key_length + iv_length:
        d_i = digest(d_i + password + salt).digest()
        d += d_i
    return bytes(memoryview(d)[:key_length]), bytes(
        memoryview(d)[key_length : key_length + iv_length]
    )
