#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import UUID4
from pytest_mock import MockerFixture

from cmk.agent_receiver import site_context
from cmk.agent_receiver.apps_and_routers import AGENT_RECEIVER_APP
from cmk.agent_receiver.checkmk_rest_api import ControllerCertSettings
from cmk.agent_receiver.main import main_app

_CA = b"""-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDpDGxoGtI59lZM
xHdURADCMYS/jIpYAJzT0zTHwbP54gGA0ADqJoXIrfZdcZWJWEsHJqC6WnJsxGRN
uTKSvuInGDM58PdQrMu22mvqSug5hOND7TfsgLXH843HvI7Axo1gQOGhUzIKn0A+
1YgDAm1HQ+8F/0DB/L2UsHXJVJDfvx6GDTCDY2sxTYU8u6qV37V8i6p7hYEcXIXH
PxZg36xp8/1z/PGabt6v6CEZeofImS/9eT2BdCQU5gAH1/rn1n9vUkWIdzB2JzVS
wHK8K7UmDE7TO9oPU8dBZDW3MU+Hz5oIQU84F/WJKkzU+PUkzWq3ycy00DAcvg9y
/cCPy0HXAgMBAAECggEBAJWq9eAyAXtaGfh5YI2MktQkizWdY6e61P0xMj9rxlMf
84kvjLbUAK1uE7/VV4z6WE0CYMztk3kI88X6v2EBGCq1XwjCGYMFRltrkUzJyLRQ
BMi2C2lnC9ebMh3pmeByY49Ce+VokcXCmrb/2bbdEyNmnJZEZOlwkKxyW2LuXZBj
aoz+XVNSZBMlSc4PO9WfYIMhO+AQcK8TyULlENAWge8EF17fBz3ASAwLvusamgYM
4bNP+x6NDmAZDES2OE5xloEnsJqVn5JXRjUbCmF1mg7Fq8I7URns7LGLAUbQEhGe
a+HyBvj1DxUwVnrkZKjVnj+077IrY6zyGCV60SFO5/kCgYEA/pgi1rlXGkKBEKqE
Jaxeld6pXKorUyoIkZkNcr7BghKhaOb6bUJgJNB4M4Js5Lw1nRegaZhwwduiLW24
YdziPMeSbSNCZKZ//3EOF9FpsqJpYVW7pR3xE35UAc0h11+7vbVYAK1wysFtFBoI
Zc6LBAfCJ6iCPYSulmG2pRIu3AMCgYEA6lXVN/3Vv7zfXZ1AATSv4LEWZ8T0Wz0b
ibkYMtEh5+mfBVkkqZ/Ayb7o+q4gZOOPCKH4S5PDDqUrWFYL+21FFsp6ekHUdPSW
DIBHwMAxlM+InLq5q7rO+GeOYdlsT6G6SGetUruBmKA+b+IyKSh+fPcc94xkZHc3
l27kNGWqHJ0CgYEAp17EqHy3sl++EYLH1Sx4EfaLSIvmZ4nekDkaCjE1bZlp21jd
kS5tnkYef15i0AybAmch4cmBdzA4cb0L1eosIODidjUT1K9QvlFIfogBAJqcxIxk
C6yfa71E5NpCQSCCf7jT3b4nxGNcnjZvBt69rSyciw3QcTjkvaAHPoWxoJkCgYAj
neInfXxEhUeJ6gG1bTWiOChIo2XkjDgoSarE5oZ5wkd6P59T7MUXpN2yZE7mJrQx
wrSDgDTwf+hDp+hwUZ5jpWjSNjk9gYNg6Qp+4Hdov9Zqw/K+iEk29j5s3ugYfmNa
5+8vGPLMqOZ0iPPIz6/R/Jk5guwrXPdlG+SxlhYx/QKBgQCMni83pr9X0vvPYU8/
8ukuMqCbaUKvyy2bb4mca2uSDc2IIzU+i8YrppPnKdKUx733duox+/9duc+/ETJx
SM4RXzuE4ADGG6QLGJGztQ0f8uBbT2IPPuFzV+lc7Ch1L3OZ8dqZCjejxvQuUO8u
76HZZLVSG6APCXhj6xF7E7nRJg==
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDCTCCAfGgAwIBAgIINWhbsT86D/cwDQYJKoZIhvcNAQENBQAwIDEeMBwGA1UE
AwwVU2l0ZSAnaGV1dGUnIGxvY2FsIENBMCAXDTIxMTAyMTA2MTQyMFoYDzMwMjAw
MjIyMDYxNDIwWjAgMR4wHAYDVQQDDBVTaXRlICdoZXV0ZScgbG9jYWwgQ0EwggEi
MA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDpDGxoGtI59lZMxHdURADCMYS/
jIpYAJzT0zTHwbP54gGA0ADqJoXIrfZdcZWJWEsHJqC6WnJsxGRNuTKSvuInGDM5
8PdQrMu22mvqSug5hOND7TfsgLXH843HvI7Axo1gQOGhUzIKn0A+1YgDAm1HQ+8F
/0DB/L2UsHXJVJDfvx6GDTCDY2sxTYU8u6qV37V8i6p7hYEcXIXHPxZg36xp8/1z
/PGabt6v6CEZeofImS/9eT2BdCQU5gAH1/rn1n9vUkWIdzB2JzVSwHK8K7UmDE7T
O9oPU8dBZDW3MU+Hz5oIQU84F/WJKkzU+PUkzWq3ycy00DAcvg9y/cCPy0HXAgMB
AAGjRTBDMB0GA1UdDgQWBBSReq9eLFn06+uHtXa8dEOOaN4hcDASBgNVHRMBAf8E
CDAGAQH/AgEAMA4GA1UdDwEB/wQEAwIBBjANBgkqhkiG9w0BAQ0FAAOCAQEAA4KD
TUCf3UsLWCKzy9iUy0xLAT5XQUnPAXtwKiG1jshX25dpzTiYSLAuO72JdcPnb07Q
MDjqYBKCNe70SlO0E6fZs4jW/nos4uO/vGWlU0zZv3wgIkdt50AuEo0+CtlKExmR
VcNr04Hzw5a9MdInNWqMLsvWENWnIhPmHk4Vj7s3uXI0PMd/iAYBZ0P5bA9tWcOL
IDMdZ/39PA0rUjizLrvkkWgdQRDr/ofov79/gvFUcEaKqgf/TTXEMj7r7IbKjtRi
YHMnEteGimP99xWR6e0tf4aRTTMx10dIwKzTXPsYNcqX/yntDcNz16Kz1HncnzTi
EA2I5TbsU6LAEfx6vA==
-----END CERTIFICATE-----
"""

_CA = b"""-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDpDGxoGtI59lZM
xHdURADCMYS/jIpYAJzT0zTHwbP54gGA0ADqJoXIrfZdcZWJWEsHJqC6WnJsxGRN
uTKSvuInGDM58PdQrMu22mvqSug5hOND7TfsgLXH843HvI7Axo1gQOGhUzIKn0A+
1YgDAm1HQ+8F/0DB/L2UsHXJVJDfvx6GDTCDY2sxTYU8u6qV37V8i6p7hYEcXIXH
PxZg36xp8/1z/PGabt6v6CEZeofImS/9eT2BdCQU5gAH1/rn1n9vUkWIdzB2JzVS
wHK8K7UmDE7TO9oPU8dBZDW3MU+Hz5oIQU84F/WJKkzU+PUkzWq3ycy00DAcvg9y
/cCPy0HXAgMBAAECggEBAJWq9eAyAXtaGfh5YI2MktQkizWdY6e61P0xMj9rxlMf
84kvjLbUAK1uE7/VV4z6WE0CYMztk3kI88X6v2EBGCq1XwjCGYMFRltrkUzJyLRQ
BMi2C2lnC9ebMh3pmeByY49Ce+VokcXCmrb/2bbdEyNmnJZEZOlwkKxyW2LuXZBj
aoz+XVNSZBMlSc4PO9WfYIMhO+AQcK8TyULlENAWge8EF17fBz3ASAwLvusamgYM
4bNP+x6NDmAZDES2OE5xloEnsJqVn5JXRjUbCmF1mg7Fq8I7URns7LGLAUbQEhGe
a+HyBvj1DxUwVnrkZKjVnj+077IrY6zyGCV60SFO5/kCgYEA/pgi1rlXGkKBEKqE
Jaxeld6pXKorUyoIkZkNcr7BghKhaOb6bUJgJNB4M4Js5Lw1nRegaZhwwduiLW24
YdziPMeSbSNCZKZ//3EOF9FpsqJpYVW7pR3xE35UAc0h11+7vbVYAK1wysFtFBoI
Zc6LBAfCJ6iCPYSulmG2pRIu3AMCgYEA6lXVN/3Vv7zfXZ1AATSv4LEWZ8T0Wz0b
ibkYMtEh5+mfBVkkqZ/Ayb7o+q4gZOOPCKH4S5PDDqUrWFYL+21FFsp6ekHUdPSW
DIBHwMAxlM+InLq5q7rO+GeOYdlsT6G6SGetUruBmKA+b+IyKSh+fPcc94xkZHc3
l27kNGWqHJ0CgYEAp17EqHy3sl++EYLH1Sx4EfaLSIvmZ4nekDkaCjE1bZlp21jd
kS5tnkYef15i0AybAmch4cmBdzA4cb0L1eosIODidjUT1K9QvlFIfogBAJqcxIxk
C6yfa71E5NpCQSCCf7jT3b4nxGNcnjZvBt69rSyciw3QcTjkvaAHPoWxoJkCgYAj
neInfXxEhUeJ6gG1bTWiOChIo2XkjDgoSarE5oZ5wkd6P59T7MUXpN2yZE7mJrQx
wrSDgDTwf+hDp+hwUZ5jpWjSNjk9gYNg6Qp+4Hdov9Zqw/K+iEk29j5s3ugYfmNa
5+8vGPLMqOZ0iPPIz6/R/Jk5guwrXPdlG+SxlhYx/QKBgQCMni83pr9X0vvPYU8/
8ukuMqCbaUKvyy2bb4mca2uSDc2IIzU+i8YrppPnKdKUx733duox+/9duc+/ETJx
SM4RXzuE4ADGG6QLGJGztQ0f8uBbT2IPPuFzV+lc7Ch1L3OZ8dqZCjejxvQuUO8u
76HZZLVSG6APCXhj6xF7E7nRJg==
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIDCTCCAfGgAwIBAgIINWhbsT86D/cwDQYJKoZIhvcNAQENBQAwIDEeMBwGA1UE
AwwVU2l0ZSAnaGV1dGUnIGxvY2FsIENBMCAXDTIxMTAyMTA2MTQyMFoYDzMwMjAw
MjIyMDYxNDIwWjAgMR4wHAYDVQQDDBVTaXRlICdoZXV0ZScgbG9jYWwgQ0EwggEi
MA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDpDGxoGtI59lZMxHdURADCMYS/
jIpYAJzT0zTHwbP54gGA0ADqJoXIrfZdcZWJWEsHJqC6WnJsxGRNuTKSvuInGDM5
8PdQrMu22mvqSug5hOND7TfsgLXH843HvI7Axo1gQOGhUzIKn0A+1YgDAm1HQ+8F
/0DB/L2UsHXJVJDfvx6GDTCDY2sxTYU8u6qV37V8i6p7hYEcXIXHPxZg36xp8/1z
/PGabt6v6CEZeofImS/9eT2BdCQU5gAH1/rn1n9vUkWIdzB2JzVSwHK8K7UmDE7T
O9oPU8dBZDW3MU+Hz5oIQU84F/WJKkzU+PUkzWq3ycy00DAcvg9y/cCPy0HXAgMB
AAGjRTBDMB0GA1UdDgQWBBSReq9eLFn06+uHtXa8dEOOaN4hcDASBgNVHRMBAf8E
CDAGAQH/AgEAMA4GA1UdDwEB/wQEAwIBBjANBgkqhkiG9w0BAQ0FAAOCAQEAA4KD
TUCf3UsLWCKzy9iUy0xLAT5XQUnPAXtwKiG1jshX25dpzTiYSLAuO72JdcPnb07Q
MDjqYBKCNe70SlO0E6fZs4jW/nos4uO/vGWlU0zZv3wgIkdt50AuEo0+CtlKExmR
VcNr04Hzw5a9MdInNWqMLsvWENWnIhPmHk4Vj7s3uXI0PMd/iAYBZ0P5bA9tWcOL
IDMdZ/39PA0rUjizLrvkkWgdQRDr/ofov79/gvFUcEaKqgf/TTXEMj7r7IbKjtRi
YHMnEteGimP99xWR6e0tf4aRTTMx10dIwKzTXPsYNcqX/yntDcNz16Kz1HncnzTi
EA2I5TbsU6LAEfx6vA==
-----END CERTIFICATE-----
"""


@pytest.fixture(autouse=True)
def fixture_umask() -> Iterator[None]:
    """Ensure the unit tests always use the same umask"""
    old_mask = os.umask(0o0007)
    try:
        yield
    finally:
        os.umask(old_mask)


def site_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    site_id = "NO_SITE"
    site_dir = tmp_path / site_id
    site_dir.mkdir()
    monkeypatch.setenv("OMD_ROOT", str(site_dir))
    monkeypatch.setenv("OMD_SITE", site_id)


@pytest.fixture(autouse=True)
def setup_site_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    site_env(monkeypatch, tmp_path)
    site_context.agent_output_dir().mkdir(parents=True)
    site_context.r4r_dir().mkdir(parents=True)
    site_context.log_path().parent.mkdir(parents=True)
    for ca_path in (
        site_context.site_ca_path(),
        site_context.agent_ca_path(),
    ):
        ca_path.parent.mkdir(parents=True, exist_ok=True)
        ca_path.write_bytes(_CA)


@pytest.fixture(autouse=True)
def mock_controller_certificate_settings(mocker: MockerFixture) -> None:
    mocker.patch("cmk.agent_receiver.endpoints.internal_credentials")
    mocker.patch(
        "cmk.agent_receiver.endpoints.controller_certificate_settings",
        return_value=ControllerCertSettings(lifetime_in_months=12),
    )


@pytest.fixture(name="client")
def fixture_client() -> TestClient:
    main_app()
    return TestClient(AGENT_RECEIVER_APP)


@pytest.fixture(name="uuid")
def fixture_uuid() -> UUID4:
    return UUID(str(uuid4()))
