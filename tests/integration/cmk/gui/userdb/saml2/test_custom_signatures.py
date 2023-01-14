#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable
from pathlib import Path

import pytest

from cmk.utils.paths import omd_root, saml2_custom_cert_dir

from cmk.gui.userdb.saml2.config import read_certificate_files, write_certificate_files

_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
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
mVytLOl3Ilbx4qC9hMQQuM4jo+yyKk9Z
-----END PRIVATE KEY-----"""

_PUBLIC_KEY = """-----BEGIN CERTIFICATE-----
MIIFYzCCA0ugAwIBAgIUUF6SUs5cfaLTcEyh9OiowZehoiYwDQYJKoZIhvcNAQEL
BQAwQTEYMBYGA1UEAwwPc2FtbDItdGVzdC1zaWduMRgwFgYDVQQKDA9jaGVja21r
LXRlc3RpbmcxCzAJBgNVBAYTAkRFMB4XDTIzMDEyMDEyMjgwOFoXDTMzMDExNzEy
MjgwOFowQTEYMBYGA1UEAwwPc2FtbDItdGVzdC1zaWduMRgwFgYDVQQKDA9jaGVj
a21rLXRlc3RpbmcxCzAJBgNVBAYTAkRFMIICIjANBgkqhkiG9w0BAQEFAAOCAg8A
MIICCgKCAgEAvpQtu1l46qAnfqvYQjN0uMuqpJptYk9OtGG6C/7RoLMiNFD4fJ10
U8d2af2xPMX0cwJJUVEe0/8Ga3ZMxo06M6T674jRegidux3j/gA7ZoaR850xejvG
8244a7E1zbD1+jfKjZHSb3kpsg0W03zacqlnm6KMXpZkWcfBTrbonoOHfCBXeJm8
Gnaxvr6PHTviOtlnZ4GZ3ZU21+p7dZ4vuTS29MnIGjXzUzOt93mwSciZDDjHtyeU
JRL6D8+qK+NNjY8oMQOqZhdNxUMXpQUhyOvWDHWfoNLfVb3dPIrNwxUvyW3hVCaU
oefO/UiyqjcVIcyHCjtw6dGwD3zrbdzfA+Z4tJkmypEsAcrtdN5DF801ARO+mrZ9
hFlGqHUzD4LbhNrWOGHb+vE+Lvk1g+V0ntpOcr9D4rxTlQvCFHOUs7Y9ssKUbAYN
rnr1cOtH1zNeccLmJ0fLi+uv25xItHemPhWlFb3TyxDpD/qQWoiMe4GcFQqtO1sB
JpOD+iB5tJZDtEcIWj92zyWKIw/o6EupIfx5qty/Alps0bROuBInOpckQHNDrseF
7zei9O+jC97oYop4nxPyzZZLRPRjTanZ1Bt07x3Xl5fscQ8jgxcVFoqdTBxW8+UL
qXDGk/qrPh76KDsc9rLOtmfgCQdWh8TRDAuW8dHb7RvyryVpjF8hNUMCAwEAAaNT
MFEwHQYDVR0OBBYEFItmNBslt7lfRHQJPfgIGMIelmaAMB8GA1UdIwQYMBaAFItm
NBslt7lfRHQJPfgIGMIelmaAMA8GA1UdEwEB/wQFMAMBAf8wDQYJKoZIhvcNAQEL
BQADggIBAJtmvhXERUovKsUDIHcNf/7KO4+JuE6HgznDs3jmRhVQ6dqr6cbOS5YX
VJVNwqCBJmDXpPlbM6EzCgjq5pEy+NkSObqlEQEj6e6IGX/NxjzbI0xwfnRzV63A
rInVbG5o+G7GP0qHMCLjkeTiRmjOwrqBEMUP97s0FMkUMdTzLJWBY7mEKwtLYIN+
g7GORf91vxs96X+xS61ovQ4dSrnEm+Zm15NWo1NRWjTgGYnQ46wzjvucgnvIhXnt
t0/CeMXp0kFB7+d0waoNKSkevGgaUjH93Wt+PrVp1KlNP2n2GPOYk6PfKhkSosFH
9gMOgeBsnwx8/kxOZTJ+7k8/96MrPycf404jCiADKw7Rs8Uf9E00Sgswr4cGrxV2
FVDu03n7twSPc7c2AciPSsSXb0snaot1G2i5OAsH12tHSptTVHbe6LoZ55AAZotS
aLs6L9/t0ad/hptf8jfnLIx1Je3+6wkrwwVRSzKvvzSxi8olDfNAFzQ9zeIeutRr
MojdM2wLKQsbrFfAi0cLQSOyVN1R7Efdw5tjEywF8zfbY9OvwQuOAE3rYYKbie9W
qjGyHWLpjTpU4hmTblKY/LW39bYQiXGHe+zJnQ4Vss/ObLT56DwWhU7UKemI25sn
X3gjE5fKgFetIe4GNzR1pP6JEbprY1UD9iUep8yUOOahw1mubZ32
-----END CERTIFICATE-----
"""


def _assert_mode(file_: Path, mode: int) -> None:
    __tracebackhide__ = True  # pylint: disable=unused-variable
    assert file_.stat().st_mode & 0o777 == mode


@pytest.fixture(name="tmp_omd_root")
def fixture_tmp_omd_root(tmp_path: Path) -> Iterable[Path]:
    yield tmp_path


@pytest.fixture(name="custom_signature_cert_dir")
def fixture_custom_signature_cert_dir(
    tmp_omd_root: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterable[Path]:
    monkeypatch.setattr("cmk.gui.userdb.saml2.config.omd_root", tmp_omd_root)

    custom_path = tmp_omd_root / saml2_custom_cert_dir.relative_to(omd_root)
    custom_path.mkdir(parents=True)
    monkeypatch.setattr("cmk.gui.userdb.saml2.config.saml2_custom_cert_dir", custom_path)
    yield custom_path


def test_write_certificate_files(tmp_omd_root: Path, custom_signature_cert_dir: Path) -> None:
    connection_id = "uuid-123"
    option = write_certificate_files(("custom", (_PRIVATE_KEY, _PUBLIC_KEY)), connection_id)

    assert isinstance(option, tuple)

    type_, (private_keyfile_str, public_keyfile_str) = option
    assert type_ == "custom"
    assert not private_keyfile_str.startswith(str(tmp_omd_root))
    assert not public_keyfile_str.startswith(str(tmp_omd_root))

    private_keyfile = Path(tmp_omd_root / private_keyfile_str)
    public_keyfile = Path(tmp_omd_root / public_keyfile_str)

    custom_certdir = custom_signature_cert_dir / connection_id
    assert custom_certdir.exists()
    _assert_mode(custom_certdir, 0o700)

    assert private_keyfile.exists()
    assert public_keyfile.exists()

    for keyfile in [private_keyfile, public_keyfile]:
        _assert_mode(keyfile, 0o600)

    assert private_keyfile.read_text() == _PRIVATE_KEY
    assert public_keyfile.read_text() == _PUBLIC_KEY


def test_read_certificate_files(custom_signature_cert_dir: Path) -> None:
    connection_id = "uuid-123"
    paths = write_certificate_files(("custom", (_PRIVATE_KEY, _PUBLIC_KEY)), connection_id)
    option = read_certificate_files(paths)

    assert isinstance(option, tuple)

    type_, (private_key, public_key) = option

    assert type_ == "custom"
    assert private_key == _PRIVATE_KEY
    assert public_key == _PUBLIC_KEY
