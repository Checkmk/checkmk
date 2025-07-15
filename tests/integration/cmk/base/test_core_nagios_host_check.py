#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import importlib
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest

from tests.integration.linux_test_host import create_linux_test_host

from tests.testlib.site import Site

from cmk.ccc.hostaddress import HostName


@contextmanager
def _set_precompile(site: Site) -> Iterator[None]:
    global_mk = "etc/check_mk/conf.d/wato/global.mk"
    delay_str = "\ndelay_precompile = True\n"
    site.write_file(global_mk, f"{site.read_file(global_mk)}{delay_str}")
    try:
        yield None
    finally:
        site.write_file(global_mk, site.read_file(global_mk).replace(delay_str, ""))


@contextmanager
def _stopped(site: Site) -> Iterator[None]:
    site.stop()
    try:
        yield None
    finally:
        # teardown will fail if the site is not started again ¯\_(ツ)_/¯
        site.start()


def test_compile_delayed_host_check(request: pytest.FixtureRequest, site: Site) -> None:
    if site.get_config("CORE") != "nagios":
        pytest.skip("This test is only for Nagios")
    with _set_precompile(site):
        _test_compile_delayed_host_check(request, site)


def _test_compile_delayed_host_check(request: pytest.FixtureRequest, site: Site) -> None:
    #
    # Setup
    #
    hostname = HostName("localhost")
    compiled_file = Path(f"var/check_mk/core/helper_config/latest/host_checks/{hostname}")
    source_file = Path(f"{compiled_file}.py")

    create_linux_test_host(request, site, hostname)
    assert not site.file_exists(compiled_file)
    assert not site.file_exists(source_file)

    site.check_output(["cmk", "-II", hostname])
    site.check_output(["cmk", "-R"])

    with _stopped(site):  # don't interfere...
        #
        # Phase 1: No compilation yet.
        #
        site.check_output(["cmk", "-U"])
        # Check that the files have been created...
        assert site.file_exists(compiled_file)
        assert site.file_exists(source_file)
        # but the source has *not yet* been compiled, but the compiled file is a symlink to the source:
        assert site.resolve_path(compiled_file) == site.resolve_path(source_file)

        #
        # Phase 2: Compilation.
        #
        site.check_output(["python3", "-P", f"{compiled_file}"])
        # *Now* it has been compiled:
        assert site.resolve_path(compiled_file) != site.resolve_path(source_file)
        assert site.read_file(compiled_file, encoding=None).startswith(importlib.util.MAGIC_NUMBER)
