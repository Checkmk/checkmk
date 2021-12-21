#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.utils import agent


def test_vanilla_agents_filenames(site, mocker):
    # we have functions to receive the path to the vanilla agent packages.
    # this test makes sure that those functions always point to existing files.

    # we have a mixed situation here: we use the source code from git, but
    # check against the installed site. so we have to make sure the version
    # matches: we mock the source code to reflect the site version.
    mocker.patch("cmk.gui.utils.agent.cmk_version", site.version.version)

    assert site.file_exists(str(agent.packed_agent_path_windows_msi()))
    assert site.file_exists(str(agent.packed_agent_path_linux_deb()))
    assert site.file_exists(str(agent.packed_agent_path_linux_rpm()))
