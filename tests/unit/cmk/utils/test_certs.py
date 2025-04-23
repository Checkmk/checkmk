#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from datetime import datetime, UTC
from pathlib import Path
from zoneinfo import ZoneInfo

import time_machine
from cryptography import x509
from dateutil.relativedelta import relativedelta

from cmk.ccc.site import SiteId

from cmk.utils.certs import CN_TEMPLATE, RootCA

from cmk.crypto.certificate import Certificate, CertificateWithPrivateKey
from cmk.crypto.keys import PlaintextPrivateKeyPEM, PrivateKey
from cmk.crypto.x509 import SAN, SubjectAlternativeNames, X509Name


def _rsa_private_keys_equal(key_a: PrivateKey, key_b: PrivateKey) -> bool:
    """Check if two keys are the same RSA key"""
    # Assert keys are RSA keys here just to cut corners on type checking. ed25519 keys don't have
    # private_numbers(). Also, no-one else needs __eq__ on PrivateKey at the moment.
    return key_a.get_raw_rsa_key().private_numbers() == key_b.get_raw_rsa_key().private_numbers()


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


class Test_CNTemplate:
    def test_site_name_matches(self) -> None:
        assert CN_TEMPLATE.extract_site("CN=Site 'heute' local CA") == SiteId("heute")

    def test_site_name_does_not_match(self) -> None:
        assert CN_TEMPLATE.extract_site("CN=This is not a CA of a site") is None

    def test_format_site(self) -> None:
        assert CN_TEMPLATE.format(SiteId("hurz")) == "Site 'hurz' local CA"


def test_create_root_ca_and_key(tmp_path: Path) -> None:
    filename = tmp_path / "test_certs_testCA"
    with time_machine.travel(datetime.fromtimestamp(100, tz=ZoneInfo("UTC"))):
        ca = RootCA.load_or_create(filename, "peter", key_size=1024)

    assert ca.private_key.get_raw_rsa_key().key_size == 1024
    assert ca.certificate.common_name == "peter"

    assert str(ca.certificate.not_valid_before) == "1970-01-01 00:01:40+00:00", (
        "creation time is respected"
    )
    assert str(ca.certificate.not_valid_after) == "1980-01-01 00:01:40+00:00", (
        "is valid for 10 years"
    )
    assert ca.certificate.public_key == ca.private_key.public_key

    # check extensions
    assert ca.certificate._cert.extensions.get_extension_for_class(
        x509.SubjectKeyIdentifier
    ).value == x509.SubjectKeyIdentifier.from_public_key(ca.certificate.public_key._key), (
        "subject key identifier is set and corresponds to the cert's public key"
    )

    assert ca.certificate._cert.extensions.get_extension_for_class(
        x509.BasicConstraints
    ).value == x509.BasicConstraints(ca=True, path_length=0), "is a CA certificate"

    assert ca.certificate._cert.extensions.get_extension_for_class(
        x509.KeyUsage
    ).value == x509.KeyUsage(
        digital_signature=False,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=True,
        crl_sign=True,
        encipher_only=False,
        decipher_only=False,
    ), "has the expected key usages"

    assert filename.exists()
    loaded = RootCA.load(filename)
    assert loaded.certificate._cert == ca.certificate._cert
    assert _rsa_private_keys_equal(loaded.private_key, ca.private_key)


def test_sign_csr_with_local_ca() -> None:
    # To test that 'sign_csr' sets the issuer correctly (regression), make a longer chain:
    # "peters_mom" -> "peter" (RootCA instance) -> "peters_daughter" (via sign_csr)
    #
    # In reality the RootCA is self-signed of course, but for testing purposes it isn't here.
    # The regression was that RootCA set its own issuer as the issuer of signed CSRs. Thus we need
    # RootCA's subject and issuer to not be the same.

    peters_mom = CertificateWithPrivateKey.generate_self_signed(
        common_name="peters_mom",
        organization="Checkmk Testing",
        key_size=1024,
        is_ca=True,
    )

    peter_key = PrivateKey.load_pem(
        PlaintextPrivateKeyPEM(
            """
-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VwBCIEIK/fWo6sKC4PDigGfEntUd/o8KKs76Hsi03su4QhpZox
-----END PRIVATE KEY-----"""
        )
    )
    peter_cert = Certificate._create(
        subject_public_key=peter_key.public_key,
        subject_name=X509Name.create(common_name="peter"),
        subject_alternative_names=None,
        expiry=relativedelta(days=1),
        start_date=datetime.now(UTC),
        is_ca=True,
        issuer_signing_key=peters_mom.private_key,
        issuer_name=peters_mom.certificate.subject,
    )
    peter_root_ca = RootCA(peter_cert, peter_key)
    alt_names = SubjectAlternativeNames([SAN.dns_name("peters_daughter")])
    with time_machine.travel(datetime.fromtimestamp(567892121, tz=ZoneInfo("UTC"))):
        daughter_cert, daughter_key = peter_root_ca.issue_new_certificate(
            common_name="peters_daughter",
            organization="Checkmk Testing",
            subject_alternative_names=alt_names,
            expiry=relativedelta(days=100),
            key_size=1024,
        )

    assert str(daughter_cert.not_valid_before) == "1987-12-30 19:48:41+00:00"
    assert str(daughter_cert.not_valid_after) == "1988-04-08 19:48:41+00:00"

    daughter_cert.verify_is_signed_by(peter_cert)
    assert daughter_cert.public_key == daughter_key.public_key, "correct public key in the cert"

    assert daughter_cert.common_name == "peters_daughter", "subject CN is the daughter"
    assert daughter_cert.subject_alternative_names == alt_names, "subject alt name is the daughter"
    assert daughter_cert.issuer == peter_cert.subject, "issuer is peter"
