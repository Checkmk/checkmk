#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from tests.testlib.site import Site

test_plugin_code = """
from cmk.post_rename_site.registry import rename_action_registry, RenameAction

def test(old_site_id, new_site_id):
    pass

rename_action_registry.register(
    RenameAction(
        name="test",
        title="test",
        sort_index=20,
        handler=test,
    )
)
"""


@pytest.fixture()
def plugin_path(site: Site) -> Iterator[str]:
    base_dir = "local/lib/python3/cmk/post_rename_site/plugins/actions"
    site.makedirs(base_dir)
    path = f"{base_dir}/test_plugin.py"
    site.write_file(path, test_plugin_code)
    yield path
    site.delete_file(path)


@pytest.mark.usefixtures("plugin_path")
def test_load_post_rename_site_plugin(site: Site) -> None:
    assert site.python_helper("helper_verify_rename_action.py").check_output().rstrip() == "True"
