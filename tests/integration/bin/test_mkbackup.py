#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pxlint: disable=redefined-outer-name

import fcntl
import fnmatch
import functools
import os
import re
import subprocess
import tarfile
from contextlib import contextmanager
from typing import Generator

import pytest

from tests.testlib.site import Site

from cmk.utils.paths import mkbackup_lock_dir
from cmk.utils.python_printer import pformat


@contextmanager
def simulate_backup_lock(site_id):
    with open(mkbackup_lock_dir / f"mkbackup-{site_id}.lock", "ab") as flock:
        fcntl.flock(flock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield flock


@pytest.fixture(name="backup_path")
def backup_path_fixture(tmp_path):

    backup_path = str(tmp_path / "backup")

    if not os.path.exists(backup_path):
        os.makedirs(backup_path)

    return backup_path


@pytest.fixture(
    name="backup_lock_dir",
    params=[
        {"exists": True},
        {"exists": False},
    ],
)
def backup_lock_dir_fixture(request):
    # This fixture should prepare two possible scenarios:
    # 1) The folder for the backup locks does already exist *and* has the correct permissions
    # 2) The folder does not yet exist.
    # --> In both scenarios mkbackup must not fail

    # As get_site_factory executes "sudo omd start", the backup dir will already be created as
    # root. Therefore we need to perform the setup steps as root as well (due to the sticky bit of
    # /run/lock).
    if request.param["exists"]:
        subprocess.call(["sudo", "mkdir", str(mkbackup_lock_dir)])
        subprocess.call(["sudo", "chmod", "0770", str(mkbackup_lock_dir)])
        subprocess.call(["sudo", "chgrp", "omd", str(mkbackup_lock_dir)])

    else:
        subprocess.call(["sudo", "rm", "-r", str(mkbackup_lock_dir)])


@pytest.fixture(name="test_cfg", scope="function")
def test_cfg_fixture(web, site: Site, backup_path) -> Generator:
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
    site.write_text_file("etc/check_mk/backup.mk", pformat(cfg))

    keys = {
        1: {
            "alias": "lala",
            "certificate": "-----BEGIN CERTIFICATE-----\nMIIC1jCCAb4CAQEwDQYJKoZIhvcNAQEFBQAwMTEcMBoGA1UECgwTQ2hlY2tfTUsg\nU2l0ZSBoZXV0ZTERMA8GA1UEAwwIY21rYWRtaW4wHhcNMTcwODEzMjA1MDQ3WhcN\nNDcwODA2MjA1MDQ3WjAxMRwwGgYDVQQKDBNDaGVja19NSyBTaXRlIGhldXRlMREw\nDwYDVQQDDAhjbWthZG1pbjCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEB\nAMLj3TeBAC8/I1iK1MfGW7OjxEUNsM8u3LV80wMlzosgNbszoGWsAwvJzCctZKia\n6C9I4gcEr7y3gwdKWX8ic9qJ/ymG2xD9FAfe2BjqCifKzV3YXmyaHLTngIDSDc5C\nDTLlEV/ncGKheUbvaTQHi2MxOtdouKFaFEYwVFR0TViiNgSA91ERzrz79ABemMDW\nzysK5CMKDj5DhaYlNxz+Rs7qRUY3w3iz0sKWK7yvxNnJCkrVVfp/jlt4RMf6Jr1g\nINFn9MgZZVJUvC6u2zU0q9/g/pa/U5Ae9iW5WI1QnrtDq+sl55EmjVOfMb5V2TEX\ntdMeKLHCxO+uwBBeLy/uwlUCAwEAATANBgkqhkiG9w0BAQUFAAOCAQEAMiK6T6sY\nXehjEA3hcB8X3sada35nG9bZll5IJj1JXLR3iwyStVNeq7ZRWvv/QtWJWSFitf2Q\nBfuNBSgwoZFvMPMv9JXqJG3TYi78kUA0Vx+87TFOSRu93wcvm3etlRdO4OGpIbsk\njBBQ6MnHvR2zUyv6SL144mEcBYYof2NeYtAv+5+OQwyMwLmNTCS/Lz7+TO7vnBmx\nSqlPKXenUj+2sHU/5WjHLzlxWLIr7PpanUr1KmkF7oRAgHQb1tsamqK2KERq68+J\nDIQBtcrEd/kz9N+RW2gnqcjmmhQYP9XP5ZLCTC582EgrhrjBgf2UCIzZJVFz+Jfj\nitd0Om685s7wNg==\n-----END CERTIFICATE-----\n",  # noqa: E501
            "date": 1502657447.534146,
            "not_downloaded": True,
            "owner": "cmkadmin",
            "private_key": "-----BEGIN ENCRYPTED PRIVATE KEY-----\nMIIFHzBJBgkqhkiG9w0BBQ0wPDAbBgkqhkiG9w0BBQwwDgQIbwWAeEGqIF4CAggA\nMB0GCWCGSAFlAwQBKgQQZdkJLaEpboSu9Gb+yxb9AgSCBNCrLSgQvQC5cv5wiv3r\nDyGZ3pYhDXVPLvtedpvf/PVeBJ9750li6HzH9oH7hyWkXRBBCRcXzcE/VFkIezuV\nBBfkIIibKVh7MePmAsgc9gSTZadpuNx4PHiauJpicj4n3ie0WtpdQrJjSMQRppg/\nA/jzDuJkLCnFVWrhPuD635dsfpjOwhuOlVyYtTUwp4F5/jtmLbhq2fhSEDX43uHH\nHHM4NDu3EbwE8Uzbc0rsx0Qyo5Pk4/dAp30UKtMN/Iv37Z/EjPYk2jKnGHD62Xal\nHwnSkPD39o66BdxVBNc7YCR7BPGp6XNmOPDoRRT0bU1TrlH4sK2KsRyQWwb8njdF\n8jawAXD3RQPyyq7eq+sb6g9c81zD6bwBbVcz26oqGS9oNzliKWfJ/yVLhUXYNYO5\naV1MhpAvApgIpqSPPFlhCl1FnULrY1wl/57GS2/EqDUdhzQDlr1F3Ym+yMlcf1gm\noy72GnDLH66x3NYxo+ylPQa/XrTAyYbr12IPGFONuBrVuSH+b4kV1Rs8ikFTYdgt\nDBmRRQvBxh8dKD+vurfLX2XY2gO3WEAWgD7+HPOoW8PClc9/Nf6giZMOWQvqvcEk\nC18Yv87lLi5lcrhDs9ZgtUUgaW4eue7AVLKAKq74KKDnSFajF7fJmUU2Mbf69cAF\nDtwUjEbocVw/UUUpVH+B42wq+DRhrg++r4JoSn2ZvQ6ltSAkPUuR8Vctp1zTYlZJ\nl7CN3Ua+LFSMDwI9nn275FxbWnMV69TrT7gu5UrFMRsOWpPSApeTTYgPazRbuw/O\ndrOfjTlmWU1FdVSkptwMB+3nQ/8EiXMrBVipSULShGEoJ8focqHRTH5EdSPBC9e0\ne5InVX7b0ARRgCC1TuLL/cmoiOvKqRetRdzaaoaOxt40Kg4u4RFFX7HgzKQ5uIvx\nnMKLVH64lU+IeZAztY7ypjZU8xY5Cgn4JVIbSmMm573uw0uvULp7cW4R3nyeHg1T\n3ZQy609C5WwkGjgH3tV2IdxwHVzZrMv8hiEPT3nuq8fxCcipa9Q1CzoibLj909pQ\ng4upWRPvuTYyOWqCHGhUVaLXGFuFlCXwMFVUlqLbEFeKDejRhQxacCmpyYljiKCQ\nonbUVrzqE8N+Tj0W9GsmKRQUBAbDtEnU2YvDdXzG6noyS+fyrnDkF8/yt7Tdrm4a\ntSKIusvZ3xFloCLBISG+1Cm67qLxaUuol9teiKpx2IzEQycj5ZA63FQ2wFZ+kfk3\nNAhaUfXToKLksx8pojldFo4g1tiX3oGPdblgQ10xgF+eiXzcNiRbce1X2Sfg/urk\nXTN8d5WZuHA4xj0hLH/Xz1CAJjtoEpafiEWB3nmZC4/0poA6MRX1EhCQM5MgeHwo\niaNvgptDQ113MW9FnbdLn5sAoiJ6RWmK8TIW8BJSfnnKyl0lBJG0n5my7rP6ZO1r\nTGkV8cdwy7AoCWQTlfKY7QKHCZMXlyJVSVxuPEnityS+AKKxCYSL3zbPgyXvoFcB\n0XQYTpmEtPM9sJO7VbRYPijjVDLwfe6zPnqw585Fa4W1VtzxW+Y4oKgu6Cn/oGZm\npZ1+gORJtMMD2841ut3QbihY/JYKcCstzFIBzlzAkWHwRI+/wXc9QGtwk1GWriUo\nNcilHP9yv0aXGu8kZ77cd0K18w==\n-----END ENCRYPTED PRIVATE KEY-----\n",  # noqa: E501
        }
    }

    site.write_text_file("etc/check_mk/backup_keys.mk", "keys.update(%s)" % pformat(keys))

    yield None

    #
    # Cleanup code
    #
    site.delete_file("etc/check_mk/backup_keys.mk")
    site.delete_file("etc/check_mk/backup.mk")

    site.ensure_running()


def _execute_backup(site: Site, job_id="testjob"):
    # Perform the backup
    p = site.execute(
        ["mkbackup", "backup", job_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    stdout, stderr = p.communicate()
    assert stderr == ""
    assert p.wait() == 0
    assert "Backup completed" in stdout, "Invalid output: %r" % stdout

    # Check successful backup listing
    p = site.execute(
        ["mkbackup", "list", "test-target"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    stdout, stderr = p.communicate()
    assert stderr == ""
    assert p.wait() == 0
    assert "%s-complete" % job_id.replace("-", "+") in stdout

    if job_id == "testjob-encrypted":
        assert "C0:4E:D4:4B:B4:AB:8B:3F:B4:09:32:CE:7D:A6:CF:76" in stdout

    # Extract and return backup id
    print(stdout)
    matches = re.search(
        r"Backup-ID:\s+(Check_MK-[a-zA-Z0-9_+\.-]+-%s-complete)" % job_id.replace("-", "\\+"),
        stdout,
    )
    assert matches is not None
    backup_id = matches.groups()[0]

    return backup_id


def _execute_restore(site: Site, backup_id, env=None, restore_site=True):
    p = site.execute(
        ["mkbackup", "restore", "test-target", backup_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        encoding="utf-8",
    )
    stdout, stderr = p.communicate()

    try:
        assert stderr == ""
        assert "Restore completed" in stdout, "Invalid output: %r" % stdout
        assert p.wait() == 0
    except Exception:
        if restore_site:
            # Bring back the site in case the restore test fails which may leave the
            # site in a stopped state
            site.start()
        raise


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


def test_mkbackup_help(site: Site) -> None:
    p = site.execute(["mkbackup"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8")
    stdout, stderr = p.communicate()
    assert stderr == "ERROR: Missing operation mode\n"
    assert stdout.startswith("Usage:")
    assert p.wait() == 3


def test_mkbackup_list_unconfigured(site: Site) -> None:
    p = site.execute(
        ["mkbackup", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
    )
    stderr = p.communicate()[1]
    assert stderr.startswith("mkbackup is not configured yet")
    assert p.wait() == 3


def test_mkbackup_list_targets(site: Site, test_cfg) -> None:
    p = site.execute(
        ["mkbackup", "targets"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
    )
    stdout, stderr = p.communicate()
    assert stderr == ""
    assert p.wait() == 0
    assert "test-target" in stdout
    assert "tärget" in stdout


def test_mkbackup_list_backups(site: Site, test_cfg) -> None:
    p = site.execute(
        ["mkbackup", "list", "test-target"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    stdout, stderr = p.communicate()
    assert stderr == ""
    assert p.wait() == 0
    assert "Type" in stdout
    assert "Details" in stdout


def test_mkbackup_list_backups_invalid_target(site: Site, test_cfg) -> None:
    p = site.execute(
        ["mkbackup", "list", "xxx"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
    )
    stdout, stderr = p.communicate()
    assert stderr.startswith("This backup target does not exist")
    assert p.wait() == 3
    assert stdout == ""


def test_mkbackup_list_jobs(site: Site, test_cfg) -> None:
    p = site.execute(
        ["mkbackup", "jobs"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
    )
    stdout, stderr = p.communicate()
    assert stderr == ""
    assert p.wait() == 0
    assert "testjob" in stdout
    assert "Tästjob" in stdout


def test_mkbackup_simple_backup(site: Site, test_cfg, backup_lock_dir) -> None:
    _execute_backup(site)


def test_mkbackup_simple_restore(site: Site, test_cfg) -> None:
    backup_id = _execute_backup(site)
    _execute_restore(site, backup_id)


def test_mkbackup_encrypted_backup(site: Site, test_cfg) -> None:
    _execute_backup(site, job_id="testjob-encrypted")


def test_mkbackup_encrypted_backup_and_restore(site, test_cfg) -> None:
    backup_id = _execute_backup(site, job_id="testjob-encrypted")

    env = os.environ.copy()
    env["MKBACKUP_PASSPHRASE"] = "lala"

    _execute_restore(site, backup_id, env)


def test_mkbackup_compressed_backup_and_restore(site, test_cfg) -> None:
    backup_id = _execute_backup(site, job_id="testjob-compressed")
    _execute_restore(site, backup_id)


def test_mkbackup_no_history_backup_and_restore(site, test_cfg, backup_path) -> None:
    backup_id = _execute_backup(site, job_id="testjob-no-history")

    tar_path = os.path.join(backup_path, backup_id, "site-%s.tar" % site.id)

    with tarfile.open(tar_path) as tar_file:
        member_names = [m.name for m in tar_file.getmembers()]
    history = [n for n in member_names if fnmatch.fnmatch(n, "*/var/check_mk/core/archive/*")]
    logs = [n for n in member_names if fnmatch.fnmatch(n, "*/var/log/*.log")]
    rrds = [n for n in member_names if n.endswith(".rrd")]

    assert not history, history
    assert not rrds, rrds
    assert not logs, logs

    _execute_restore(site, backup_id)


def test_mkbackup_locking(site, test_cfg) -> None:
    backup_id = _execute_backup(site, job_id="testjob-no-history")
    with simulate_backup_lock(site.id):
        for what in (
            _execute_backup,
            functools.partial(_execute_restore, backup_id=backup_id),
        ):
            with pytest.raises(AssertionError) as locking_issue:
                what(site)  # type: ignore
            assert "Failed to get the exclusive backup lock" in str(locking_issue)
