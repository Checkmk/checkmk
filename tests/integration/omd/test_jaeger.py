#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

from tests.testlib.pytest_helpers.marks import skip_if_saas_edition
from tests.testlib.site import Site


@skip_if_saas_edition
def test_jaeger_exists(site: Site) -> None:
    assert Path(site.root, "bin", "jaeger").exists()


@skip_if_saas_edition
def test_jaeger_executable(site: Site) -> None:
    assert "Jaeger all-in-one distribution" in site.check_output(["jaeger", "--help"])
