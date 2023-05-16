#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging

from . import constants
from .conftest import run_cmd

LOGGER = logging.getLogger(__name__)


def get_section_header(section: str) -> str:
    """Parse a section and return the section header."""
    return section.split("<<<", 1)[-1].split("\n", 1)[0].split(">>>", 1)[0]


def get_section_name(section: str) -> str:
    """Parse a section header and return the section name."""
    return get_section_header(section).split(":", 1)[0]


def dump_section_output() -> None:
    """Dump the raw section output."""
    agent_output = f"\n{run_cmd(['check_mk_agent'])}"
    check_sections = {
        get_section_name(section): f"<<<{section}\n"
        for section in agent_output.split("\n<<<")
        if section.strip()
    }
    for section_name in sorted(check_sections):
        if len(constants.SECTION_NAMES) > 0 and section_name not in constants.SECTION_NAMES:
            continue
        section_output = check_sections[section_name]
        LOGGER.debug(section_output)
        raw_file_path = f"{constants.AGENT_OUTPUT_DIR}/{section_name}"
        with open(raw_file_path, "w", encoding="utf-8") as raw_file:
            raw_file.write(section_output)
