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

from tests.testlib.site import Site
from tests.testlib.utils import logger, run
from tests.testlib.version import CMKVersion, get_min_version


def create_agent_dump_rule(
    site: Site,
    dumps_path: Path | None = None,
    rule_folder: str = "/",
) -> tuple[str, Path]:
    """Create a rule to read agent data from a dump path.

    Returns the rule ID and the path of the dumps.

    Args:
        site: The test site.
        dumps_path: The path where the dumps are stored in the site.
        rule_folder: The host folder in the site to create the rule.
    """
    dumps_path = dumps_path or site.path("var/check_mk/dumps")
    ruleset_name = "datasource_programs"
    rule_value = f'cat "{dumps_path.as_posix()}/$HOSTNAME$"'
    if site.is_dir(dumps_path):
        logger.info('Creating folder "%s"...', dumps_path)
        _ = site.run(["mkdir", "-p", dumps_path.as_posix()])
    logger.info('Creating rule "%s"...', ruleset_name)
    rule_id = site.openapi.rules.create(
        value=rule_value,
        ruleset_name=ruleset_name,
        folder=rule_folder,
    )
    return rule_id, dumps_path


def copy_dumps(
    site: Site,
    source_dir: Path,
    target_dir: Path,
    prefix: str = "agent-",
    source_filename: str | None = None,
    target_filenames: list[str] | None = None,
) -> None:
    """Copy SNMP/agent dumps from source dir to target dir, ignoring subdirectories.

    Args:
        site: The test site.
        source_dir: The folder to copy the dumps from.
        target_dir: The folder to copy the dumps to.
        prefix: The prefix of the files to copy.
        source_filename: The specific source file name to copy (optional).
        target_filenames: The specific target file names to copy the source_filename to (optional).
    """
    logger.info("Injecting agent-output...")
    target_dir = site.path(target_dir)
    if not site.is_dir(target_dir):
        site.makedirs(target_dir)
    source_path = f"{source_dir}/{(source_filename if source_filename else prefix + '*')}"
    if source_filename and target_filenames:
        target_paths = list((target_dir / filename) for filename in target_filenames)
    else:
        target_paths = [target_dir]
    for target_path in target_paths:
        run(["bash", "-c", f'cp -f {source_path} "{target_path}"'], sudo=True)


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
