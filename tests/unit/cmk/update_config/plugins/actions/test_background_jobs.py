#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import logging
import os
from pathlib import Path

import pytest

from cmk.update_config.plugins.actions.background_jobs import UpdateBackgroundJobs
from tests.unit.cmk.gui.test_background_job import job_base_dir  # noqa: F401


@pytest.mark.parametrize(
    ["host_name_list", "host_hash_list", "migrated_host_names"],
    [
        pytest.param(
            [
                "host",
                "horst",
                "hans",
                "wurst-72befc4a7ce090cc58d0a95e7b5f7f7845168a68210f23aa2b763c51403b10c1",
                "hannes-host",
                "veryverylonghanswursthost",
            ],
            [
                "host-4740ae6347b0172c01254ff55bae5aff5199f4446e7f6d643d40185b3f475145",
                "horst-edab786c5277a54f468f5d433ce0ede9c6bfdd5e2248b28421e62b2f36a3a202",
                "hans-6428a8fbbb0e120528bb604a66787102280e1b5e26db76633ce37c8a4526e445",
                "hannes-host-3344d27c3b407564e4b45a8f5d3dc5b2dc2a1d518ef97b2a864ce871bd29f808",
                "veryverylonghanswurs-5e920124c8ad9b5f81cf2029d800d20227af9c1402250a2ad403fac6a49dca7d",
            ],
            [
                "service_discovery-wurst-72befc4a7ce090cc58d0a95e7b5f7f7845168a68210f23aa2b763c51403b10c1",
            ],
            id="Builtin tags without negate",
        ),
    ],
)
def test_background_jobs(
    host_name_list: list[str],
    host_hash_list: list[str],
    migrated_host_names: list[str],
    job_base_dir: Path,  # noqa: F811
) -> None:
    with open(
        os.path.join(job_base_dir, ".migrated_service_discovery_directories.json"), "w"
    ) as migrated_file:
        json.dump(migrated_host_names, migrated_file)

    job_name = "service_discovery"
    for host in host_name_list:
        background_job_path = os.path.join(job_base_dir, f"{job_name}-{host}")
        os.makedirs(background_job_path, exist_ok=True)

    UpdateBackgroundJobs(
        name="background_jobs",
        title="Update background jobs",
        sort_index=41,
    )(logging.getLogger())

    for hash_ in host_hash_list:
        new_background_job_path = os.path.join(job_base_dir, f"{job_name}-{hash_}")
        assert os.path.exists(new_background_job_path)
