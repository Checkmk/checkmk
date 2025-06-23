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
import re
import subprocess
from pathlib import Path
from typing import Final

import pytest

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


def create_snmp_walk_rule(
    site: Site,
    rule_folder: str = "/",
) -> tuple[str, Path]:
    """Create a rule to read snmp data from a walk path.

    Returns the rule ID and the path of the walks.

    Args:
        site: The test site.
        rule_folder: The host folder in the site to create the rule.
    """
    walks_path: Final[Path] = site.path("var/check_mk/snmpwalks")  # can not be customized
    ruleset_name = "usewalk_hosts"
    rule_value = True
    logger.info('Creating rule "%s"...', ruleset_name)
    rule_id = site.openapi.rules.create(
        value=rule_value,
        ruleset_name=ruleset_name,
        folder=rule_folder,
    )
    return rule_id, walks_path


def create_program_call_rule(
    site: Site,
    program_call: str,
    rule_folder: str = "/",
) -> str:
    """Create a rule to read agent data from a program call.

    Returns the rule ID.

    Args:
        site: The test site.
        program_call: The program call to return the agent data.
        rule_folder: The host folder in the site to create the rule.
    """
    ruleset_name = "datasource_programs"
    rule_value = program_call
    logger.info('Creating rule "%s"...', ruleset_name)
    rule_id = site.openapi.rules.create(
        value=rule_value,
        ruleset_name=ruleset_name,
        folder=rule_folder,
    )
    return rule_id


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


def inject_dumps(site: Site, dumps_dir: Path, check_dumps_up_to_date: bool = True) -> str:
    """Create dump rule and copy agent dumps from dumps_dir to site.

    Returns the rule_id of the agent dump rule.

    Args:
        site: The test site.
        dumps_dir: The folder to copy the dumps from.
        check_dumps_up_to_date: Specifies if the dumps should be validated for being up-to-date.
    """
    if check_dumps_up_to_date:
        _dumps_up_to_date(dumps_dir, get_min_version())

    rule_id, site_dumps_path = create_agent_dump_rule(site)
    copy_dumps(site, dumps_dir, site_dumps_path)

    return rule_id


def read_disk_dump(host_name: str, dump_dir: Path) -> str:
    """Return the content of an agent dump from the dumps' folder."""
    dump_file_path = f"{dump_dir}/{host_name}"
    with open(dump_file_path, encoding="utf-8") as dump_file:
        return dump_file.read()


def read_cmk_dump(host_name: str, site: Site, dump_type: str) -> str:
    """Return the current agent or snmp dump via cmk."""
    args = ["cmk", "--snmptranslate" if dump_type == "snmp" else "-d", host_name]
    cmk_dump, _ = site.execute(
        args,
        stdout=subprocess.PIPE,
        encoding="utf-8",
    ).communicate()
    if dump_type == "snmp":
        cmk_dump = "\n".join([_.split("-->")[0].strip() for _ in str(cmk_dump).splitlines()])

    return cmk_dump


def read_piggyback_hosts_from_dump(dump: str) -> set[str]:
    """Read piggyback hosts from the agent dump.

    A piggyback host is defined by the pattern '<<<<host_name>>>>' within the agent dump.
    """
    piggyback_hosts: set[str] = set()
    pattern = r"<<<<(.*?)>>>>"
    matches = re.findall(pattern, dump)
    piggyback_hosts.update(matches)
    piggyback_hosts.discard("")  # '<<<<>>>>' pattern will match an empty string
    return piggyback_hosts


def _list_unskipped_files(
    directory: Path, pattern: str | None = None, skipped_files: list[str] | None = None
) -> list[str]:
    if not directory.exists():
        # need to skip here to abort the collection and return RC=5: "no tests collected"
        pytest.skip(f'Folder "{directory}" not found; exiting!', allow_module_level=True)
    return [
        filename
        for filename in os.listdir(directory)
        if pattern is None
        or re.match(pattern, filename)
        and (not filename.startswith(".") and filename not in (skipped_files or []))
        and os.path.isfile(os.path.join(directory, filename))
    ]


def get_dump_names(
    dump_dir: Path,
    skipped_dumps: list[str] | None = None,
) -> list[str]:
    """Return a list of agent dumps in a dump dir."""
    return _list_unskipped_files(dump_dir, r"^agent-\d+\.\d+\.\d+\w*\d*-", skipped_dumps)


def get_walk_names(
    walk_dir: Path,
    skipped_walks: list[str] | None = None,
) -> list[str]:
    """Return a list of snmp walks in a walk dir."""
    return _list_unskipped_files(walk_dir, r"^snmp-", skipped_walks)


def get_dump_and_walk_names(
    directory: Path,
    skipped_files: list[str] | None = None,
) -> list[str]:
    """Return a list of agent dumps and snmp walks in a directory."""
    return get_dump_names(directory, skipped_files) + get_walk_names(directory, skipped_files)
