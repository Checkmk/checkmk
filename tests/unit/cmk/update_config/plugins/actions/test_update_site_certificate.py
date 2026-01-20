#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from pathlib import Path

import pytest

from cmk.ccc.site import omd_site, SiteId
from cmk.crypto.hash import HashAlgorithm
from cmk.update_config.lib import ExpiryVersion
from cmk.update_config.plugins.actions.update_site_certificate import UpdateSiteCertificate
from cmk.utils.certs import SiteCA
from cmk.utils.paths import omd_root

CERTIFICATE_DIRECTORY = omd_root / Path("etc/ssl")


def dummy_site_ca() -> str:
    return """-----BEGIN PRIVATE KEY-----
MIICeAIBADANBgkqhkiG9w0BAQEFAASCAmIwggJeAgEAAoGBAMn1UiDKNT3B/woi
OEqV0nDpoZf6RND98UsFVf7QmzYnsRoSCKulFpJOmLLJqcZWnNhPPR+sAuFrOMC9
BXdOQFCRG48XzHN8tP3tbNHFt4F6hGLJMZCXmeAolxeGBxcY1eYLxuw0CD61mjy0
43ft/C+Qxg6paxdi2eaBeveyFySxAgMBAAECgYAGDWAEs4qc6y9lclkVgx/nWlkJ
YOqnCLUudl55YG8GVHIuQdQYsL3YbJqO4RRBaV8R7G38gP8lGj19KSz8wk+TDN8c
4J0Rg0C4RqjEyzH0ePA7Z/sUqOWUZVLZevNBxSvOTnTLe22Gz2X1eyITxh83QpLm
hXVhZc5L+KGW9+gdQQJBAPFihTqnOyJxKCLAdCL3Ai6sAmwFBcEtfxpLJI3o5ctX
hNpYk/wtvUwmcboHZPOdwlXZENqZvYSnw8cZpNf2dR0CQQDWL6+zLlPxsm4d9W5T
JKWAacxDTU5cIJwdg+SoP/0bwbTXWTyORZ59Kim6yXJdkEyryN+FULfSw+RNNQ7g
gP2lAkEAjyWe3r6nqfAzHhDFjqqvR6BIO2jrFbl2Y9BmGCYiiGkZZycac3Voig1O
akTSUEqhIan9fbWol0+qIZuKj2wf3QJBAKz5f/zF+lckkZeyQTH2U458YtErmo/+
afXQMZbLbp6+9kxALg58HP3aUi8eRzVWtwS4ygNBZ+NX/oV3xxb6NV0CQQDlv4oH
G0tQIZb1B4/CrCbBnh69L0RGt3h7y906lRuVV0Ng/Mj5Sj8R+R/wVqEcNylRXhSE
VXzJSdPU5tH3gi42
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIICRjCCAa+gAwIBAgIUIzp8u+4nxaYgZwyOUGJS8j/4yUAwDQYJKoZIhvcNAQEN
BQAwOzEdMBsGA1UEAwwUU2l0ZSAndjI1MCcgbG9jYWwgQ0ExGjAYBgNVBAoMEUNo
ZWNrbWsgU2l0ZSB2MjUwMCAXDTI1MDgwODA3MjExN1oYDzIwNTIxMjIzMDcyMTE3
WjA7MR0wGwYDVQQDDBRTaXRlICd2MjUwJyBsb2NhbCBDQTEaMBgGA1UECgwRQ2hl
Y2ttayBTaXRlIHYyNTAwgZ8wDQYJKoZIhvcNAQEBBQADgY0AMIGJAoGBAMn1UiDK
NT3B/woiOEqV0nDpoZf6RND98UsFVf7QmzYnsRoSCKulFpJOmLLJqcZWnNhPPR+s
AuFrOMC9BXdOQFCRG48XzHN8tP3tbNHFt4F6hGLJMZCXmeAolxeGBxcY1eYLxuw0
CD61mjy043ft/C+Qxg6paxdi2eaBeveyFySxAgMBAAGjRTBDMBIGA1UdEwEB/wQI
MAYBAf8CAQAwHQYDVR0OBBYEFIQRSx/cHJE904wSPdCC4QwVqyREMA4GA1UdDwEB
/wQEAwIBBjANBgkqhkiG9w0BAQ0FAAOBgQBc3tkQmugWuO7Xyj5EQ9Je3SxUYKR6
qU5sQQ76fOT9hRcQvhszZKqRFj2flvNs/lCf1JMrOGbBgAWceGmrlubaJgK/MGbf
eGAPlxJ2poGukdPO/ae6pEDcwK7zz6nA2PxmvcAZmm5/BAlxA7NYjJaXG/TPcOBh
51Q0/VZEBkeOUw==
-----END CERTIFICATE-----"""


def dummy_site_certificate_with_AKI() -> str:
    return """-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBALZiVlv8VtWbOlR8
QD0m9U9NqCHeu7OwyV5JNn5QdPaV6bw+tqORuLj86ICf3A0kizHFm2WbGTs/QBau
XCOFd5aqAzz4q7dSG3eWZOU/jLpVn5+VfwybQeLVDLS//5YDXhbFtcNyPJvU/a1r
5SpyL6ok4IJ3dRILw+3PgmbA4Q6ZAgMBAAECgYEApEJMpOvPCPKUxiJheLHtnU7D
bj27r0o5EcG+YmTz8mFx8ShKNWa4h2K/w5g2B2AyPNFL82aMgt+kSMkgEp3R5UnZ
DS5j1iHzuNWFlrZv7lZycwyHBapoSJQY4TlVwsBoAsnfhSfynkDuJDVQrga28GNC
9Bie75X2Tfuvj/j73EECQQDjsTUSLqRgWh/kbnJyjNWQJlz1z6pKtRtHOI7eOQzo
M0+9/hN7S/gipfmXsOpSB1LKoW4qdsk0g8xg8xvYyGwbAkEAzQ8aZYwc+0oBQfcW
3nVcCNpxMU11HVhNthJfZrT+1/IRRnDofVNK/mpqvY9aL64+ZTJHU11SHlr4M8ra
T1/zWwJAL+HWPUqdur15M3qeisRfLP9EUVUohKltYR7dvJHWywXvYQ8LXcRuHCs3
P9Uuka2ElaQ5HKj6SxbkZgb59i6/vQJBAJrvF2W0eM1Q/CRIOio5CCHUUoQK3zsd
1hGETjq+9HJa/rx3YOIYReh2pVG2d1DhWVmCpKuTLhGrcC9JzKr+d1MCQH7staMD
uej5krUOBz0bwK6lC501g6HIuNmfHiwTIAEPf7d+1hym//LCfDoKPKFt+OPe+VyZ
Bn9I2oc9drempic=
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIIEDjCCAfagAwIBAgIUXunUxrBA2F873ScTOvemqjOhgkIwDQYJKoZIhvcNAQEN
BQAwTzExMC8GA1UEAwwoU2l0ZSAndjI1MCcgbG9jYWwgQ0EgMjAyNS0xMi0wMVQx
NDowMzoyMDEaMBgGA1UECgwRQ2hlY2ttayBTaXRlIHYyNTAwHhcNMjUxMjA0MDg1
ODA3WhcNMjYwMzA0MDg1ODA3WjArMQ0wCwYDVQQDDAR2MjUwMRowGAYDVQQKDBFD
aGVja21rIFNpdGUgdjI1MDCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAtmJW
W/xW1Zs6VHxAPSb1T02oId67s7DJXkk2flB09pXpvD62o5G4uPzogJ/cDSSLMcWb
ZZsZOz9AFq5cI4V3lqoDPPirt1Ibd5Zk5T+MulWfn5V/DJtB4tUMtL//lgNeFsW1
w3I8m9T9rWvlKnIvqiTggnd1EgvD7c+CZsDhDpkCAwEAAaOBiTCBhjAMBgNVHRMB
Af8EAjAAMB0GA1UdDgQWBBQ8Bqit1qR6vrJJJPo1l5t2+wwazTAfBgNVHSMEGDAW
gBS+Q4hHV3jEtsSZhYu1+YHVk0XFvDAOBgNVHQ8BAf8EBAMCB4AwJgYDVR0RBB8w
HYIEdjI1MIYVdXJuOmNoZWNrbWstc2l0ZTp2MjUwMA0GCSqGSIb3DQEBDQUAA4IC
AQB0WrrjM7gjppc4Z5sF6PyMEqhjVNKbVyAIymokEHbgZ+ArhUSlYDyYOYuqHCa+
7zLAllbJMSkm1CC5cPKe8lyqYbjPlqHS1zk9Ubwqx9wq9BLWZABDaG3iwq0Q3+WU
jvsSLkzqF7jSY1+K5SgNZ1VH4bV4fmS40O+U/I1jH6Tr26gDRvP9sW86iArmv1HK
JvuRgs1sRP01n+q0wrvZDn/tMW1O2L2MCxxBjK+ElQ5Tdgx3XX8wPi1mUOvLyTFM
j3ksVtC/YLvlFDmWtySzUawHNKqDpHBQnU2HicF0Gzvh1E00tH4STzPw6uqMjVlF
9W+lYU2HgvJqUhsma48sak3a9zs+gBEr4IHsD+PqE74khRHCTOr2PS8/HV6H4PmR
Y4cIRi+8MH1SnU4qAYiLZfFLPRKiX4DedWMNyBdTTX7hd1vXWhE5fh3DRI6B6e59
/pyV9903PNy6EvhMr90dQ2q8M87Z1uZ5yALaAv/pzN294EONc912BCjdVlLclpPz
jlRG5WjyIBLPeZePMIZPGqZ/0qJu4oDzE8mdBFcqXoc2BkMFIAOSz6yBqxCdILE3
PFfgTedQSRK/rtBa2mrYRR8IHUnRBXMRz2L4DpbR0CVZnfDC3wvPUXvAcZeneD/y
GipFb4yX4O/4UsXfSFxda5R9WeW/RBKp3BOe+rzDEIjRkw==
-----END CERTIFICATE-----"""


def dummy_site_certificate_without_AKI() -> str:
    return """-----BEGIN PRIVATE KEY-----
MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBALxrPAjc9Y3cmY8L
uA+KBQ2jxoi8KefI0ck7M4lPzXg4HrG3eme7KS/A90FcCqcg3+N5DK8alXPJsOl8
8bcfzWXUClBJbxsQEmk7aIGskzxetTWKl9DFUsOnjecyWr+6N3CrRlGfEvaBn7m1
jlYqo9O+nZw1BpUubpaS9BhCFk1PAgMBAAECgYEAtoWyzGsvvFLctoOFtBfhuUrT
whV1CsGw55zf2b5irni+0y2H+ACIb2ggnUIKV8gy2mqi7OV1rYrORADzLpAyKS7k
D8uE8XTwnaomh2ibPcY+Ldierzr/9ijamvGiTa+4ZhV724SxD0a0493kV4c7BLiv
XsO2drycEf0I9kyfWzECQQDfOjjqmJ7YXkdNz7Rh6d+GRprx0YDKbujvXEZihRqG
XMvU99qAFC+DqfkwaHQrl26+RJwvMVGmYWEuMbQSMofTAkEA2BTEortums+yCt8I
HpvzDcnrweUQYe3HBaUTf/8Rl8zpDrhFZDiLnsEzHgn/Retel0/M52ZUwOOLJl/f
82GTFQJBAKr6OGAPuBL321uRDJO2g5ugdstjcWccHlQ/9DU/x/pEF2eu0/AoBeCu
Dwxx5RECczNO7+YBu41ZpwqvzUHm7DsCQCgL4U2PkzYZ3BNrtmOF34vkqk7rFxgv
Kz1+lJiaOzZ5AZB60lF6sVWg1Mpya98XehZs8brJGlgNU9Ku3iCLKukCQGGoe+zZ
phRaYeQ5jZpTT3fJ1OGNzaGc5e1TGhvqXiPqa8t1EAtNRCUpRLtBHnUgU/q4LEYI
tFH6XoHhoqg2UDM=
-----END PRIVATE KEY-----
-----BEGIN CERTIFICATE-----
MIID6zCCAdOgAwIBAgIUSzomL6v3iXl4zl+5+1E8FKgRk3swDQYJKoZIhvcNAQEN
BQAwTzExMC8GA1UEAwwoU2l0ZSAndjI1MCcgbG9jYWwgQ0EgMjAyNS0xMi0wMVQx
NDowMzoyMDEaMBgGA1UECgwRQ2hlY2ttayBTaXRlIHYyNTAwHhcNMjUxMjA0MDg1
MzI3WhcNMjYwMzA0MDg1MzI3WjArMQ0wCwYDVQQDDAR2MjUwMRowGAYDVQQKDBFD
aGVja21rIFNpdGUgdjI1MDCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEAvGs8
CNz1jdyZjwu4D4oFDaPGiLwp58jRyTsziU/NeDgesbd6Z7spL8D3QVwKpyDf43kM
rxqVc8mw6Xzxtx/NZdQKUElvGxASaTtogayTPF61NYqX0MVSw6eN5zJav7o3cKtG
UZ8S9oGfubWOViqj076dnDUGlS5ulpL0GEIWTU8CAwEAAaNnMGUwDAYDVR0TAQH/
BAIwADAdBgNVHQ4EFgQU2E/0+DJ+DFVJCkTm2iH73anVVOUwDgYDVR0PAQH/BAQD
AgeAMCYGA1UdEQQfMB2CBHYyNTCGFXVybjpjaGVja21rLXNpdGU6djI1MDANBgkq
hkiG9w0BAQ0FAAOCAgEAik4qUddBEPRFHrytduymBl37y9I4fY42gGqPDOdPkyaK
jHUyn/FGG5Rb7rAlljHl1LQ+OITm0QUUqhvBchediq8HG6Bp8cAi+BP8d8nh8KOn
h6jqmL5lGNRFFr/wtP4RlAn7nLTq8kEYLHHwxkPvorx+MxV9Xjzk51kyPiXsj5Pt
Gp/MfDPTVFCuvYMrZQvcMCzjSRBYldO5XdsEOiYoQO3MMw8/e9cJRECihRz2ZuDg
h0qoKnvj/XUqznER1sug0kW0mo0p4OeO83jQ1fNgHlDP4Oq0bCk0cWidbA9EQtD1
Ck+lfIl7g+vFKndpt0IatAbHTT18g0YiHu9IfUiUQlbpLYFv6NK4mvnoau4xxr2/
usoavfeu+TjSoG4Mg5HpzbIut8w50VMxq6if5+XPtsYsZzJuzjInRpMS5frqcYf+
haAC2r4Dp2RUdhog5cJLW8J/BJwIVC6t9Fd4FMqrDlHjjyic29tiuKfhWAevRd7z
5rrLqjukcECTMz+9yYo5zf5WXfgyYs9QzVq6S+qwsrG4/LJ0XwnDwTYvYvelKChd
+XSR94vBlIJ6PjjZGWySZBuOXehcGbm+NvKXBB1uwjH7yW2Z5fOLeAXiN6SDGY50
2ed8G6pXCLyL2zSyCBZ3afu1BJFr1dJiL2StyBEnzx7aQfz/JE5mmB8i4wxd20c=
-----END CERTIFICATE-----"""


@pytest.fixture
def setup_certificate_paths() -> Path:
    site_ca_path = CERTIFICATE_DIRECTORY / Path("ca.pem")
    site_ca_path.parent.mkdir(parents=True, exist_ok=True)
    site_ca_path.write_text(dummy_site_ca())

    site_cert_path = CERTIFICATE_DIRECTORY / Path(f"sites/{omd_site()}.pem")
    site_cert_path.parent.mkdir(parents=True, exist_ok=True)

    return site_cert_path


def run_update_site_certificate() -> None:
    UpdateSiteCertificate(
        name="update-site-certificate",
        title="Update Site Certificate",
        sort_index=100,
        expiry_version=ExpiryVersion.CMK_300,
        continue_on_failure=True,
    )(logging.getLogger())


def get_site_certificate_fingerprint() -> str:
    site_ca = SiteCA.load(CERTIFICATE_DIRECTORY)
    site_cert = site_ca.load_site_certificate(CERTIFICATE_DIRECTORY, SiteId(omd_site()))
    assert site_cert is not None
    return site_cert.certificate.fingerprint(HashAlgorithm.Sha256).hex(sep=":").upper()


def test_non_existing_site_certificate(setup_certificate_paths: Path) -> None:
    run_update_site_certificate()

    assert "BEGIN CERTIFICATE" in setup_certificate_paths.read_text()


def test_site_certificate_with_AKI(setup_certificate_paths: Path) -> None:
    setup_certificate_paths.write_text(dummy_site_certificate_with_AKI())

    run_update_site_certificate()

    assert "BEGIN CERTIFICATE" in setup_certificate_paths.read_text()

    assert get_site_certificate_fingerprint() == (
        "54:39:B8:49:E6:3C:BE:B0:4C:26:91:DA:26:D3:99:2C:"
        "33:8D:31:F7:A2:B7:46:D4:4B:E0:74:91:A5:26:9F:6A"
    )


def test_site_certificate_without_AKI(setup_certificate_paths: Path) -> None:
    setup_certificate_paths.write_text(dummy_site_certificate_without_AKI())

    run_update_site_certificate()

    assert "BEGIN CERTIFICATE" in setup_certificate_paths.read_text()

    assert get_site_certificate_fingerprint() != (
        "54:39:B8:49:E6:3C:BE:B0:4C:26:91:DA:26:D3:99:2C:"
        "33:8D:31:F7:A2:B7:46:D4:4B:E0:74:91:A5:26:9F:6A"
    )
