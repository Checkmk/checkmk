#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fnmatch
import logging
import os
import re
import subprocess
from collections.abc import Generator, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.testlib.pytest_helpers.calls import exit_pytest_on_exceptions
from tests.testlib.site import get_site_factory, Site
from tests.testlib.utils import DISTROS_MISSING_WHITELIST_ENVIRONMENT_FOR_SU, run
from tests.testlib.web_session import CMKWebSession

from cmk.utils.paths import mkbackup_lock_dir

logger = logging.getLogger(__name__)


@pytest.fixture(name="site_for_mkbackup_tests", scope="module")
def site(request: pytest.FixtureRequest) -> Generator[Site]:
    """
    The tests in this module heavily modify the site they operate on. For example, they restore the
    site from a previously created backup without history, which results in a site without baked
    agents. To avoid impacting any subsequent tests, we create a dedicate site for the tests in this
    module.
    """
    with exit_pytest_on_exceptions(
        exit_msg=f"Failure in site creation using fixture '{__file__}::{request.fixturename}'!"
    ):
        yield from get_site_factory(prefix="int_").get_test_site(
            name="test_mkbup",
            save_results=False,
        )


@contextmanager
def simulate_backup_lock(site_for_mkbackup_tests: Site) -> Iterator[None]:
    lock_path = mkbackup_lock_dir / f"mkbackup-{site_for_mkbackup_tests.id}.lock"
    logger.info("Lock file: %s", lock_path)

    file_locking_proc: subprocess.Popen[str]
    with site_for_mkbackup_tests.python_helper("helper_mkbackup_file_lock.py").execute(
        encoding="utf-8",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
    ) as file_locking_proc:
        assert file_locking_proc.stdin
        assert file_locking_proc.stdout

        file_locking_proc.stdin.write(f"{lock_path}\n")
        file_locking_proc.stdin.flush()
        assert file_locking_proc.stdout.readline().strip() == "locked"
        logger.info("%s is now locked", lock_path)

        try:
            yield None
        finally:
            logger.info("Shutting down file locking process")
            assert file_locking_proc.poll() is None, (
                "The file locking process should still be running. The test design relies on this."
            )
            further_stdout, stderr = file_locking_proc.communicate(timeout=10)

    assert not further_stdout, "No further output expected from file locking process"
    assert not stderr, "No stderr output expected from file locking process"


@pytest.fixture(name="cleanup_restore_lock")
def cleanup_restore_lock_fixture(site_for_mkbackup_tests: Site) -> Iterator[None]:
    """Prevent conflict with file from other test runs

    The restore lock is left behind after the restore. In case a new site
    is created with the same name, there will be a permission conflict
    resulting in a test failure."""

    def rm() -> None:
        restore_lock_path = Path(f"/tmp/restore-{site_for_mkbackup_tests.id}.state")
        if restore_lock_path.exists():
            subprocess.run(["/usr/bin/sudo", "rm", str(restore_lock_path)], check=True)

    rm()
    try:
        yield
    finally:
        rm()


@pytest.fixture(name="backup_path")
def backup_path_fixture(site_for_mkbackup_tests: Site) -> Iterator[str]:
    yield from site_for_mkbackup_tests.system_temp_dir()


@pytest.fixture(
    name="backup_lock_dir",
    params=[
        pytest.param(True, id="lock dir exists"),
        pytest.param(False, id="lock dir not existing"),
    ],
)
def backup_lock_dir_fixture(site_for_mkbackup_tests: Site, request: pytest.FixtureRequest) -> None:
    # This fixture should prepare two possible scenarios:
    # 1) The folder for the backup locks does already exist *and* has the correct permissions
    # 2) The folder does not yet exist.
    # --> In both scenarios mkbackup must not fail

    # In the second case the "omd" command executed as root ensures that the directory is created.
    # This functionality has been added to the "omd" command, because it is the only command which
    # can reliably create the directory when started as root.
    if not request.param:
        run(["rm", "-r", str(mkbackup_lock_dir)], sudo=True)
        assert not mkbackup_lock_dir.exists()

        # This omd call triggers the creation of the lock dir with the correct permissions. In
        # production there is always at least one command executed before being able to execute
        # the backup code. So we can assume it has been executed before.
        run(["omd", "status"], sudo=True)

    assert mkbackup_lock_dir.exists()
    backup_permission_mask = oct(mkbackup_lock_dir.stat().st_mode)[-4:]
    assert backup_permission_mask == "0770"
    assert mkbackup_lock_dir.group() == "omd"


@pytest.fixture(name="test_cfg", scope="function")
def test_cfg_fixture(
    web: CMKWebSession, site_for_mkbackup_tests: Site, backup_path: str
) -> Iterator[None]:
    site_for_mkbackup_tests.ensure_running()

    cfg = {
        "jobs": {
            "testjob": {
                "compress": False,
                "encrypt": None,
                "schedule": None,
                "target": "test-target",
                "title": "T\xe4stjob",
            },
            "testjob-no-history": {
                "no_history": True,
                "compress": False,
                "encrypt": None,
                "schedule": None,
                "target": "test-target",
                "title": "T\xe4stjob no history",
            },
            "testjob-compressed": {
                "compress": True,
                "encrypt": None,
                "schedule": None,
                "target": "test-target",
                "title": "T\xe4stjob",
            },
            "testjob-encrypted": {
                "compress": False,
                "encrypt": "C0:4E:D4:4B:B4:AB:8B:3F:B4:09:32:CE:7D:A6:CF:76",
                "schedule": None,
                "target": "test-target",
                "title": "T\xe4stjob",
            },
            "testjob-encrypted-expired-cert": {
                "compress": True,
                "encrypt": "C8:3B:C2:BA:00:15:D5:5B:04:B0:81:96:D9:EE:BB:AE",
                "schedule": None,
                "target": "test-target",
                "title": "T\xe4stjob",
            },
        },
        "targets": {
            "test-target": {
                "remote": ("local", {"is_mountpoint": False, "path": backup_path}),
                "title": "t\xe4rget",
            },
        },
    }
    site_for_mkbackup_tests.write_file("etc/check_mk/backup.mk", str(cfg))

    # A 2048 bit RSA key in a cert signed with sha1WithRSAEncryption. This made it to our tests at
    # some point so until proven otherwise, assume it made it to production and backups still have
    # to work with it.
    cert_weak_crypto = """-----BEGIN CERTIFICATE-----
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
"""
    priv_key_weak_crypto = """-----BEGIN ENCRYPTED PRIVATE KEY-----
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
"""

    # An expired certificate. See comment in test_mkbackup_encrypted_backup_and_restore_expired().
    cert_expired = """-----BEGIN CERTIFICATE-----
MIIFETCCAvmgAwIBAgIUYQ9YZQkO7Pj6fgaDt08Avz2fgekwDQYJKoZIhvcNAQEN
BQAwIjEOMAwGA1UEAwwFaGVsbG8xEDAOBgNVBAoMB3Rlc3RpbmcwHhcNMjUwNjAx
MDk1NTA2WhcNMjUwNjAxMDk1NTA2WjAiMQ4wDAYDVQQDDAVoZWxsbzEQMA4GA1UE
CgwHdGVzdGluZzCCAiIwDQYJKoZIhvcNAQEBBQADggIPADCCAgoCggIBALZji35q
yvP0kG0xLiBMkHAGqKtqnKzdbf0KnoCdP1gBB/tVHagMaqbJj7pny5E0v/LzxQ3m
itJqJShV4pXVzfUNd6aZ5Psi+Mn4myGyr7QEblCUbQW0wEg8Kk9N0CmOJtPirFY7
pzbQWHaw01yEU0sr0lT9oJiOyY4h6hGEbapPRNf7o26p3f0Tz5GlNmk6p7dxcmQ9
8TcB+q5wdOCWKugB0mi2E3Zuad3f3+UtNi8x7s/wBAcy0bVGxntrlMu3PcD9ykV3
1QA12tuHolJ5fpaRrAl5FXieWAffKXeoSKPJmR9f5MYdFYDwDkJg3tkVBBq2blJi
wt3Iarh1HcaJOOMQd+d7jG6lGHSSeUAKtj2orgeVNhDfJ4RDj3tv5XrcT9CCMXov
uRvf5ocE29N8iW3QEwvaa5FhP5l3BYEw2dEmOmwpu6alq97wH/A7cKutldzDDPD+
U+4aG+GybpuYn8U6NducxBqfopIPqxpEEx759zZNRXSdGynrSCtNcL2AnLUV93B5
GDM1Fl70S8Nlarg3OG11KtqMiSyLbYcQ7VRL9xiJ7IGsO3b6lBP/C7yeWoq9Zq1x
xuOpehp2TKcwIn12/9CRAEVKkmFAOIGihcS21I7aRBcwlndkQ3apGWTWvz5ax3NH
hU7EWuuZHQZrkUMKlNdPUJRlNzLu/bY+jkL/AgMBAAGjPzA9MAwGA1UdEwEB/wQC
MAAwHQYDVR0OBBYEFBC3Kwtnq032l8kDaYO0sBWieKMgMA4GA1UdDwEB/wQEAwIH
gDANBgkqhkiG9w0BAQ0FAAOCAgEAZotoibzBfUjJMCH6PndNUdQXeUYL+nTYjPQ1
nffkQmpJwtWmNSq8PJLz3uCQBBN5oGFMgbfq9WfWwNPXRX2AfUUDW0ExJKOnjGe4
PFUkLcKJ3jvauPG2CIWmr48TyO7gb1q4c31ZgY1nigvJqJ24Z2KxOqavDo6/qrHm
C+GdKslqth6+vS/uIGIh1MHC/dEYla4jSYQILFeaP5WCu92OuPm4Gy+4XQtil2LM
nc/RgpUYpOBKbUaBSWP4YpJzP9w5BWjJhUAz19Px4DDSjG1DeU0i+fcrTNHiAvFy
aVr6eib6V5Y0CluCqgBFORsRRmIamuPeVkEh2c81iuJGNwGF5Up9vqYx3e/ZA8v+
+HSE9RPeMuQ1nEa9T/mTXahtX5UjZIVN9JraIA9a3gCqyzPFTI4a5Z/3tmijPPKK
CCFhWwa9gHIx/Vm+GPyOlZmze/YIHUdSjWYFPM4MZPN8yGtAfOHS5hK60PcsiSIl
MfVj/T3EH5o+5bW+2sPqWBuQWqnR+jg9No/p6SF3Pfs63FpUz73LHrr5HPPqZ40S
P1/KDeOt5XQJ4z6KKvFtL2S0K/H5Y++9frNj90ZZZuNO+ug2QoWzr0Rjc98X7Z5/
Li7hl5PC5S1phorJekRc7VGf8k22TQSrmdcffDR5pGoI2+DTQgpYfbxsA1NTsPqI
COHDc3M=
-----END CERTIFICATE-----"""
    priv_key_expired = """-----BEGIN ENCRYPTED PRIVATE KEY-----
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
-----END ENCRYPTED PRIVATE KEY-----
"""

    keys = {
        1: {
            "alias": "lala",
            "certificate": cert_weak_crypto,  # C8:3B:C2:BA:00:15:D5:5B:04:B0:81:96:D9:EE:BB:AE
            "date": 1502657447.534146,
            "not_downloaded": True,
            "owner": "cmkadmin",
            "private_key": priv_key_weak_crypto,
        },
        2: {
            "alias": "expired",
            "certificate": cert_expired,  # C0:4E:D4:4B:B4:AB:8B:3F:B4:09:32:CE:7D:A6:CF:76
            "date": 1502657447.534146,
            "not_downloaded": False,
            "owner": "cmkadmin",
            "private_key": priv_key_expired,
        },
    }

    site_for_mkbackup_tests.write_file("etc/check_mk/backup_keys.mk", f"keys.update({keys})")

    yield None

    #
    # Cleanup code
    #
    site_for_mkbackup_tests.delete_file("etc/check_mk/backup_keys.mk")
    site_for_mkbackup_tests.delete_file("etc/check_mk/backup.mk")

    site_for_mkbackup_tests.ensure_running()


def _execute_backup(site_for_mkbackup_tests: Site, job_id: str = "testjob") -> str:
    # Perform the backup
    p = site_for_mkbackup_tests.run(["mkbackup", "backup", job_id])
    assert "Backup completed" in p.stdout, "Invalid output: %r" % p.stdout

    # Check successful backup listing
    p = site_for_mkbackup_tests.run(["mkbackup", "list", "test-target"])
    assert "%s-complete" % job_id.replace("-", "+") in p.stdout

    if job_id == "testjob-encrypted":
        assert "C0:4E:D4:4B:B4:AB:8B:3F:B4:09:32:CE:7D:A6:CF:76" in p.stdout
    elif job_id == "testjob-encrypted-expired-cert":
        assert "C8:3B:C2:BA:00:15:D5:5B:04:B0:81:96:D9:EE:BB:AE" in p.stdout

    # Extract and return backup id
    matches = re.search(
        r"Backup-ID:\s+(Check_MK-[a-zA-Z0-9_+\.-]+-%s-complete)" % job_id.replace("-", "\\+"),
        p.stdout,
    )
    assert matches is not None
    backup_id = matches.groups()[0]

    return backup_id


def _execute_restore(
    site_for_mkbackup_tests: Site,
    backup_id: str,
    env: Mapping[str, str] | None = None,
    stop_on_failure: bool = False,
) -> None:
    try:
        p = site_for_mkbackup_tests.run(
            ["mkbackup", "restore", "test-target", backup_id],
            env=env,
            preserve_env=["MKBACKUP_PASSPHRASE"] if env and "MKBACKUP_PASSPHRASE" in env else None,
        )
    except subprocess.CalledProcessError as excp:
        if stop_on_failure:
            pytest.exit(f"Stop test run after failed restore!\n{str(excp)}")
        raise excp
    assert "Restore completed" in p.stdout, "Invalid output: %r" % p.stdout


# .
#   .--Command line--------------------------------------------------------.
#   |   ____                                          _   _ _              |
#   |  / ___|___  _ __ ___  _ __ ___   __ _ _ __   __| | | (_)_ __   ___   |
#   | | |   / _ \| '_ ` _ \| '_ ` _ \ / _` | '_ \ / _` | | | | '_ \ / _ \  |
#   | | |__| (_) | | | | | | | | | | | (_| | | | | (_| | | | | | | |  __/  |
#   |  \____\___/|_| |_| |_|_| |_| |_|\__,_|_| |_|\__,_| |_|_|_| |_|\___|  |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Test the basic functionality of the command line interface. Detailed |
#   | functional test should be implemented in unit tests (see below).     |
#   '----------------------------------------------------------------------'


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_help(site_for_mkbackup_tests: Site) -> None:
    p = site_for_mkbackup_tests.run(["mkbackup"], check=False)
    assert p.stderr == "ERROR: Missing operation mode\n"
    assert p.stdout.startswith("Usage:")
    assert p.returncode == 3


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_list_targets(site_for_mkbackup_tests: Site) -> None:
    p = site_for_mkbackup_tests.run(["mkbackup", "targets"], check=False)
    assert p.stderr == ""
    assert p.returncode == 0
    assert "test-target" in p.stdout
    assert "tärget" in p.stdout


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_list_backups(site_for_mkbackup_tests: Site) -> None:
    p = site_for_mkbackup_tests.run(["mkbackup", "list", "test-target"])
    assert p.stderr == ""
    assert p.returncode == 0
    assert "Details" in p.stdout


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_list_backups_invalid_target(site_for_mkbackup_tests: Site) -> None:
    p = site_for_mkbackup_tests.run(["mkbackup", "list", "xxx"], check=False)
    assert p.stderr.startswith("This backup target does not exist")
    assert p.returncode == 3
    assert p.stdout == ""


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_list_jobs(site_for_mkbackup_tests: Site) -> None:
    p = site_for_mkbackup_tests.run(["mkbackup", "jobs"])
    assert p.stderr == ""
    assert p.returncode == 0
    assert "testjob" in p.stdout
    assert "Tästjob" in p.stdout


@pytest.mark.usefixtures("test_cfg", "backup_lock_dir")
def test_mkbackup_simple_backup(site_for_mkbackup_tests: Site) -> None:
    _execute_backup(site_for_mkbackup_tests)


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
def test_mkbackup_simple_restore(site_for_mkbackup_tests: Site) -> None:
    backup_id = _execute_backup(site_for_mkbackup_tests)
    _execute_restore(site_for_mkbackup_tests, backup_id)


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_encrypted_backup(site_for_mkbackup_tests: Site) -> None:
    _execute_backup(site_for_mkbackup_tests, job_id="testjob-encrypted")


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
@pytest.mark.skipif(
    os.environ.get("DISTRO") in DISTROS_MISSING_WHITELIST_ENVIRONMENT_FOR_SU,
    reason="This test would use preserve-env, which needs --white-list-environment under alma-8, which is not available",
)
def test_mkbackup_encrypted_backup_and_restore(site_for_mkbackup_tests: Site) -> None:
    backup_id = _execute_backup(site_for_mkbackup_tests, job_id="testjob-encrypted")

    env = os.environ.copy()
    env["MKBACKUP_PASSPHRASE"] = "lala"

    _execute_restore(site_for_mkbackup_tests, backup_id, env)


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
@pytest.mark.skipif(
    os.environ.get("DISTRO") in DISTROS_MISSING_WHITELIST_ENVIRONMENT_FOR_SU,
    reason="This test would use preserve-env, which needs --white-list-environment under alma-8, which is not available",
)
def test_mkbackup_encrypted_backup_and_restore_expired(site_for_mkbackup_tests: Site) -> None:
    # Note: This test deliberately uses an expired certificate for the backup key. This MUST not
    # cause the test to fail.
    # The key is wrapped in an x.509 cert for no real reason, but we have to assume that the cert
    # has expired on customer installations by now. This should never prevent them from restoring
    # their backups.
    backup_id = _execute_backup(site_for_mkbackup_tests, job_id="testjob-encrypted-expired-cert")

    env = os.environ.copy()
    env["MKBACKUP_PASSPHRASE"] = "cmk"

    _execute_restore(site_for_mkbackup_tests, backup_id, env)


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
def test_mkbackup_compressed_backup_and_restore(site_for_mkbackup_tests: Site) -> None:
    backup_id = _execute_backup(site_for_mkbackup_tests, job_id="testjob-compressed")
    _execute_restore(site_for_mkbackup_tests, backup_id)


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
def test_mkbackup_no_history_backup_and_restore(
    site_for_mkbackup_tests: Site, backup_path: str
) -> None:
    backup_id = _execute_backup(site_for_mkbackup_tests, job_id="testjob-no-history")

    tar_path = os.path.join(backup_path, backup_id, "site-%s.tar" % site_for_mkbackup_tests.id)

    p = site_for_mkbackup_tests.execute(["tar", "-tvf", tar_path], stdout=subprocess.PIPE)
    stdout = p.communicate()[0]
    assert p.returncode == 0
    member_names = [l.split(" ")[-1] for l in stdout.split("\n")]

    history = [n for n in member_names if fnmatch.fnmatch(n, "*/var/check_mk/core/archive/*")]
    logs = [n for n in member_names if fnmatch.fnmatch(n, "*/var/log/*.log")]
    rrds = [n for n in member_names if n.endswith(".rrd")]

    assert not history, history
    assert not rrds, rrds
    assert not logs, logs

    _execute_restore(site_for_mkbackup_tests, backup_id)


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
def test_mkbackup_locking(site_for_mkbackup_tests: Site) -> None:
    backup_id = _execute_backup(site_for_mkbackup_tests, job_id="testjob-no-history")
    with simulate_backup_lock(site_for_mkbackup_tests):
        with pytest.raises(subprocess.CalledProcessError) as locking_issue:
            _execute_backup(site_for_mkbackup_tests)
        assert "Failed to get the exclusive backup lock" in str(locking_issue.value.stderr)
        with pytest.raises(subprocess.CalledProcessError) as locking_issue:
            _execute_restore(site_for_mkbackup_tests, backup_id=backup_id, stop_on_failure=False)
        assert "Failed to get the exclusive backup lock" in str(locking_issue.value.stderr)
