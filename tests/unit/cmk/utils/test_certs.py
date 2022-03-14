#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from pytest_mock import MockerFixture

from tests.testlib import on_time
from tests.testlib.certs import (
    check_certificate_against_private_key,
    check_certificate_against_public_key,
    check_cn,
)

from cmk.utils.certs import (
    _make_csr,
    _make_private_key,
    _make_root_certificate,
    _make_subject_name,
    _rsa_public_key_from_cert_or_csr,
    _sign_csr,
    load_cert_and_private_key,
    RootCA,
)

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

_SITE_CERT = b"""-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQCgNgfTJm7T2GpV
SwUuln69aYRlP5AKsFJjAO2jmAN1Cw0BhYbw3YbuI5XJM0z072pk5NrZYBIRFLcm
AjunOEFoZX2qAh1xCirTyDWF6lxihLWRwuORKtC7Fxc1f9Tad/5fxPHfdvW0/pAG
UVTe1z/aD0nsFzmf764Gj5nkF0Eh+ZAjyBQnSszR+k8NloAO66cQeeWDFxLFvS36
wk+ISiA3BIfNu892QO74Wv3eaZFDzedBfQPPMmPFv9PVGKOHh3VHYwgWkXeizeEs
CUna7iCPi/lZB8LTjk98aZ2qSOYLvLo5Fx8ZGwh6cZCf3eZNMRzqrzLNQMGsec7R
sr83TRRlAgMBAAECggEBAIJwOyKw0d7s/nX/JHLv2LSCama8v5vUPt+Ya+Kb64Sp
wKcSffExi5/rnRI5EFkDbE5E/eGplEwP36W0f7j/1lEXAJ8gJbRZINFY2irzys/z
WJkaYYlZoKQSgrTuJPDSbWqvwHW+NwJrl/ts0Hq2Kahydi8gIayTyc5RsGvCeyca
7UiYHuLVSodwKtXN11/FjpeII5D//ev2g4cwA4NHXBQirjJBSp/T90L+Tsc0Y07/
hPd9HXnT/5ob0eZMvoqiVsvpZZipRYT2wmum28tNDY3E6EERW3G27+JxJaVlT9eG
TIZBoerduzFBKy1BzSsIZX4yJsm1gCB0CqJ6co8AhMECgYEA0WyksZHphtuz5ZG/
Vmj7RXdawTBwdpvbFFLTzxD81pJbfYOZO5LERxCvX/qGno71EWZxZMvqqfHzlfLs
rjM3v7Ai7dTTVtq4LI9nvTuk+RR15rdyGf+VayYar2cvVNniR7Fd9RoBCrB7UbTL
VMAYSvUeprognExC6JSOXj9mNw0CgYEAw9d6Zm+0+nrVmvVnRdUMea2COuBmCXxu
hixy1LMCynJlJmZs3MB/qeVvyh5T1l+pyds6MYD0rdUWHjBTENfBuf51lzDUxdCE
mEO7S/7ONjc0eyL2o639vVgAdTE6dG7Nu6fApdMn0XtB4rF5q7vDI4wmRYdf2gqS
wKGfI7GZfLkCgYEAw2B9IaBD4mmTooffnqjgSsV36KXdNfpfX82KBzMM/s2aBzW/
viFFdhst0ffyoXgzT+FnxqarLZMpMeppPndP+khDvegAppX0nrXHDXbYiPu6ptzb
2T9lUYpB+QPl115SSZpCUsjI0gUld2uZCl8QCtY1m0wn4kkPXtZBH9I79P0CgYB8
gkg9TBPhk6quRAsOaK7vxRIg4H2+1i9memffNpg1oZkRWtknV/NSTp5OAA4JIvTN
cuWCh5wH0IupUcvdz25JE7ArGU6NHU7Ph3BSloMAEQT6rHXmBj5l3McdutiRIckG
31Yplx+fnR98Qp06Q7uCpB3I4pJcC5DVi2ujw8vzcQKBgQDRZx+5pZo6ai6xGO+0
oINtF24qVT6or/JenstoVCuF/+pEyXxTpT+VUrh5KN5BFKxNY30i0ce4rhVnuVBw
dA6nsZ1zuYUANTIXiyLdpR30vl5yjuvlfnV6/+xHJst7lEtiHOzcejkDVBINzOYO
bo4aHIMujsht1UJMCrdMGkQafQ==
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIICsjCCAZqgAwIBAgIIdLzPYwFq4l0wDQYJKoZIhvcNAQENBQAwIDEeMBwGA1UE
AwwVU2l0ZSAnaGV1dGUnIGxvY2FsIENBMCAXDTIxMTAyMTA2MTQyMFoYDzMwMjAw
MjIyMDYxNDIwWjAQMQ4wDAYDVQQDDAVoZXV0ZTCCASIwDQYJKoZIhvcNAQEBBQAD
ggEPADCCAQoCggEBAKA2B9MmbtPYalVLBS6Wfr1phGU/kAqwUmMA7aOYA3ULDQGF
hvDdhu4jlckzTPTvamTk2tlgEhEUtyYCO6c4QWhlfaoCHXEKKtPINYXqXGKEtZHC
45Eq0LsXFzV/1Np3/l/E8d929bT+kAZRVN7XP9oPSewXOZ/vrgaPmeQXQSH5kCPI
FCdKzNH6Tw2WgA7rpxB55YMXEsW9LfrCT4hKIDcEh827z3ZA7vha/d5pkUPN50F9
A88yY8W/09UYo4eHdUdjCBaRd6LN4SwJSdruII+L+VkHwtOOT3xpnapI5gu8ujkX
HxkbCHpxkJ/d5k0xHOqvMs1Awax5ztGyvzdNFGUCAwEAATANBgkqhkiG9w0BAQ0F
AAOCAQEAyjLmqWG00P++wLQFSY3Hc6LMYG8VOaqkiU5ZySnXoJqyHL5E1+iTWEpo
hbVLECo8TbL4hzG+DX1UJo923V851GWVyBfA5kBL+y2Q4+WkuTSfedvPvVlNFhWV
NkQjzE2qloFTYxtAcYh3qulUx44zu3yRFZTHpiYLaRPBhU6R2J/f9gNulAyr/2Xa
245T2KLjq3xGk+oFXbZ8xnOXaMks8xx1Uscy4I2Vj5Q2FiSl/SmZ2uLW9bTXfHXU
nV9RB41QIpThjlYmFaNJWVCO4u3tqVfDAbzpiCAF54eUOQ5iTIQPzFN5J6ACZsgn
00XPdmGfV2A6eqWQp3BcUAmqsJLzlQ==
-----END CERTIFICATE-----
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


@pytest.mark.parametrize(
    "cert_bytes, expected_cn",
    [
        pytest.param(
            _CA,
            "Site 'heute' local CA",
            id="ca",
        ),
        pytest.param(
            _SITE_CERT,
            "heute",
            id="site certificate",
        ),
    ],
)
def test_load_cert_and_private_key(
    mocker: MockerFixture,
    cert_bytes: bytes,
    expected_cn: str,
) -> None:
    mocker.patch(
        "cmk.utils.certs.Path.read_bytes",
        return_value=cert_bytes,
    )
    cert, priv_key = load_cert_and_private_key(Path("whatever"))
    assert check_cn(
        cert,
        expected_cn,
    )
    assert isinstance(
        cert.public_key(),
        RSAPublicKey,
    )
    assert isinstance(
        priv_key,
        RSAPrivateKey,
    )
    check_certificate_against_private_key(
        cert,
        priv_key,
    )


def test_make_private_key() -> None:
    assert _make_private_key().key_size == 2048


def test_make_root_certificate() -> None:
    key = _make_private_key()
    with on_time(100, "UTC"):
        cert = _make_root_certificate(
            _make_subject_name("peter"),
            1,
            key,
        )
    assert check_cn(
        cert,
        "peter",
    )
    assert str(cert.not_valid_before) == "1970-01-01 00:01:40"
    assert str(cert.not_valid_after) == "1970-01-02 00:01:40"
    check_certificate_against_private_key(
        cert,
        key,
    )


def test_make_csr() -> None:
    csr = _make_csr(
        _make_subject_name("abc123"),
        _make_private_key(),
    )
    assert csr.is_signature_valid
    assert check_cn(
        csr,
        "abc123",
    )


def test_sign_csr() -> None:
    root_key = _make_private_key()
    root_cert = _make_root_certificate(
        _make_subject_name("peter"),
        1,
        root_key,
    )
    key = _make_private_key()
    csr = _make_csr(
        _make_subject_name("from_peter"),
        key,
    )
    with on_time(100, "UTC"):
        cert = _sign_csr(
            csr,
            2,
            root_cert,
            root_key,
        )

    assert check_cn(
        cert,
        "from_peter",
    )
    assert str(cert.not_valid_before) == "1970-01-01 00:01:40"
    assert str(cert.not_valid_after) == "1970-01-03 00:01:40"
    check_certificate_against_private_key(
        cert,
        key,
    )
    # ensure that 'from_peter' is indeed signed by 'peter'
    check_certificate_against_public_key(
        cert,
        _rsa_public_key_from_cert_or_csr(root_cert),
    )


def test_sign_csr_with_local_ca() -> None:
    root_key = _make_private_key()
    root_cert = _make_root_certificate(
        _make_subject_name("peter"),
        1,
        root_key,
    )
    key = _make_private_key()
    csr = _make_csr(
        _make_subject_name("from_peter"),
        key,
    )

    root_ca = RootCA(root_cert, root_key)
    with on_time(567892121, "UTC"):
        cert = root_ca.sign_csr(csr, 100)

    assert check_cn(
        cert,
        "from_peter",
    )
    assert str(cert.not_valid_before) == "1987-12-30 19:48:41"
    assert str(cert.not_valid_after) == "1988-04-08 19:48:41"
    check_certificate_against_private_key(
        cert,
        key,
    )
    # ensure that 'from_peter' is indeed signed by 'peter'
    check_certificate_against_public_key(
        cert,
        _rsa_public_key_from_cert_or_csr(root_cert),
    )
