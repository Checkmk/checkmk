#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.gui.watolib.groups_io import load_contact_group_information
from cmk.gui.watolib.sample_config import init_wato_datastructures, SampleConfigGeneratorGroups
from cmk.utils.paths import omd_root


def test_init_wato_data_structures(request_context: None) -> None:
    init_wato_datastructures()
    assert Path(omd_root, "etc/check_mk/conf.d/wato/rules.mk").exists()
    assert Path(omd_root, "etc/check_mk/multisite.d/wato/tags.mk").exists()
    assert Path(omd_root, "etc/check_mk/conf.d/wato/global.mk").exists()
    assert not Path(omd_root, "var/check_mk/web/automation").exists()
    assert Path(omd_root, "var/check_mk/web/agent_registration").exists()
    assert Path(omd_root, "var/check_mk/web/agent_registration/automation.secret").exists()


@pytest.mark.usefixtures("request_context")
def test_sample_config_gen_groups() -> None:
    SampleConfigGeneratorGroups().generate()
    assert load_contact_group_information() == {
        "all": {
            "alias": "Everything",
        },
    }
