#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions & objects to parse werk contents."""

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

from scripts.gerrit_api.client import ChangeDetails, GerritClient


class WerkImpact(StrEnum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    ALL = "all"

    @staticmethod
    def werk_level_to_impact(level: int) -> "WerkImpact":
        mapping = {1: WerkImpact.LOW, 2: WerkImpact.NORMAL, 3: WerkImpact.HIGH}
        try:
            return mapping[level]
        except KeyError as exc:
            exc.add_note("Expected Werk levels in range [1,3] only!")
            raise exc


@dataclass
class WerkDetails:
    ID: int
    SUMMARY: str
    VERSION: str
    IMPACT: WerkImpact = WerkImpact.NORMAL
    PRIO: WerkImpact = WerkImpact.NORMAL


class WerksParser:
    """Parse contents of a Werk file and return QA-centric details.

    NOTE - this works for 'werk v2' syntax!
    """

    DELIMITER: Final = "|"

    def __init__(self, file_path: str, raw_werk: str) -> None:
        super().__init__()
        self._raw = raw_werk
        self._id = int(Path(file_path).stem)

    def _details(self) -> None:
        """Parse the contents of a werk and store the information."""
        for line in self._raw.split("\n"):
            if line.startswith("#"):
                self._summary = line.split("#")[-1].strip()
            elif WerksParser.DELIMITER in line:
                if "version" in line:
                    self._version = line.split(WerksParser.DELIMITER)[-1].strip()
                if "level" in line:
                    self._level = int(line.split(WerksParser.DELIMITER)[-1].strip())
                if "compatible" in line:
                    self._compatible = line.split(WerksParser.DELIMITER)[-1].strip()
        self._impact = self._get_impact()

    def _get_impact(self) -> WerkImpact:
        """Decide the impact of a werk on the client.

        Incompatible werks are considered as HIGH impact, irrespective of the type of change.
        Impact of compatible werks is based on the type of change:
        + Trivial   - LOW impact
        + Prominent - NORMAL impact
        + Major     - HIGH impact
        """
        if self._compatible.lower() == "no":
            return WerkImpact.HIGH
        return WerkImpact.werk_level_to_impact(self._level)

    @property
    def details(self) -> WerkDetails:
        """Return QA-centric details corresponding to the werk under consideration."""
        self._details()
        return WerkDetails(
            ID=self._id,
            SUMMARY=self._summary,
            VERSION=self._version,
            IMPACT=self._impact,
        )


def werk_details(client: GerritClient, change: ChangeDetails) -> WerkDetails:
    """Fetch the QA-centric details of a Werk corresponding to a gerrit change.

    Raises:
        FileNotFoundError: the werk is not found within the change.
    """

    def _werk_file(client: GerritClient, change: ChangeDetails) -> str:
        """Search for files present within a changes and return the file corresponding to a Werk."""
        for file in client.changes_api.get_files(change):
            if re.findall(r"\d{4,6}.md$", file):
                return file
        raise FileNotFoundError(
            f"Change\n'{change.change_id}:{change.subject}'\n, doesn't include a Werk!"
        )

    raw = client.changes_api.get_content_from_file(change, file := _werk_file(client, change))
    return WerksParser(raw_werk=raw, file_path=file).details
