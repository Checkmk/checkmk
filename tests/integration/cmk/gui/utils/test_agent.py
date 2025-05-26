#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from pytest_mock import MockerFixture

from tests.testlib.site import Site

from cmk.gui.utils import agent


def test_vanilla_agents_filenames(site: Site, mocker: MockerFixture) -> None:
    # we have functions to receive the path to the vanilla agent packages.
    # this test makes sure that those functions always point to existing files.

    # we have a mixed situation here: we use the source code from git, but
    # check against the installed site. so we have to make sure the version
    # matches: we mock the source code to reflect the site version.
    mocker.patch("cmk.gui.utils.agent.cmk_version", site.version.version)
    mocker.patch("cmk.utils.paths.agents_dir", site.root / "share/check_mk/agents")

    assert site.file_exists(agent.packed_agent_path_windows_msi().relative_to(site.root))
    assert site.file_exists(agent.packed_agent_path_linux_deb().relative_to(site.root))
    assert site.file_exists(agent.packed_agent_path_linux_rpm().relative_to(site.root))
