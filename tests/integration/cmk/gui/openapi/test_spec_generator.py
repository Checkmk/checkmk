#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import subprocess

from tests.testlib.site import Site


def test_initial_api_spec_computation_was_done(site: Site) -> None:
    assert site.file_exists("var/check_mk/rest_api/spec/doc.spec")
    assert site.file_exists("var/check_mk/rest_api/spec/swagger-ui.spec")


def test_compute_api_spec(site: Site) -> None:
    site.delete_file("var/check_mk/rest_api/spec/doc.spec")
    site.delete_file("var/check_mk/rest_api/spec/swagger-ui.spec")

    output = site.check_output(["cmk-compute-api-spec"], stderr=subprocess.STDOUT)

    assert "warnings.warn" not in output, output

    assert site.file_exists("var/check_mk/rest_api/spec/doc.spec")
    assert site.file_exists("var/check_mk/rest_api/spec/swagger-ui.spec")

    spec = ast.literal_eval(site.read_file("var/check_mk/rest_api/spec/doc.spec"))
    assert len(spec["paths"]) > 100  # Some watermark we have a decent amount of endpoints
