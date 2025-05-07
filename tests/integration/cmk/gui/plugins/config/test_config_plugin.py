#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib.site import Site


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/lib/python3/cmk/gui/plugins/config"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_file(path, 'x = "yo"\n')
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_config_plugin(site: Site) -> None:
    assert site.python_helper("helper_test_load_config_plugin.py").check_output().rstrip() == "yo"


@pytest.fixture()
def legacy_plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/share/check_mk/web/plugins/config"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_file(path, 'x = "legacy"\n')
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("legacy_plugin_path")
def test_load_legacy_config_plugin(site: Site) -> None:
    assert (
        site.python_helper("helper_test_load_config_plugin.py").check_output().rstrip() == "legacy"
    )
