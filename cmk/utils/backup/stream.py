#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, IO

from Cryptodome.Cipher import AES, PKCS1_OAEP
from Cryptodome.Cipher._mode_cbc import CbcMode
from Cryptodome.PublicKey import RSA
from OpenSSL import crypto

from cmk.utils.exceptions import MKGeneralException


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
        self,
        stream: IO[bytes],
        is_alive: Callable[[], bool],
        key_ident: str | None,
        debug: bool,
    ) -> None:
        self._stream = stream
        self._is_alive = is_alive
        self._cipher: CbcMode | None = None
        self._key_ident = key_ident
        self._next_chunk: bytes | None = None
        self.debug = debug

        # The iv is an initialization vector for the CBC mode of operation. It
        # needs to be unique per key per message. Normally, it's sent alongside
        # the data in cleartext. Here, since the key is only ever used once,
        # you can use a known IV.
        self._iv = b"\x00" * AES.block_size

    def process(self) -> Iterator[bytes]:
        head = self._init_processing()
        if head is not None:
            yield head

        while True:
            chunk, finished = self._read_chunk()
            yield self._process_chunk(chunk)
            if finished and not self._is_alive():
                break  # end of stream reached

    def _init_processing(self) -> bytes | None:
        raise NotImplementedError()

    def _read_from_stream(self, size: int) -> bytes:
        try:
            return self._stream.read(size)
        except ValueError:
            if self._stream.closed:
                return b""  # handle EOF transparently
            raise

    def _read_chunk(self) -> tuple[bytes, bool]:
        raise NotImplementedError()

    def _process_chunk(self, chunk: bytes) -> bytes:
        raise NotImplementedError()

    def _get_key_spec(self, key_id: bytes) -> dict[str, bytes]:
        keys = self._load_backup_keys()

        for key in keys.values():
            digest: bytes = load_certificate_pem(key["certificate"]).digest("md5")
            if key_id == digest:
                return key

        raise MKGeneralException("Failed to load the configured backup key: %s" % key_id.decode())

    # TODO: The return type is a bit questionable...
    def _load_backup_keys(self) -> dict[str, dict[str, bytes]]:
        path = Path(os.environ["OMD_ROOT"], "etc/check_mk/backup_keys.mk")

        variables: dict[str, dict[str, Any]] = {"keys": {}}
        if path.exists():
            exec(path.read_text(), variables, variables)
        # TODO: Verify value of keys.
        return variables["keys"]


class BackupStream(MKBackupStream):
    def _init_processing(self) -> bytes | None:
        if self._key_ident is None:
            return None

        secret_key, encrypted_secret_key = self._derive_key(
            self._get_encryption_public_key(self._key_ident.encode("utf-8")), 32
        )
        cipher = AES.new(secret_key, AES.MODE_CBC, self._iv)
        assert isinstance(cipher, CbcMode)
        self._cipher = cipher

        # Write out a file version marker and  the encrypted secret key, preceded by
        # a length indication. All separated by \0.
        # Version 1: Encrypted secret key written with pubkey.encrypt(). Worked with
        #            early versions of 1.4 until moving from PyCrypto to PyCryptodome
        # Version 2: Use PKCS1_OAEP for encrypting the encrypted_secret_key.
        return b"%d\0%d\0%s\0" % (2, len(encrypted_secret_key), encrypted_secret_key)

    def _read_chunk(self) -> tuple[bytes, bool]:
        finished = False
        if self._key_ident is not None:
            chunk = self._read_from_stream(1024 * AES.block_size)

            # Detect end of file and add padding to fill up to block size
            if chunk == b"" or len(chunk) % AES.block_size != 0:
                padding_length = (AES.block_size - len(chunk) % AES.block_size) or AES.block_size
                chunk += padding_length * bytes((padding_length,))
                finished = True
        else:
            chunk = self._read_from_stream(1024 * 1024)
            if chunk == b"":
                finished = True

        return chunk, finished

    def _process_chunk(self, chunk: bytes) -> bytes:
        if self._key_ident is not None:
            assert self._cipher is not None
            return self._cipher.encrypt(chunk)
        return chunk

    def _get_encryption_public_key(self, key_id: bytes) -> RSA.RsaKey:
        key = self._get_key_spec(key_id)

        # First extract the public key part from the certificate
        cert = load_certificate_pem(key["certificate"])
        pub: crypto.PKey = cert.get_pubkey()
        pub_pem = dump_publickey_pem(pub)

        # Now construct the public key object
        return RSA.importKey(pub_pem)

    # logic from http://stackoverflow.com/questions/6309958/encrypting-a-file-with-rsa-in-python
    # Since our packages moved from PyCrypto to PyCryptodome we need to change this to use PKCS1_OAEP.
    def _derive_key(self, pubkey, key_length):
        secret_key = os.urandom(key_length)

        # Encrypt the secret key with the RSA public key
        cipher_rsa = PKCS1_OAEP.new(pubkey)
        encrypted_secret_key = cipher_rsa.encrypt(secret_key)

        return secret_key, encrypted_secret_key


class RestoreStream(MKBackupStream):
    def _init_processing(self) -> bytes | None:
        self._next_chunk = None
        if self._key_ident is None:
            return None

        file_version, encrypted_secret_key = self._read_encrypted_secret_key()
        secret_key = self._decrypt_secret_key(
            file_version, encrypted_secret_key, self._key_ident.encode("utf-8")
        )
        cipher = AES.new(secret_key, AES.MODE_CBC, self._iv)
        assert isinstance(cipher, CbcMode)
        self._cipher = cipher
        return None

    def _read_chunk(self) -> tuple[bytes, bool]:
        if self._key_ident is None:
            # process unencrypted backup
            chunk = self._read_from_stream(1024 * 1024)
            return chunk, chunk == b""

        assert self._cipher is not None
        this_chunk = self._cipher.decrypt(self._read_from_stream(1024 * AES.block_size))

        if self._next_chunk is None:
            # First chunk. Only store for next loop
            self._next_chunk = this_chunk
            return b"", False

        if len(this_chunk) == 0:
            # Processing last chunk. Stip off padding.
            pad = self._next_chunk[-1]
            chunk = self._next_chunk[:-pad]
            return chunk, True

        # Processing regular chunk
        chunk = self._next_chunk
        self._next_chunk = this_chunk
        return chunk, False

    def _process_chunk(self, chunk: bytes) -> bytes:
        return chunk

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

    def _get_encryption_private_key(self, key_id: bytes) -> RSA.RsaKey:
        key = self._get_key_spec(key_id)

        try:
            passphrase = os.environ["MKBACKUP_PASSPHRASE"]
        except KeyError:
            raise MKGeneralException(
                "Failed to get passphrase for decryption the backup. "
                "It needs to be given as environment variable "
                '"MKBACKUP_PASSPHRASE".'
            )

        # First decrypt the private key using PyOpenSSL (was unable to archieve
        # this with RSA.importKey(). :-(
        pkey = load_privatekey_pem(key["private_key"], passphrase.encode("utf-8"))
        priv_pem = dump_privatekey_pem(pkey)

        try:
            return RSA.importKey(priv_pem)
        except (ValueError, IndexError, TypeError):
            if self.debug:
                raise
            raise MKGeneralException("Failed to load private key (wrong passphrase?)")

    def _decrypt_secret_key(
        self, file_version: bytes, encrypted_secret_key: bytes, key_id: bytes
    ) -> bytes:
        private_key = self._get_encryption_private_key(key_id)

        if file_version == b"1":
            raise MKGeneralException(
                "You can not restore this backup using your current Check_MK "
                "version. You need to use a Check_MK 1.4 version that has "
                "been released before 2017-03-24. The last compatible "
                "release is 1.4.0b4."
            )
        cipher_rsa = PKCS1_OAEP.new(private_key)
        return cipher_rsa.decrypt(encrypted_secret_key)


# Some typed wrappers around OpenSSL.crypto, there are only Python 2 interface
# files available... :-/


def load_certificate_pem(buf: bytes) -> crypto.X509:
    return crypto.load_certificate(crypto.FILETYPE_PEM, buf)


def dump_publickey_pem(pkey: crypto.PKey) -> bytes:
    return crypto.dump_publickey(crypto.FILETYPE_PEM, pkey)


def load_privatekey_pem(buf: bytes, passphrase: bytes) -> crypto.PKey:
    return crypto.load_privatekey(crypto.FILETYPE_PEM, buf, passphrase)


def dump_privatekey_pem(pkey: crypto.PKey) -> bytes:
    return crypto.dump_privatekey(crypto.FILETYPE_PEM, pkey)
