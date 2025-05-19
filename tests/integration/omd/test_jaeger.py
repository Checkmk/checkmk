#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from tests.testlib.site import Site


@pytest.mark.skip_if_edition("saas")
def test_jaeger_exists(site: Site) -> None:
    assert (site.root / "bin" / "jaeger").exists()


@pytest.mark.skip_if_edition("saas")
def test_jaeger_executable(site: Site) -> None:
    assert "Jaeger backend v2" in site.check_output(["jaeger", "--help"])
