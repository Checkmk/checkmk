#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import json
import marshal

import pytest
from bs4 import BeautifulSoup

import cmk.utils.paths
from cmk.ccc.version import Edition
from cmk.gui.config import Config
from cmk.gui.http import request
from cmk.gui.pages import PageContext
from cmk.gui.permissions import all_permissions
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.session import session
from cmk.gui.utils.transaction_manager import transactions
from cmk.profiling.gui._store import ProfileStore
from cmk.profiling.gui.pages import ModePerformanceProfiles


@pytest.mark.usefixtures("request_context")
def test_page_offers_deleting_a_stored_profile(test_edition: Edition, config: Config) -> None:
    profile_id = ProfileStore(cmk.utils.paths.profiles_dir).save_uploaded(
        marshal.dumps({("/tmp/x.py", 1, "f"): (1, 1, 0.01, 0.02, {})}), "upload.profile"
    )
    config = dataclasses.replace(config, profiling_options={"enabled": True})

    with output_funnel.plugged():
        ModePerformanceProfiles(
            test_edition,
            PageContext(
                config=config,
                request=request,
                transactions=transactions,
                session=session,
                user_permissions=UserPermissions.from_config(config, all_permissions()),
            ),
        ).page(config)
        rendered = "".join(output_funnel.drain())

    app = BeautifulSoup(rendered, "html.parser").find("cmk-profiling-profiles-list")
    assert app is not None
    (profile,) = json.loads(str(app["data"]))["profiles"]
    assert profile["profile_id"] == profile_id
    assert profile["delete_action"]["action"] == "confirm_link"
    assert f"_delete={profile_id}" in profile["delete_action"]["arguments"]["url"]
