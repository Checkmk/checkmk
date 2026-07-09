#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui.sidebar import CustomSnapins
from cmk.gui.utils.roles import UserPermissions


def _write_user_custom_snapins(user_id: UserId) -> None:
    profile_dir = cmk.utils.paths.profile_dir / user_id
    profile_dir.mkdir(parents=True, exist_ok=True)
    store.save_object_to_file(
        profile_dir / "user_custom_snapins.mk",
        {
            "my_tactical_overview": {
                "title": "My tactical overview",
                "description": "",
                "public": False,
                "custom_snapin": (
                    "tactical_overview",
                    {
                        "rows": [
                            {
                                "title": "Hosts",
                                "query": ("hosts", {}),
                            }
                        ],
                        "show_stale": True,
                        "show_failed_notifications": True,
                        "show_sites_not_connected": True,
                    },
                ),
            },
            # Created with Checkmk <= 2.0, where the host matrix snap-in was customizable.
            # Ignored since 2.1, but must not crash the GUI.
            "my_host_matrix": {
                "title": "My host matrix",
                "description": "",
                "public": False,
                "custom_snapin": (
                    "hostmatrix",
                    {"context": {"wato_folder": {"wato_folder_path": "/os/windows"}}},
                ),
            },
        },
    )


@pytest.mark.usefixtures("request_context")
def test_custom_snapins_load_skips_legacy_entries(with_user: tuple[UserId, str]) -> None:
    user_id, _password = with_user
    _write_user_custom_snapins(user_id)

    instances = CustomSnapins.load(UserPermissions({}, {}, {}, []))

    assert [instance.name() for instance in instances.instances()] == ["my_tactical_overview"]
