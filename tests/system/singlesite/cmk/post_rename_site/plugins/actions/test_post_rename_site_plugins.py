#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.testlib.site import Site

from . import prs_test_plugin

POST_RENAME_SITE_PLUGINS_PATH = "local/lib/python3/cmk/plugins/mytest/post_rename_site"


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    site.makedirs(POST_RENAME_SITE_PLUGINS_PATH)
    path = f"{POST_RENAME_SITE_PLUGINS_PATH}/test_plugin.py"
    site.write_file(path, Path(prs_test_plugin.__file__).read_text())
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_post_rename_site_plugin(site: Site) -> None:
    assert site.python_helper("helper_verify_rename_action.py").check_output().rstrip() == "True"
