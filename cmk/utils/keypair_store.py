#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, Any, Self

from pydantic import BaseModel, PlainValidator, WithJsonSchema

from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.crypto.certificate import Certificate, CertificatePEM, CertificateWithPrivateKey
from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.keys import EncryptedPrivateKeyPEM, PrivateKey
from cmk.crypto.password import Password

_AnnotatedUserId = Annotated[
    UserId,
    PlainValidator(UserId.parse),
    WithJsonSchema({"type": "string"}, mode="serialization"),
]


class Key(BaseModel):
    certificate: str
    private_key: str
    alias: str
    owner: _AnnotatedUserId
    date: float
    # Before 2.2 this field was only used for Setup backup keys. Now we add it to all key, because it
    # won't hurt for other types of keys (e.g. the bakery signing keys). We set a default of False
    # to initialize it for all existing keys assuming it was already downloaded. It is still only
    # used in the context of the backup keys.
    not_downloaded: bool = False

    def to_certificate_with_private_key(self, passphrase: Password) -> CertificateWithPrivateKey:
        return CertificateWithPrivateKey(
            certificate=self.to_certificate(),
            private_key=PrivateKey.load_pem(EncryptedPrivateKeyPEM(self.private_key), passphrase),
        )

    def to_certificate(self) -> Certificate:
        """convert the string certificate to Certificate object"""
        return Certificate.load_pem(CertificatePEM(self.certificate))

    def fingerprint(self, algorithm: HashAlgorithm) -> str:
        """return the fingerprint aka hash of the certificate as a hey string"""
        return (
            Certificate.load_pem(CertificatePEM(self.certificate))
            .fingerprint(algorithm)
            .hex(":")
            .upper()
        )


class KeyId(str):
    """KeyId type used for dictionary keys of KeypairStore & agent signature keys.
    Accepts str|int|uuid.UUID on initialization and coerces to str internally.
    Earlier key_id were integers, later changed to UUIDs. To support both types transparently,
    we accept str|int|uuid.UUID here.
    """

    def __new__(cls, value: str | int | uuid.UUID) -> Self:
        return super().__new__(cls, str(value))

    @classmethod
    def generate(cls) -> Self:
        return cls(uuid.uuid4())


class KeyAlreadyExists(Exception):
    def __init__(self, key_id: KeyId, alias: str) -> None:
        super().__init__(f"Key already exists: {key_id}")
        self.key_id = key_id
        self.alias = alias


type KeypairMap = dict[KeyId, Key]


class KeypairStore:
    def __init__(self, path: Path, attr: str) -> None:
        super().__init__()
        self._path = path
        self._attr = attr

    def load(self) -> KeypairMap:
        if not self._path.exists():
            return {}

        variables: dict[str, dict[str | int, dict[str, Any]]] = {self._attr: {}}  # type: ignore[explicit-any]
        with self._path.open("rb") as f:
            exec(f.read(), variables, variables)  # nosec B102 # BNS:aee528
        return self.parse(variables[self._attr])

    def save(self, keys: KeypairMap) -> None:
        self._path.parent.mkdir(mode=0o770, exist_ok=True, parents=True)
        with store.locked(self._path):
            store.save_to_mk_file(
                self._path, key=self._attr, value=self._unparse(keys), pprint_value=True
            )

    @staticmethod
    def parse(raw_keys: Mapping[str | int, dict[str, str | float | bool]]) -> KeypairMap:
        return {KeyId(key_id): Key.model_validate(raw_key) for key_id, raw_key in raw_keys.items()}

    @staticmethod
    def _unparse(keys: KeypairMap) -> dict[str, dict[str, str | float | bool]]:
        return {key_id: key.model_dump() for key_id, key in keys.items()}

    def choices(self) -> list[tuple[str, str]]:
        choices = []
        for key in self.load().values():
            choices.append((key.fingerprint(HashAlgorithm.MD5), key.alias))
        return sorted(choices, key=lambda x: x[1])

    def get_key_by_digest(self, digest: str) -> tuple[KeyId, Key]:
        for key_id, key in self.load().items():
            if key.fingerprint(HashAlgorithm.MD5) == digest:
                return key_id, key
        raise KeyError

    def add(self, key: Key) -> None:
        keys = self.load()

        this_digest = key.fingerprint(HashAlgorithm.MD5)
        for key_id, stored_key in keys.items():
            if stored_key.fingerprint(HashAlgorithm.MD5) == this_digest:
                raise KeyAlreadyExists(key_id, stored_key.alias)

        keys[KeyId.generate()] = key
        self.save(keys)
