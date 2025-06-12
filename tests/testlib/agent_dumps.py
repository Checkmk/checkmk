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

from pathlib import Path
from typing import Final

from tests.testlib.site import Site
from tests.testlib.utils import logger, run
from tests.testlib.version import CMKVersion, get_min_version


def create_agent_dump_rule(
    site: Site,
    dumps_path: Path | None = None,
    rule_folder: str = "/",
) -> Path:
    """Create a rule to read agent data from a dump path.

    Returns the path of the dumps.

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
    site.openapi.rules.create(
        value=rule_value,
        ruleset_name=ruleset_name,
        folder=rule_folder,
    )
    logger.info('Rule "%s" created!', ruleset_name)

    return dumps_path


def create_snmp_walk_rule(
    site: Site,
    rule_folder: str = "/",
) -> Path:
    """Create a rule to read snmp data from a walk path.

    Returns the path of the walks.

    Args:
        site: The test site.
        rule_folder: The host folder in the site to create the rule.
    """
    walks_path: Final[Path] = site.path("var/check_mk/snmpwalks")  # can not be customized
    ruleset_name = "usewalk_hosts"
    rule_value = True
    logger.info('Creating rule "%s"...', ruleset_name)
    site.openapi.rules.create(
        value=rule_value,
        ruleset_name=ruleset_name,
        folder=rule_folder,
    )
    logger.info('Rule "%s" created!', ruleset_name)

    return walks_path


def create_program_call_rule(
    site: Site,
    program_call: str,
    rule_folder: str = "/",
) -> None:
    """Create a rule to read agent data from a program call.

    Args:
        site: The test site.
        program_call: The program call to return the agent data.
        rule_folder: The host folder in the site to create the rule.
    """
    ruleset_name = "datasource_programs"
    rule_value = program_call
    logger.info('Creating rule "%s"...', ruleset_name)
    site.openapi.rules.create(
        value=rule_value,
        ruleset_name=ruleset_name,
        folder=rule_folder,
    )
    logger.info('Rule "%s" created!', ruleset_name)


def _dumps_up_to_date(dumps_dir: Path, min_version: CMKVersion) -> None:
    """Check if the dumps are up-to-date with the minimum-version branch."""
    dumps = list(dumps_dir.glob("*"))
    if not dumps:
        raise FileNotFoundError("No dumps found!")
    for dump in dumps:
        if str(min_version.semantic) not in dump.name:
            raise ValueError(
                f"Dump '{dump.name}' is outdated! "
                f"Please regenerate it using an agent with version {min_version.semantic}."
            )


def copy_dumps(
    site: Site,
    source_dir: Path,
    target_dir: Path,
    prefix: str = "agent-",
    filename: str | None = None,
) -> None:
    """Copy SNMP/agent dumps from source dir to target dir, ignoring subdirectories.

    Args:
        site: The test site.
        source_dir: The folder to copy the dumps from.
        target_dir: The folder to copy the dumps to.
        prefix: The prefix of the files to copy.
        filename: The specific file name to copy (optional).
    """
    logger.info("Injecting agent-output...")
    target_dir = site.path(target_dir)
    if not site.is_dir(target_dir):
        site.makedirs(target_dir)
    source_path = f"{source_dir.as_posix()}/{(filename if filename else prefix + '*')}"
    assert run(["bash", "-c", f'cp -f {source_path} "{target_dir}"'], sudo=True).returncode == 0


def inject_dumps(site: Site, dumps_dir: Path, check_dumps_up_to_date: bool = True) -> None:
    """Create dump rule and copy agent dumps from dumps_dir to site.

    Args:
        site: The test site.
        dumps_dir: The folder to copy the dumps from.
        check_dumps_up_to_date: Specifies if the dumps should be validated for being up-to-date.
    """
    if check_dumps_up_to_date:
        _dumps_up_to_date(dumps_dir, get_min_version())

    site_dumps_path = create_agent_dump_rule(site)
    copy_dumps(site, dumps_dir, site_dumps_path)
