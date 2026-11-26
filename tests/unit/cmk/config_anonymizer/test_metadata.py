#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""An anonymized configuration records the edition and version of its source site."""

import json
from pathlib import Path

from cmk.ccc.version import Edition
from cmk.config_anonymizer.metadata import Metadata, write_metadata


def test_metadata_file_names_the_edition_and_version_of_the_source_site(tmp_path: Path) -> None:
    path = write_metadata(tmp_path, Metadata(edition=Edition.ULTIMATEMT, version="3.0.0b1"))

    assert path == tmp_path / "metadata.json"
    assert json.loads(path.read_text()) == {"edition": "ultimatemt", "version": "3.0.0b1"}


def test_metadata_file_is_written_into_a_target_directory_that_does_not_exist_yet(
    tmp_path: Path,
) -> None:
    target_dir = tmp_path / "anonymized" / "anon1"

    write_metadata(target_dir, Metadata(edition=Edition.COMMUNITY, version="3.0.0b1"))

    assert (target_dir / "metadata.json").is_file()
