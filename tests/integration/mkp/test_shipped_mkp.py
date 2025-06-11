#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import subprocess
from collections.abc import Iterable, Iterator
from contextlib import contextmanager

import pytest

from tests.testlib.site import Site

from tests.extension_compatibility.test_extension_compatibility import ImportErrors

from .lib import disable_extension, enable_extension

MKP_TO_TEST: Iterable[str] = ()


@pytest.mark.parametrize("package_name", MKP_TO_TEST)
def test_enabling_shipped_mkp(site: Site, package_name: str) -> None:
    """
    Test if the shipped MKPs are present and can be activated in a site

    The MKP has to be present as a shared MKP, not a local one.
    If it would show up in local it would mean someone has manually copied it.
    """
    process = site.execute(
        ["mkp", "show-all", "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()

    assert process.returncode == 0
    assert stderr == ""

    mkp_listing = json.loads(stdout)

    shipped_mkps = mkp_listing["shipped"]
    assert shipped_mkps, "No MKPs shipped - but we expect at least one"

    mkp_names = {mkp["name"] for mkp in shipped_mkps}
    assert package_name in mkp_names

    with _temporary_enable_extension(site, package_name):
        encountered_errors = ImportErrors.collect_from_site(site)

    assert not encountered_errors.base_errors
    assert not encountered_errors.gui_errors


@contextmanager
def _temporary_enable_extension(site: Site, name: str) -> Iterator[None]:
    try:
        enable_extension(site, name)
        yield
    finally:
        disable_extension(site, name)
