#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""helper functions to manage agent dumps during testing

This module provides helper functions to:
- Verify that the dump files in a given directory are consistent with the minimum required version,
- Inject these dumps into a test site by creating the necessary directories, copying the files,
    and setting up a corresponding rule to simulate agent output.
"""

import os
from pathlib import Path

from tests.testlib.common.utils import logger, run
from tests.testlib.site import Site
from tests.testlib.version import CMKVersion, get_min_version


def _dumps_up_to_date(dumps_dir: Path, min_version: CMKVersion) -> None:
    """Check if the dumps are up-to-date with the minimum-version branch."""
    dumps = list(dumps_dir.glob("*"))
    min_version_str = min_version.version
    min_version_branch = min_version_str[: min_version_str.find("p")]
    if not dumps:
        raise FileNotFoundError("No dumps found!")
    for dump in dumps:
        if str(min_version_branch) not in dump.name:
            raise ValueError(
                f"Dump '{dump.name}' is outdated! "
                f"Please regenerate it using an agent with version {min_version_branch}."
            )


def inject_dumps(site: Site, dumps_dir: Path) -> None:
    _dumps_up_to_date(dumps_dir, get_min_version())

    # create dump folder in the test site
    site_dumps_path = site.path("var/check_mk/dumps")
    logger.info('Creating folder "%s"...', site_dumps_path)
    _ = site.run(["mkdir", "-p", site_dumps_path.as_posix()])

    logger.info("Injecting agent-output...")

    for dump_name in list(os.listdir(dumps_dir)):
        assert (
            run(
                [
                    "cp",
                    "-f",
                    f"{dumps_dir}/{dump_name}",
                    f"{site_dumps_path}/{dump_name}",
                ],
                sudo=True,
            ).returncode
            == 0
        )

    ruleset_name = "datasource_programs"
    logger.info('Creating rule "%s"...', ruleset_name)
    site.openapi.rules.create(ruleset_name=ruleset_name, value=f"cat {site_dumps_path}/*")
    logger.info('Rule "%s" created!', ruleset_name)
