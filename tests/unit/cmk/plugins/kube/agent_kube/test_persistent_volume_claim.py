#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.kube.agent_handlers.persistent_volume_claim_handler import create_pvc_sections


def test_create_pvc_sections_with_non_existing_api_pvcs():
    sections = create_pvc_sections(
        piggyback_name="test",
        attached_pvc_names=["pvc_claim"],
        api_pvcs={},
        api_pvs={},
        attached_volumes={},
    )
    assert len(list(sections)) == 0
