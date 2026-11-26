#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What an anonymized configuration says about the site it was taken from.

The anonymized files alone do not tell which edition and version wrote them.
Whoever loads the dump into another site (e.g. the system tests using the
sample configs) needs to know, so it is recorded next to ``etc/`` and ``var/``.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from cmk.ccc.version import Edition

METADATA_FILENAME = "metadata.json"


@dataclass(frozen=True)
class Metadata:
    edition: Edition
    version: str


def write_metadata(target_dir: Path, metadata: Metadata) -> Path:
    """Write the metadata file into `target_dir` and return its path."""
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / METADATA_FILENAME
    path.write_text(
        json.dumps({"edition": metadata.edition.long, "version": metadata.version}, indent=4) + "\n"
    )
    return path
