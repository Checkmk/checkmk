#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import subprocess

from tests.testlib.site import Site


def test_compute_api_spec(site: Site) -> None:
    site.delete_file("var/check_mk/rest_api/spec/doc.spec")
    site.delete_file("var/check_mk/rest_api/spec/swagger-ui.spec")

    p = site.execute(["cmk-compute-api-spec"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert p.wait() == 0

    output = p.communicate()[0]
    assert "warnings.warn" not in output, output

    assert site.file_exists("var/check_mk/rest_api/spec/doc.spec")
    assert site.file_exists("var/check_mk/rest_api/spec/swagger-ui.spec")

    spec = ast.literal_eval(site.read_file("var/check_mk/rest_api/spec/doc.spec"))
    assert len(spec["paths"]) > 100  # Some watermark we have a decent amount of endpoints
