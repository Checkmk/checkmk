#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import fnmatch
import logging
import os
import re
import subprocess
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

import pytest
from psutil import Process

from tests.testlib.site import Site
from tests.testlib.utils import run
from tests.testlib.web_session import CMKWebSession

from cmk.utils.paths import mkbackup_lock_dir

logger = logging.getLogger(__name__)


@contextmanager
def simulate_backup_lock(site: Site, timeout: int = 1200) -> Iterator[None]:
    file_name = f"mkbackup-{site.id}.lock"
    with site.execute(
        [
            "flock",
            "-o",
            "-x",
            "-n",
            str(mkbackup_lock_dir / file_name),
            "sleep",
            str(timeout),
        ]
    ) as p:
        logger.info("Lock file %s", file_name)
        start_time = time.time()
        try:
            yield None
        finally:
            # command returns an exit code only after 'timeout' seconds (sleep).
            if p.poll() == 0:
                raise TimeoutError(
                    f"{file_name} in unlocked state since "
                    f"{((time.time() - start_time) - timeout):.2f} seconds!"
                    "\nThis affects the test design and may result in false positives!"
                )
            for c in Process(p.pid).children(recursive=True):
                if c.name() == "sleep":
                    assert site.run(["kill", str(c.pid)]).returncode == 0


@pytest.fixture(name="cleanup_restore_lock")
def cleanup_restore_lock_fixture(site: Site) -> Iterator[None]:
    """Prevent conflict with file from other test runs

    The restore lock is left behind after the restore. In case a new site
    is created with the same name, there will be a permission conflict
    resulting in a test failure."""

    def rm() -> None:
        restore_lock_path = Path(f"/tmp/restore-{site.id}.state")
        if restore_lock_path.exists():
            subprocess.run(["/usr/bin/sudo", "rm", str(restore_lock_path)], check=True)

    rm()
    try:
        yield
    finally:
        rm()


@pytest.fixture(name="backup_path")
def backup_path_fixture(site: Site) -> Iterator[str]:
    yield from site.system_temp_dir()


@pytest.fixture(
    name="backup_lock_dir",
    params=[
        pytest.param(True, id="lock dir exists"),
        pytest.param(False, id="lock dir not existing"),
    ],
)
def backup_lock_dir_fixture(site: Site, request: pytest.FixtureRequest) -> None:
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
def test_cfg_fixture(web: CMKWebSession, site: Site, backup_path: str) -> Iterator[None]:
    site.ensure_running()

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
        },
        "targets": {
            "test-target": {
                "remote": ("local", {"is_mountpoint": False, "path": backup_path}),
                "title": "t\xe4rget",
            },
        },
    }
    site.write_text_file("etc/check_mk/backup.mk", str(cfg))

    keys = {
        1: {
            "alias": "lala",
            "certificate": "-----BEGIN CERTIFICATE-----\nMIIC1jCCAb4CAQEwDQYJKoZIhvcNAQEFBQAwMTEcMBoGA1UECgwTQ2hlY2tfTUsg\nU2l0ZSBoZXV0ZTERMA8GA1UEAwwIY21rYWRtaW4wHhcNMTcwODEzMjA1MDQ3WhcN\nNDcwODA2MjA1MDQ3WjAxMRwwGgYDVQQKDBNDaGVja19NSyBTaXRlIGhldXRlMREw\nDwYDVQQDDAhjbWthZG1pbjCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEB\nAMLj3TeBAC8/I1iK1MfGW7OjxEUNsM8u3LV80wMlzosgNbszoGWsAwvJzCctZKia\n6C9I4gcEr7y3gwdKWX8ic9qJ/ymG2xD9FAfe2BjqCifKzV3YXmyaHLTngIDSDc5C\nDTLlEV/ncGKheUbvaTQHi2MxOtdouKFaFEYwVFR0TViiNgSA91ERzrz79ABemMDW\nzysK5CMKDj5DhaYlNxz+Rs7qRUY3w3iz0sKWK7yvxNnJCkrVVfp/jlt4RMf6Jr1g\nINFn9MgZZVJUvC6u2zU0q9/g/pa/U5Ae9iW5WI1QnrtDq+sl55EmjVOfMb5V2TEX\ntdMeKLHCxO+uwBBeLy/uwlUCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEAMiK6T6sY\nXehjEA3hcB8X3sada35nG9bZll5IJj1JXLR3iwyStVNeq7ZRWvv/QtWJWSFitf2Q\nBfuNBSgwoZFvMPMv9JXqJG3TYi78kUA0Vx+87TFOSRu93wcvm3etlRdO4OGpIbsk\njBBQ6MnHvR2zUyv6SL144mEcBYYof2NeYtAv+5+OQwyMwLmNTCS/Lz7+TO7vnBmx\nSqlPKXenUj+2sHU/5WjHLzlxWLIr7PpanUr1KmkF7oRAgHQb1tsamqK2KERq68+J\nDIQBtcrEd/kz9N+RW2gnqcjmmhQYP9XP5ZLCTC582EgrhrjBgf2UCIzZJVFz+Jfj\nitd0Om685s7wNg==\n-----END CERTIFICATE-----\n",
            "date": 1502657447.534146,
            "not_downloaded": True,
            "owner": "cmkadmin",
            "private_key": "-----BEGIN ENCRYPTED PRIVATE KEY-----\nMIIFHzBJBgkqhkiG9w0BBQ0wPDAbBgkqhkiG9w0BBQwwDgQIbwWAeEGqIF4CAggA\nMB0GCWCGSAFlAwQBKgQQZdkJLaEpboSu9Gb+yxb9AgSCBNCrLSgQvQC5cv5wiv3r\nDyGZ3pYhDXVPLvtedpvf/PVeBJ9750li6HzH9oH7hyWkXRBBCRcXzcE/VFkIezuV\nBBfkIIibKVh7MePmAsgc9gSTZadpuNx4PHiauJpicj4n3ie0WtpdQrJjSMQRppg/\nA/jzDuJkLCnFVWrhPuD635dsfpjOwhuOlVyYtTUwp4F5/jtmLbhq2fhSEDX43uHH\nHHM4NDu3EbwE8Uzbc0rsx0Qyo5Pk4/dAp30UKtMN/Iv37Z/EjPYk2jKnGHD62Xal\nHwnSkPD39o66BdxVBNc7YCR7BPGp6XNmOPDoRRT0bU1TrlH4sK2KsRyQWwb8njdF\n8jawAXD3RQPyyq7eq+sb6g9c81zD6bwBbVcz26oqGS9oNzliKWfJ/yVLhUXYNYO5\naV1MhpAvApgIpqSPPFlhCl1FnULrY1wl/57GS2/EqDUdhzQDlr1F3Ym+yMlcf1gm\noy72GnDLH66x3NYxo+ylPQa/XrTAyYbr12IPGFONuBrVuSH+b4kV1Rs8ikFTYdgt\nDBmRRQvBxh8dKD+vurfLX2XY2gO3WEAWgD7+HPOoW8PClc9/Nf6giZMOWQvqvcEk\nC18Yv87lLi5lcrhDs9ZgtUUgaW4eue7AVLKAKq74KKDnSFajF7fJmUU2Mbf69cAF\nDtwUjEbocVw/UUUpVH+B42wq+DRhrg++r4JoSn2ZvQ6ltSAkPUuR8Vctp1zTYlZJ\nl7CN3Ua+LFSMDwI9nn275FxbWnMV69TrT7gu5UrFMRsOWpPSApeTTYgPazRbuw/O\ndrOfjTlmWU1FdVSkptwMB+3nQ/8EiXMrBVipSULShGEoJ8focqHRTH5EdSPBC9e0\ne5InVX7b0ARRgCC1TuLL/cmoiOvKqRetRdzaaoaOxt40Kg4u4RFFX7HgzKQ5uIvx\nnMKLVH64lU+IeZAztY7ypjZU8xY5Cgn4JVIbSmMm573uw0uvULp7cW4R3nyeHg1T\n3ZQy609C5WwkGjgH3tV2IdxwHVzZrMv8hiEPT3nuq8fxCcipa9Q1CzoibLj909pQ\ng4upWRPvuTYyOWqCHGhUVaLXGFuFlCXwMFVUlqLbEFeKDejRhQxacCmpyYljiKCQ\nonbUVrzqE8N+Tj0W9GsmKRQUBAbDtEnU2YvDdXzG6noyS+fyrnDkF8/yt7Tdrm4a\ntSKIusvZ3xFloCLBISG+1Cm67qLxaUuol9teiKpx2IzEQycj5ZA63FQ2wFZ+kfk3\nNAhaUfXToKLksx8pojldFo4g1tiX3oGPdblgQ10xgF+eiXzcNiRbce1X2Sfg/urk\nXTN8d5WZuHA4xj0hLH/Xz1CAJjtoEpafiEWB3nmZC4/0poA6MRX1EhCQM5MgeHwo\niaNvgptDQ113MW9FnbdLn5sAoiJ6RWmK8TIW8BJSfnnKyl0lBJG0n5my7rP6ZO1r\nTGkV8cdwy7AoCWQTlfKY7QKHCZMXlyJVSVxuPEnityS+AKKxCYSL3zbPgyXvoFcB\n0XQYTpmEtPM9sJO7VbRYPijjVDLwfe6zPnqw585Fa4W1VtzxW+Y4oKgu6Cn/oGZm\npZ1+gORJtMMD2841ut3QbihY/JYKcCstzFIBzlzAkWHwRI+/wXc9QGtwk1GWriUo\nNcilHP9yv0aXGu8kZ77cd0K18w==\n-----END ENCRYPTED PRIVATE KEY-----\n",
        }
    }

    site.write_text_file("etc/check_mk/backup_keys.mk", f"keys.update({keys})")

    yield None

    #
    # Cleanup code
    #
    site.delete_file("etc/check_mk/backup_keys.mk")
    site.delete_file("etc/check_mk/backup.mk")

    site.ensure_running()


def _execute_backup(site: Site, job_id: str = "testjob") -> str:
    # Perform the backup
    p = site.run(["mkbackup", "backup", job_id])
    assert "Backup completed" in p.stdout, "Invalid output: %r" % p.stdout

    # Check successful backup listing
    p = site.run(["mkbackup", "list", "test-target"])
    assert "%s-complete" % job_id.replace("-", "+") in p.stdout

    if job_id == "testjob-encrypted":
        assert "C0:4E:D4:4B:B4:AB:8B:3F:B4:09:32:CE:7D:A6:CF:76" in p.stdout

    # Extract and return backup id
    matches = re.search(
        r"Backup-ID:\s+(Check_MK-[a-zA-Z0-9_+\.-]+-%s-complete)" % job_id.replace("-", "\\+"),
        p.stdout,
    )
    assert matches is not None
    backup_id = matches.groups()[0]

    return backup_id


def _execute_restore(
    site: Site, backup_id: str, env: Mapping[str, str] | None = None, stop_on_failure: bool = False
) -> None:
    try:
        p = site.run(
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
def test_mkbackup_help(site: Site) -> None:
    p = site.run(["mkbackup"], check=False)
    assert p.stderr == "ERROR: Missing operation mode\n"
    assert p.stdout.startswith("Usage:")
    assert p.returncode == 3


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_list_targets(site: Site) -> None:
    p = site.run(["mkbackup", "targets"], check=False)
    assert p.stderr == ""
    assert p.returncode == 0
    assert "test-target" in p.stdout
    assert "tärget" in p.stdout


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_list_backups(site: Site) -> None:
    p = site.run(["mkbackup", "list", "test-target"])
    assert p.stderr == ""
    assert p.returncode == 0
    assert "Details" in p.stdout


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_list_backups_invalid_target(site: Site) -> None:
    p = site.run(["mkbackup", "list", "xxx"], check=False)
    assert p.stderr.startswith("This backup target does not exist")
    assert p.returncode == 3
    assert p.stdout == ""


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_list_jobs(site: Site) -> None:
    p = site.run(["mkbackup", "jobs"])
    assert p.stderr == ""
    assert p.returncode == 0
    assert "testjob" in p.stdout
    assert "Tästjob" in p.stdout


@pytest.mark.usefixtures("test_cfg", "backup_lock_dir")
def test_mkbackup_simple_backup(site: Site) -> None:
    _execute_backup(site)


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
def test_mkbackup_simple_restore(site: Site) -> None:
    backup_id = _execute_backup(site)
    _execute_restore(site, backup_id)


@pytest.mark.usefixtures("test_cfg")
def test_mkbackup_encrypted_backup(site: Site) -> None:
    _execute_backup(site, job_id="testjob-encrypted")


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
def test_mkbackup_encrypted_backup_and_restore(site: Site) -> None:
    backup_id = _execute_backup(site, job_id="testjob-encrypted")

    env = os.environ.copy()
    env["MKBACKUP_PASSPHRASE"] = "lala"

    _execute_restore(site, backup_id, env)


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
def test_mkbackup_compressed_backup_and_restore(site: Site) -> None:
    backup_id = _execute_backup(site, job_id="testjob-compressed")
    _execute_restore(site, backup_id)


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
def test_mkbackup_no_history_backup_and_restore(site: Site, backup_path: str) -> None:
    backup_id = _execute_backup(site, job_id="testjob-no-history")

    tar_path = os.path.join(backup_path, backup_id, "site-%s.tar" % site.id)

    p = site.execute(["tar", "-tvf", tar_path], stdout=subprocess.PIPE)
    stdout = p.communicate()[0]
    assert p.returncode == 0
    member_names = [l.split(" ")[-1] for l in stdout.split("\n")]

    history = [n for n in member_names if fnmatch.fnmatch(n, "*/var/check_mk/core/archive/*")]
    logs = [n for n in member_names if fnmatch.fnmatch(n, "*/var/log/*.log")]
    rrds = [n for n in member_names if n.endswith(".rrd")]

    assert not history, history
    assert not rrds, rrds
    assert not logs, logs

    _execute_restore(site, backup_id)


@pytest.mark.usefixtures("test_cfg", "cleanup_restore_lock")
def test_mkbackup_locking(site: Site) -> None:
    backup_id = _execute_backup(site, job_id="testjob-no-history")
    with simulate_backup_lock(site):
        with pytest.raises(subprocess.CalledProcessError) as locking_issue:
            _execute_backup(site)
        assert "Failed to get the exclusive backup lock" in str(locking_issue.value.stderr)
        with pytest.raises(subprocess.CalledProcessError) as locking_issue:
            _execute_restore(site, backup_id=backup_id, stop_on_failure=False)
        assert "Failed to get the exclusive backup lock" in str(locking_issue.value.stderr)
