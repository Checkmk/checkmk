#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from base64 import urlsafe_b64encode
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from agent_receiver import constants
from agent_receiver.server import agent_receiver_app
from cryptography.hazmat.primitives.serialization import Encoding
from cryptography.x509 import Certificate
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from omdlib.certs import CertificateAuthority, RootCA

from cmk.utils.certs import RootCA  # TODO: cleanup this layer violation


@pytest.fixture(autouse=True)
def create_dirs() -> None:
    constants.AGENT_OUTPUT_DIR.mkdir()
    constants.REGISTRATION_REQUESTS.mkdir()


@pytest.fixture(name="client")
def fixture_client() -> TestClient:
    return TestClient(agent_receiver_app)


@pytest.fixture(name="root_ca")
def fixture_root_ca(
    mocker: MockerFixture,
    tmp_path: Path,
) -> RootCA:
    ca_path = tmp_path / "ca"
    mocker.patch("agent_receiver.certificates.ROOT_CERT", ca_path)
    return RootCA(ca_path, "test-ca")


@pytest.fixture(name="trusted_cert")
def fixture_trusted_cert(root_ca: RootCA) -> Certificate:
    return root_ca.new_signed_cert("abc213", 100)[0]


@pytest.fixture(name="trusted_cert_b64")
def fixture_trusted_cert_b64(trusted_cert: Certificate) -> str:
    return urlsafe_b64encode(trusted_cert.public_bytes(Encoding.DER)).decode()


@pytest.fixture(name="untrusted_cert")
def fixture_untrusted_cert(tmp_path: Path) -> Certificate:
    return RootCA(tmp_path / "ca-2", "test-ca-2").new_signed_cert("abc123", 100)[0]


@pytest.fixture(name="untrusted_cert_b64")
def fixture_untrusted_cert_b64(untrusted_cert: Certificate) -> str:
    return urlsafe_b64encode(untrusted_cert.public_bytes(Encoding.DER)).decode()


@pytest.fixture(name="uuid")
def fixture_uuid() -> UUID:
    return uuid4()
