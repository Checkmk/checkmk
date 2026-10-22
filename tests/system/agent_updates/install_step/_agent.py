#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The agent package that carries the installer units, and the keys it is baked with."""

import time
from dataclasses import dataclass
from pathlib import PurePosixPath

from cmk.ccc.user import UserId
from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.crypto.hash import HashAlgorithm
from cmk.crypto.password import Password
from cmk.utils.keypair_store import Key

AGENT_USER = "cmk-agent"
INSTALLATION_DIRECTORY = PurePosixPath("/opt/checkmk/agent")
INSTALLER_SOCKET = PurePosixPath("/run/cmk-agent-installer.sock")
INSTALLER_SOCKET_UNIT = "cmk-agent-ctl-installer.socket"

_PASSPHRASE = Password("cmk-40788-passphrase")


@dataclass(frozen=True)
class SigningKey:
    """A key pair whose private half the test holds, so that it can sign any package."""

    key: Key

    @property
    def certificate(self) -> str:
        return self.key.certificate

    def sign(self, data: bytes) -> bytes:
        # SHA-256, because that is what verification.rs of the controller checks.
        return self.key.to_certificate_with_private_key(_PASSPHRASE).private_key.rsa_sign_data(
            data, HashAlgorithm.Sha256
        )


def generate_signing_key(alias: str) -> SigningKey:
    key_pair = CertificateWithPrivateKey.generate_self_signed(
        common_name=alias,
        organization="Checkmk system tests",
        key_size=2048,
    )
    return SigningKey(
        Key(
            certificate=key_pair.certificate.dump_pem().str,
            private_key=key_pair.private_key.dump_pem(password=_PASSPHRASE).str,
            alias=alias,
            owner=UserId("cmkadmin"),
            date=time.time(),
        )
    )


@dataclass(frozen=True)
class IntegratedUpdaterAgent:
    """The installed agent package, baked for the single directory deployment."""

    install_dir: PurePosixPath
    trusted_key: SigningKey

    @property
    def ctl(self) -> PurePosixPath:
        return self.install_dir / "package" / "bin" / "cmk-agent-ctl"

    @property
    def update_config(self) -> PurePosixPath:
        return self.install_dir / "package" / "config" / "cmk-agent-ctl-update.toml"

    @property
    def controller_dir(self) -> PurePosixPath:
        return self.install_dir / "runtime" / "controller"

    @property
    def download_dir(self) -> PurePosixPath:
        return self.controller_dir / "update"
