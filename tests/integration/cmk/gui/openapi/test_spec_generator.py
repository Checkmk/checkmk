#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from tests.testlib.site import Site


def test_api_spec_shipped(site: Site) -> None:
    assert site.file_exists("share/doc/check_mk/rest-api/spec/doc.spec")
    assert site.file_exists("share/doc/check_mk/rest-api/spec/swagger-ui.spec")
