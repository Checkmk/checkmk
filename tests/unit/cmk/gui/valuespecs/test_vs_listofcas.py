#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Callable

import pytest

import cmk.gui.valuespec as vs
from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.gui.exceptions import MKUserError


# some relevant data:
#   Signature Algorithm: sha1WithRSAEncryption
#   Issuer: C = CH, O = SwissSign AG, CN = SwissSign Gold CA - G2
#   Subject: C = CH, O = SwissSign AG, CN = SwissSign Gold CA - G2
#   Subject Public Key Info:
#       Public Key Algorithm: rsaEncryption
#           Public-Key: (4096 bit)
#   Signature Algorithm: sha1WithRSAEncryption
def _swiss_sign_cert() -> str:
    # this is a function to avoid spamming the pytest output
    return """
-----BEGIN CERTIFICATE-----
MIIFujCCA6KgAwIBAgIJALtAHEP1Xk+wMA0GCSqGSIb3DQEBBQUAMEUxCzAJBgNV
BAYTAkNIMRUwEwYDVQQKEwxTd2lzc1NpZ24gQUcxHzAdBgNVBAMTFlN3aXNzU2ln
biBHb2xkIENBIC0gRzIwHhcNMDYxMDI1MDgzMDM1WhcNMzYxMDI1MDgzMDM1WjBF
MQswCQYDVQQGEwJDSDEVMBMGA1UEChMMU3dpc3NTaWduIEFHMR8wHQYDVQQDExZT
d2lzc1NpZ24gR29sZCBDQSAtIEcyMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIIC
CgKCAgEAr+TufoskDhJuqVAtFkQ7kpJcyrhdhJJCEyq8ZVeCQD5XJM1QiyUqt2/8
76LQwB8CJEoTlo8jE+YoWACjR8cGp4QjK7u9lit/VcyLwVcfDmJlD909Vopz2q5+
bbqBHH5CjCA12UNNhPqE21Is8w4ndwtrvxEvcnifLtg+5hg3Wipy+dpikJKVyh+c
6bM8K8vzARO/Ws/BtQpgvd21mWRTuKCWs2/iJneRjOBiEAKfNA+k1ZIzUd6+jbqE
emA8atufK+ze3gE/bk3lUIbLtK/tREDFylqM2tIrfKjuvqblCqoOpd8FUrdVxyJd
MmqXl2MT28nbeTZ7hTpKxVKJ+STnnXepgv9VHKVxaSvRAiTysybUa9oEVeXBCsdt
MDeQKuSeFDNeFhdVxVu1yzSJkvGdJo+hB9TGsnhQ2wwMC3wLjEHXuendjIj3o02y
MszYF9rNt85mndT9Xv+9lz4pded+p2JYryU0pUHHPbwNUMoDAw8IWh+Vc3hiv69y
FGkOpeUDDniOJihC8AcLYiAQZzlG+qkDzAQ4embvIIO1jEpWjpEA/I5cgt6IoMPi
aG59je883WX0XaxR7ySArqpWl2/5rX3aYT+YdzylkbYcjCbaZaIJbcHiVOO5ykxM
gI93e2CaHt+28kgeDrpOVG2Y4OGiGqJ3UM/EY5LsRxmd6+ZrzsECAwEAAaOBrDCB
qTAOBgNVHQ8BAf8EBAMCAQYwDwYDVR0TAQH/BAUwAwEB/zAdBgNVHQ4EFgQUWyV7
lqRlUX64OfPAeGZe6Drn8O4wHwYDVR0jBBgwFoAUWyV7lqRlUX64OfPAeGZe6Drn
8O4wRgYDVR0gBD8wPTA7BglghXQBWQECAQEwLjAsBggrBgEFBQcCARYgaHR0cDov
L3JlcG9zaXRvcnkuc3dpc3NzaWduLmNvbS8wDQYJKoZIhvcNAQEFBQADggIBACe6
45R88a7A3hfm5djV9VSwg/S7zV4Fe0+fdWavPOhWfvxyeDgD2StiGwC5+OlgzczO
UYrHUDFu4Up+GC9pWbY9ZIEr44OE5iKHjn3g7gKZYbge9LgriBIWhMIxkziWMaa5
O1M/wySTVltpkuzFwbs4AOPsF6m43Md8AYOfMke6UiI0HTJ6CVanfCU2qT1L2sCC
bwq7EsiHSycR+R4tx5M/nttfJmtS2S6K8RTGRI0Vqbe/vd6mGu6uLftIdxf+u+yv
GPUqUfA5hJeVbG4bwyvEdGB5JbAKJ9/fXtI5z0V9QkvfsywexcZdylU6oJxpmo/a
77KwPJ+HbBIrZXAVUjEaJM9vMSNQH4xPjyPDdEFjHFWoFN0+4FFQz/EbMFYOkrCC
hdiDyyJkvC24JdVUorgG6q2SpCSgwYa1ShNqR88uC1aVVMvOmttqtKay20EIhid3
92qgQmwLOM7XdVAyksLfKzAiSNDVQTglXaTpXZ/GlHXQRf0wl0OPkKsKx4ZzYEpp
Ld6leNcG2mqeSz53OiATIgHQv2ieY2BrNU0LbbqhPcCT4H8js1WtciVORvnSFu+w
ZMEBnunKoGqYDs/YYPIvSbjkQuE4NRb0yG5P94FW6LqjviOvrv1vA+ACOzB2+htt
Qc8Bsem4yWb02ybzOqR08kkkW8mw0FfB+j564ZfJ
-----END CERTIFICATE-----
"""


# some relevant data:
#   Signature Algorithm: ecdsa-with-SHA384
#   Issuer: C = TR, L = Ankara, O = E-Tugra EBG A.S., OU = E-Tugra Trust Center, CN = E-Tugra Global Root CA ECC v3
#   Subject: C = TR, L = Ankara, O = E-Tugra EBG A.S., OU = E-Tugra Trust Center, CN = E-Tugra Global Root CA ECC v3
#   Subject Public Key Info:
#       Public Key Algorithm: id-ecPublicKey
#           Public-Key: (384 bit)
#           ASN1 OID: secp384r1
#           NIST CURVE: P-384
#   Signature Algorithm: ecdsa-with-SHA384
def _etugra_cert() -> str:
    # this is a function to avoid spamming the pytest output
    return """
-----BEGIN CERTIFICATE-----
MIICpTCCAiqgAwIBAgIUJkYZdzHhT28oNt45UYbm1JeIIsEwCgYIKoZIzj0EAwMw
gYAxCzAJBgNVBAYTAlRSMQ8wDQYDVQQHEwZBbmthcmExGTAXBgNVBAoTEEUtVHVn
cmEgRUJHIEEuUy4xHTAbBgNVBAsTFEUtVHVncmEgVHJ1c3QgQ2VudGVyMSYwJAYD
VQQDEx1FLVR1Z3JhIEdsb2JhbCBSb290IENBIEVDQyB2MzAeFw0yMDAzMTgwOTQ2
NThaFw00NTAzMTIwOTQ2NThaMIGAMQswCQYDVQQGEwJUUjEPMA0GA1UEBxMGQW5r
YXJhMRkwFwYDVQQKExBFLVR1Z3JhIEVCRyBBLlMuMR0wGwYDVQQLExRFLVR1Z3Jh
IFRydXN0IENlbnRlcjEmMCQGA1UEAxMdRS1UdWdyYSBHbG9iYWwgUm9vdCBDQSBF
Q0MgdjMwdjAQBgcqhkjOPQIBBgUrgQQAIgNiAASOmCm/xxAeJ9urA8woLNheSBkQ
KczLWYHMjLiSF4mDKpL2w6QdTGLVn9agRtwcvHbB40fQWxPa56WzZkjnIZpKT4YK
fWzqTTKACrJ6CZtpS5iB4i7sAnCWH/31Rs7K3IKjYzBhMA8GA1UdEwEB/wQFMAMB
Af8wHwYDVR0jBBgwFoAU/4Ixcj75xGZsrTie0bBRiKWQzPUwHQYDVR0OBBYEFP+C
MXI++cRmbK04ntGwUYilkMz1MA4GA1UdDwEB/wQEAwIBBjAKBggqhkjOPQQDAwNp
ADBmAjEA5gVYaWHlLcoNy/EZCL3W/VGSGn5jVASQkZo1kTmZ+gepZpO6yGjUij/6
7W4WAie3AjEA3VoXK3YdZUKWpqxdinlW2Iob35reX8dQj7FbcQwm32pAAOwzkSFx
vmjkI6TZraE3
-----END CERTIFICATE-----
"""


@pytest.mark.parametrize(
    "pem,expected",
    [
        (
            _swiss_sign_cert,
            {
                "issuer": "CN=SwissSign Gold CA - G2,O=SwissSign AG,C=CH",
                "subject": "CN=SwissSign Gold CA - G2,O=SwissSign AG,C=CH",
                "creation": "2006-10-25",
                "expiration": "2036-10-25",
                "fingerprint": "62:DD:0B:E9:B9:F5:0A:16:3E:A0:F8:E7:5C:05:3B:1E:CA:57:EA:55:C8:68:8F:64:7C:68:81:F2:C8:35:7B:95",
            },
        ),
        (
            _etugra_cert,  # ECC certificate
            {
                "issuer": "CN=E-Tugra Global Root CA ECC v3,OU=E-Tugra Trust Center,O=E-Tugra EBG A.S.,L=Ankara,C=TR",
                "subject": "CN=E-Tugra Global Root CA ECC v3,OU=E-Tugra Trust Center,O=E-Tugra EBG A.S.,L=Ankara,C=TR",
                "expiration": "2045-03-12",
                "creation": "2020-03-18",
                "fingerprint": "87:3F:46:85:FA:7F:56:36:25:25:2E:6D:36:BC:D7:F1:6F:C2:49:51:F2:64:E4:7E:1B:95:4F:49:08:CD:CA:13",
            },
        ),
    ],
)
def test_analyze_cert(pem: Callable[[], str], expected: dict) -> None:
    cert = Certificate.load_pem(CertificatePEM(pem()))
    assert vs._CAorCAChain._analyse_cert(cert) == expected


@pytest.mark.parametrize(
    "invalid_pem",
    [
        "",
        "gibberish",
        "-----BEGIN CERTIFICATE-----\n-----END CERTIFICATE-----\n",
    ],
)
def test_validate_value_invalid_certs(invalid_pem: str) -> None:
    with pytest.raises(MKUserError, match="Invalid certificate file"):
        vs._CAorCAChain()._validate_value(invalid_pem, "test")
