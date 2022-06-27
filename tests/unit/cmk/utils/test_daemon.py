#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os

import pytest

import cmk.utils.daemon as daemon
import cmk.utils.store as store
from cmk.utils.exceptions import MKGeneralException


@pytest.fixture(autouse=True)
def cleanup_locks():
    yield
    store.release_all_locks()


def test_lock_with_pid_file(tmp_path) -> None:
    pid_file = tmp_path / "test.pid"

    daemon.lock_with_pid_file(pid_file)

    assert store.have_lock("%s" % pid_file)

    with pid_file.open() as f:
        assert int(f.read()) == os.getpid()


def test_cleanup_locked_pid_file(tmp_path) -> None:
    pid_file = tmp_path / "test.pid"

    assert not store.have_lock("%s" % pid_file)
    daemon.lock_with_pid_file(pid_file)
    assert store.have_lock("%s" % pid_file)

    daemon._cleanup_locked_pid_file(pid_file)

    assert not store.have_lock("%s" % pid_file)


def test_pid_file_lock_context_manager(tmp_path) -> None:
    pid_file = tmp_path / "test.pid"

    assert not store.have_lock("%s" % pid_file)

    with daemon.pid_file_lock(pid_file):
        assert store.have_lock("%s" % pid_file)


def test_pid_file_lock_context_manager_exception(tmp_path) -> None:
    pid_file = tmp_path / "test.pid"

    assert not store.have_lock("%s" % pid_file)
    try:
        with daemon.pid_file_lock(pid_file):
            assert store.have_lock("%s" % pid_file)
            raise MKGeneralException("bla")
    except MKGeneralException:
        pass

    assert not store.have_lock("%s" % pid_file)
