# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Check that the hand-maintained dependency manifest still points at existing files."""

from pathlib import Path

import pytest
import yaml
from list_dependencies import CustomManifest, CustomManifestEntry

_MANIFEST = CustomManifest.model_validate(
    yaml.safe_load((Path(__file__).parent / "manual_dependency_manifest.yml").read_text())
)


@pytest.mark.parametrize(
    "entry",
    [pytest.param(entry, id=entry.purl.purl_str()) for entry in _MANIFEST.dependencies],
)
def test_declared_path_exists(entry: CustomManifestEntry) -> None:
    if entry.path is None:
        pytest.skip("no path declared")
    assert Path(entry.path).is_file(), (
        f"Declared path {entry.path} for {entry.purl.purl_str()} does not exist"
    )
