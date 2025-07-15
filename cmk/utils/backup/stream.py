#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, IO

from cmk.ccc.exceptions import MKException, MKGeneralException
from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.crypto.deprecated import (
    AesCbcCipher,
    certificate_md5_digest,
    decrypt_with_rsa_key,
    encrypt_for_rsa_key,
)
from cmk.crypto.keys import EncryptedPrivateKeyPEM, PrivateKey, PublicKey
from cmk.crypto.password import Password


# Using RSA directly to encrypt the whole backup is a bad idea. So we use the RSA
# public key to generate and encrypt a shared secret which is then used to encrypt
# the backup with AES.
#
# When encryption is active, this function uses the configured RSA public key to
# a) create a random secret key which is encrypted with the RSA public key
# b) the encrypted key is used written to the backup file
# c) the unencrypted random key is used as AES key for encrypting the backup stream
class MKBackupStream:
    def __init__(
        self, stream: IO[bytes], is_alive: Callable[[], bool], key_ident: str | None, debug: bool
    ) -> None:
        self._stream = stream
        self._is_alive = is_alive
        self._cipher: AesCbcCipher | None = None
        self._key_ident = key_ident
        self.debug = debug

        # The iv is an initialization vector for the CBC mode of operation. It
        # needs to be unique per key per message. Normally, it's sent alongside
        # the data in cleartext. Here, since the key is only ever used once,
        # you can use a known IV.
        self._iv = b"\x00" * AesCbcCipher.BLOCK_SIZE

    def process(self) -> Iterator[bytes]:
        if (head := self._init_processing()) is not None:
            yield head

        finished = False
        while not finished or self._is_alive():
            chunk, finished = (
                self._get_plaintext_chunk()
                if self._key_ident is None
                else self._get_encrypted_chunk()
            )
            yield chunk

        assert not self._cipher or self._cipher.finalize() == b"", (
            "Cipher didn't finish processing all input"
        )

    def _init_processing(self) -> bytes | None:
        raise NotImplementedError()

    def _read_from_stream(self, size: int) -> bytes:
        try:
            return self._stream.read(size)
        except ValueError:
            if self._stream.closed:
                return b""  # handle EOF transparently
            raise

    def _get_plaintext_chunk(self) -> tuple[bytes, bool]:
        chunk = self._read_from_stream(1024 * 1024)
        return chunk, chunk == b""

    def _get_encrypted_chunk(self) -> tuple[bytes, bool]:
        raise NotImplementedError()

    def _get_key_spec(self, key_id: bytes) -> dict[str, bytes]:
        keys = self._load_backup_keys()

        for key in keys.values():
            digest = certificate_md5_digest(
                Certificate.load_pem(CertificatePEM(key["certificate"]))
            )
            if key_id == digest.encode("utf-8"):
                return key

        raise MKGeneralException("Failed to load the configured backup key: %s" % key_id.decode())

    # TODO: The return type is a bit questionable...
    def _load_backup_keys(self) -> dict[str, dict[str, bytes]]:
        path = Path(os.environ["OMD_ROOT"], "etc/check_mk/backup_keys.mk")

        variables: dict[str, dict[str, Any]] = {"keys": {}}
        if path.exists():
            exec(path.read_text(), variables, variables)  # nosec B102 # BNS:aee528
        # TODO: Verify value of keys.
        return variables["keys"]


class BackupStream(MKBackupStream):
    def _init_processing(self) -> bytes | None:
        if self._key_ident is None:
            return None

        secret_key, encrypted_secret_key = self._derive_key(
            self._get_encryption_public_key(self._key_ident.encode("utf-8")), 32
        )
        self._cipher = AesCbcCipher("encrypt", secret_key, self._iv)

        # Write out a file version marker and  the encrypted secret key, preceded by
        # a length indication. All separated by \0.
        # Version 1: Encrypted secret key written with pubkey.encrypt(). Worked with
        #            early versions of 1.4 until moving from PyCrypto to PyCryptodome
        # Version 2: Use PKCS1_OAEP for encrypting the encrypted_secret_key.
        return b"%d\0%d\0%s\0" % (2, len(encrypted_secret_key), encrypted_secret_key)

    def _get_encrypted_chunk(self) -> tuple[bytes, bool]:
        assert self._cipher is not None

        chunk = self._read_from_stream(1024 * AesCbcCipher.BLOCK_SIZE)
        was_last_chunk = chunk == b"" or len(chunk) % AesCbcCipher.BLOCK_SIZE != 0

        if was_last_chunk:
            chunk = self._cipher.pad_block(chunk)

        return self._cipher.update(chunk), was_last_chunk

    def _get_encryption_public_key(self, key_id: bytes) -> PublicKey:
        key = self._get_key_spec(key_id)
        return Certificate.load_pem(CertificatePEM(key["certificate"])).public_key

    # logic from http://stackoverflow.com/questions/6309958/encrypting-a-file-with-rsa-in-python
    def _derive_key(self, pubkey: PublicKey, key_length: int) -> tuple[bytes, bytes]:
        secret_key = os.urandom(key_length)
        return secret_key, encrypt_for_rsa_key(pubkey, secret_key)


class RestoreStream(MKBackupStream):
    def __init__(
        self, stream: IO[bytes], is_alive: Callable[[], bool], key_ident: str | None, debug: bool
    ) -> None:
        super().__init__(stream, is_alive, key_ident, debug)

        # If encryption is used, stream cannot return the chunks it reads directly. Because the
        # final chunk contains padding, it first needs to see if it will read another chunk and
        # remove the padding if not.
        self._previous_chunk: bytes | None = None

    def _init_processing(self) -> bytes | None:
        if self._key_ident is None:
            return None

        file_version, encrypted_secret_key = self._read_encrypted_secret_key()
        secret_key = self._decrypt_secret_key(
            file_version, encrypted_secret_key, self._key_ident.encode("utf-8")
        )
        self._cipher = AesCbcCipher("decrypt", secret_key, self._iv)
        return None

    def _get_encrypted_chunk(self) -> tuple[bytes, bool]:
        assert self._cipher is not None

        this_chunk = self._cipher.update(self._read_from_stream(1024 * AesCbcCipher.BLOCK_SIZE))

        if self._previous_chunk is None:
            # First chunk. Only store for next loop.
            self._previous_chunk = this_chunk
            return b"", False

        if len(this_chunk) == 0:
            # The previous was the last chunk. Stip off PKCS#7 padding and return it.
            return self._cipher.unpad_block(self._previous_chunk), True

        # Processing regular chunk. Store it and return previous.
        chunk = self._previous_chunk
        self._previous_chunk = this_chunk
        return chunk, False

    def _read_encrypted_secret_key(self) -> tuple[bytes, bytes]:
        def read_field() -> bytes:
            buf = b""
            while True:
                c = self._stream.read(1)
                if c == b"\0":
                    break
                buf += c
            return buf

        file_version = read_field()
        if file_version not in [b"1", b"2"]:
            raise MKGeneralException(
                "Failed to process backup file (invalid version %r)" % file_version
            )

        try:
            key_len = int(read_field())
        except ValueError:
            raise MKGeneralException("Failed to parse the encrypted backup file (key length)")

        encrypted_secret_key = self._stream.read(int(key_len))

        if self._stream.read(1) != b"\0":
            raise MKGeneralException("Failed to parse the encrypted backup file (header broken)")

        return file_version, encrypted_secret_key

    def _get_encryption_private_key(self, key_id: bytes) -> PrivateKey:
        key = self._get_key_spec(key_id)

        try:
            passphrase = os.environ["MKBACKUP_PASSPHRASE"]
        except KeyError:
            raise MKGeneralException(
                "Failed to get passphrase for decryption the backup. "
                "It needs to be given as environment variable "
                '"MKBACKUP_PASSPHRASE".'
            )

        try:
            return PrivateKey.load_pem(
                EncryptedPrivateKeyPEM(key["private_key"]), Password(passphrase)
            )
        except (ValueError, IndexError, TypeError, MKException):
            if self.debug:
                raise
            raise MKGeneralException("Failed to load private key (wrong passphrase?)")

    def _decrypt_secret_key(
        self, file_version: bytes, encrypted_secret_key: bytes, key_id: bytes
    ) -> bytes:
        if file_version == b"1":
            raise MKGeneralException(
                "You can not restore this backup using your current Check_MK "
                "version. You need to use a Check_MK 1.4 version that has "
                "been released before 2017-03-24. The last compatible "
                "release is 1.4.0b4."
            )

        return decrypt_with_rsa_key(self._get_encryption_private_key(key_id), encrypted_secret_key)
