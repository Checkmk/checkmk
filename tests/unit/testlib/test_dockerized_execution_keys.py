#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import tarfile
from io import BytesIO
from pathlib import Path
from typing import cast

import docker.models.containers

from tests.testlib.system.script_helpers.dockerized_execution import copy_key_files

_KEY = b"-----BEGIN OPENSSH PRIVATE KEY-----\nnot a real key\n"


class _Container:
    def __init__(self) -> None:
        self.archives: list[tuple[str, bytes]] = []

    def put_archive(self, path: str, data: bytes) -> bool:
        self.archives.append((path, data))
        return True


def _copy(environ: dict[str, str]) -> tuple[dict[str, str], _Container]:
    container = _Container()
    variables = copy_key_files(cast(docker.models.containers.Container, container), environ)
    return variables, container


def test_test_user_alone_reads_key_copy(tmp_path: Path) -> None:
    """Only the test user can read the copy of the key.

    ssh runs as the test user, and it refuses a key that other users can read. A copy that belongs
    to root, or that has mode 0644, would make every Windows test fail at login.
    """
    (key_file := tmp_path / "key").write_bytes(_KEY)

    variables, container = _copy({"WINDOWS_HOST_SSH_KEY_FILE": str(key_file)})

    [(target, data)] = container.archives
    with tarfile.open(fileobj=BytesIO(data)) as tar:
        copy = tar.getmember(str(Path(variables["QA_WINDOWS_HOST_SSH_KEY"]).relative_to(target)))
        content = tar.extractfile(copy)
        assert content is not None and content.read() == _KEY
        directory = tar.getmember("ci-keys")
    assert (copy.mode, copy.uid, copy.gid) == (0o600, os.getuid(), os.getgid())
    assert (directory.mode, directory.uid, directory.gid) == (0o700, os.getuid(), os.getgid())


def test_qa_variable_holds_path_not_key(tmp_path: Path) -> None:
    """The QA_ variable names the copy and never holds the key itself.

    The test container writes every QA_ variable into the job log. A key in a QA_ variable would
    therefore end up in the log.
    """
    (key_file := tmp_path / "key").write_bytes(_KEY)

    variables, _container = _copy({"WINDOWS_HOST_SSH_KEY_FILE": str(key_file)})

    assert variables == {"QA_WINDOWS_HOST_SSH_KEY": "/tmp/ci-keys/qa_windows_host_ssh_key"}


def test_without_key_file_nothing_reaches_container() -> None:
    """Without a key file, nothing reaches the test container.

    run-dockerized.py calls copy_key_files() for every target, not only for the agent update tests.
    A QA_ variable that named a missing copy would make the Windows tests fail at login instead of
    skipping.
    """
    variables, container = _copy({})

    assert (variables, container.archives) == ({}, [])
