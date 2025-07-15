#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import binascii
import io
from unittest import mock

import pytest

from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.crypto.deprecated import certificate_md5_digest
from cmk.utils.backup.stream import BackupStream, MKBackupStream, RestoreStream

BACKUP_KEYS = {
    1: {
        "alias": "lala",
        "date": 1502657447.534146,
        "not_downloaded": True,
        "owner": "cmkadmin",
        "certificate": """-----BEGIN CERTIFICATE-----
MIIC1jCCAb4CAQEwDQYJKoZIhvcNAQEFBQAwMTEcMBoGA1UECgwTQ2hlY2tfTUsg
U2l0ZSBoZXV0ZTERMA8GA1UEAwwIY21rYWRtaW4wHhcNMTcwODEzMjA1MDQ3WhcN
NDcwODA2MjA1MDQ3WjAxMRwwGgYDVQQKDBNDaGVja19NSyBTaXRlIGhldXRlMREw
DwYDVQQDDAhjbWthZG1pbjCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEB
AMLj3TeBAC8/I1iK1MfGW7OjxEUNsM8u3LV80wMlzosgNbszoGWsAwvJzCctZKia
6C9I4gcEr7y3gwdKWX8ic9qJ/ymG2xD9FAfe2BjqCifKzV3YXmyaHLTngIDSDc5C
DTLlEV/ncGKheUbvaTQHi2MxOtdouKFaFEYwVFR0TViiNgSA91ERzrz79ABemMDW
zysK5CMKDj5DhaYlNxz+Rs7qRUY3w3iz0sKWK7yvxNnJCkrVVfp/jlt4RMf6Jr1g
INFn9MgZZVJUvC6u2zU0q9/g/pa/U5Ae9iW5WI1QnrtDq+sl55EmjVOfMb5V2TEX
tdMeKLHCxO+uwBBeLy/uwlUCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEAMiK6T6sY
XehjEA3hcB8X3sada35nG9bZll5IJj1JXLR3iwyStVNeq7ZRWvv/QtWJWSFitf2Q
BfuNBSgwoZFvMPMv9JXqJG3TYi78kUA0Vx+87TFOSRu93wcvm3etlRdO4OGpIbsk
jBBQ6MnHvR2zUyv6SL144mEcBYYof2NeYtAv+5+OQwyMwLmNTCS/Lz7+TO7vnBmx
SqlPKXenUj+2sHU/5WjHLzlxWLIr7PpanUr1KmkF7oRAgHQb1tsamqK2KERq68+J
DIQBtcrEd/kz9N+RW2gnqcjmmhQYP9XP5ZLCTC582EgrhrjBgf2UCIzZJVFz+Jfj
itd0Om685s7wNg==
-----END CERTIFICATE-----
""",
        "private_key": """-----BEGIN ENCRYPTED PRIVATE KEY-----
MIIFHzBJBgkqhkiG9w0BBQ0wPDAbBgkqhkiG9w0BBQwwDgQIbwWAeEGqIF4CAggA
MB0GCWCGSAFlAwQBKgQQZdkJLaEpboSu9Gb+yxb9AgSCBNCrLSgQvQC5cv5wiv3r
DyGZ3pYhDXVPLvtedpvf/PVeBJ9750li6HzH9oH7hyWkXRBBCRcXzcE/VFkIezuV
BBfkIIibKVh7MePmAsgc9gSTZadpuNx4PHiauJpicj4n3ie0WtpdQrJjSMQRppg/
A/jzDuJkLCnFVWrhPuD635dsfpjOwhuOlVyYtTUwp4F5/jtmLbhq2fhSEDX43uHH
HHM4NDu3EbwE8Uzbc0rsx0Qyo5Pk4/dAp30UKtMN/Iv37Z/EjPYk2jKnGHD62Xal
HwnSkPD39o66BdxVBNc7YCR7BPGp6XNmOPDoRRT0bU1TrlH4sK2KsRyQWwb8njdF
8jawAXD3RQPyyq7eq+sb6g9c81zD6bwBbVcz26oqGS9oNzliKWfJ/yVLhUXYNYO5
aV1MhpAvApgIpqSPPFlhCl1FnULrY1wl/57GS2/EqDUdhzQDlr1F3Ym+yMlcf1gm
oy72GnDLH66x3NYxo+ylPQa/XrTAyYbr12IPGFONuBrVuSH+b4kV1Rs8ikFTYdgt
DBmRRQvBxh8dKD+vurfLX2XY2gO3WEAWgD7+HPOoW8PClc9/Nf6giZMOWQvqvcEk
C18Yv87lLi5lcrhDs9ZgtUUgaW4eue7AVLKAKq74KKDnSFajF7fJmUU2Mbf69cAF
DtwUjEbocVw/UUUpVH+B42wq+DRhrg++r4JoSn2ZvQ6ltSAkPUuR8Vctp1zTYlZJ
l7CN3Ua+LFSMDwI9nn275FxbWnMV69TrT7gu5UrFMRsOWpPSApeTTYgPazRbuw/O
drOfjTlmWU1FdVSkptwMB+3nQ/8EiXMrBVipSULShGEoJ8focqHRTH5EdSPBC9e0
e5InVX7b0ARRgCC1TuLL/cmoiOvKqRetRdzaaoaOxt40Kg4u4RFFX7HgzKQ5uIvx
nMKLVH64lU+IeZAztY7ypjZU8xY5Cgn4JVIbSmMm573uw0uvULp7cW4R3nyeHg1T
3ZQy609C5WwkGjgH3tV2IdxwHVzZrMv8hiEPT3nuq8fxCcipa9Q1CzoibLj909pQ
g4upWRPvuTYyOWqCHGhUVaLXGFuFlCXwMFVUlqLbEFeKDejRhQxacCmpyYljiKCQ
onbUVrzqE8N+Tj0W9GsmKRQUBAbDtEnU2YvDdXzG6noyS+fyrnDkF8/yt7Tdrm4a
tSKIusvZ3xFloCLBISG+1Cm67qLxaUuol9teiKpx2IzEQycj5ZA63FQ2wFZ+kfk3
NAhaUfXToKLksx8pojldFo4g1tiX3oGPdblgQ10xgF+eiXzcNiRbce1X2Sfg/urk
XTN8d5WZuHA4xj0hLH/Xz1CAJjtoEpafiEWB3nmZC4/0poA6MRX1EhCQM5MgeHwo
iaNvgptDQ113MW9FnbdLn5sAoiJ6RWmK8TIW8BJSfnnKyl0lBJG0n5my7rP6ZO1r
TGkV8cdwy7AoCWQTlfKY7QKHCZMXlyJVSVxuPEnityS+AKKxCYSL3zbPgyXvoFcB
0XQYTpmEtPM9sJO7VbRYPijjVDLwfe6zPnqw585Fa4W1VtzxW+Y4oKgu6Cn/oGZm
pZ1+gORJtMMD2841ut3QbihY/JYKcCstzFIBzlzAkWHwRI+/wXc9QGtwk1GWriUo
NcilHP9yv0aXGu8kZ77cd0K18w==
-----END ENCRYPTED PRIVATE KEY-----
""",
    }
}
MKBACKUP_PASSPHRASE = "lala"
KEY_IDENT = "C0:4E:D4:4B:B4:AB:8B:3F:B4:09:32:CE:7D:A6:CF:76"


@mock.patch(
    "cmk.utils.backup.stream.MKBackupStream._load_backup_keys",
    lambda _: BACKUP_KEYS,
)
@mock.patch("os.environ", {"MKBACKUP_PASSPHRASE": MKBACKUP_PASSPHRASE})
def _run_stream(Stream: type[MKBackupStream], data: bytes) -> bytes:
    s = Stream(stream=io.BytesIO(data), is_alive=lambda: False, key_ident=KEY_IDENT, debug=False)
    return b"".join(s.process())


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"", id="empty string"),
        pytest.param(16 * b"A", id="full block of padding"),
        pytest.param((16 * 1024 + 5) * b"b", id="read from stream multiple times"),
    ],
)
def test_roundtrip(data: bytes) -> None:
    """Check if we can encrypt something and decrypt it again"""
    encrypted = _run_stream(BackupStream, data)
    assert encrypted.startswith(b"2\x00256\x00")  # version marker and key length

    restored = _run_stream(RestoreStream, encrypted)
    assert restored == data


def test_restore_existing() -> None:
    """Check that we can still decrypt this data that was encrypted in the past.

    This helps to ensure we're still compatible with existing backups. The test data was created
    with version 2 of the container format.
    """
    encrypted = binascii.unhexlify(
        b"320032353600690030f5da2b37a50ac8a26e9fecab21ef67ebf08ee0bbffdd7207ee995d974ca613891ea344"
        b"279eef1046015ef2117c43f84f062087e4a970aeabd9fde7dd081162accc1854be7abe8207172188e327d94a"
        b"6712f10996c5ae47586815dd0dac6273de2ddcf9eca0cbb3e91b23d9ef9db817dcb048ff80ed3d690ab92d4f"
        b"cee9a79dde6363cc723aa53fc71b03788cd9bf14e38f718a6c8e83ab5f73ed6a4b0b94036ff0f27e2c01a5b4"
        b"8ac11742830d1104dbfb75ef2f5f6a0c5cd279272934bc4190d6ac398abc189cf8ce5d31707b119493d3a7c4"
        b"8cbd7d64e8c8620afc5927bb68c01b5d06066ea3485cce8501764ac24e7af7db7c8e1cc085291d99d4140003"
        b"eaccadbbfb91ef84a356216c1bdcc96c84955d78d782495522fc0863cc2303638db05891d740d5d7ea215177"
        b"84e4b2ed4beb7c9c9e1f067ae3c6617c6589a1732fe15b24149b91169995e7659662d4"
    )
    restored = _run_stream(RestoreStream, encrypted)
    assert (
        restored
        == b"We are stuck with technology when what we really want is just stuff that works."
    )


def test_calculate_digest() -> None:
    """Test the MD5 certificate digest calculation that we don't use outside of backup"""
    pem = CertificatePEM(BACKUP_KEYS[1]["certificate"])  # type: ignore[arg-type]
    assert certificate_md5_digest(Certificate.load_pem(pem)) == KEY_IDENT
