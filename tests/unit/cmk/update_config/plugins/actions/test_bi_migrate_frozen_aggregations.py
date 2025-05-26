#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

from cmk.update_config.plugins.actions import bi_migrate_frozen_aggregations as migration

# Legacy File Structure
# ├── Host heute
# └── origin_hints_default_aggregation
#     └── Host heute

# New File Structure
# └── f6b9d6c7228d50138851a817b88517b2
#     └── 4370a11f4a305d85bf798c88d7cb1e0e


@pytest.fixture
def frozen_aggr_path(tmp_path: Path) -> Path:
    return tmp_path / "frozen_aggregations"


def test_run_migration(frozen_aggr_path: Path) -> None:
    _setup_legacy_file_structure(frozen_aggr_path)

    migration._run_migration(frozen_aggr_path)

    # successfully migrated to new file structure.
    assert (aggr := frozen_aggr_path / "f6b9d6c7228d50138851a817b88517b2").exists()  # aggregation
    assert (branch := aggr / "4370a11f4a305d85bf798c88d7cb1e0e").exists()  # branch

    # content of frozen aggregation branch the same post migration.
    assert branch.read_text() == '{"id": "frozen_default_aggregation_Host heute"}'

    # legacy files cleaned up.
    assert not (frozen_aggr_path / "Host heute").exists()
    assert not (frozen_aggr_path / "origin_hints_default_aggregation").exists()


def _setup_legacy_file_structure(frozen_aggr_path: Path) -> None:
    frozen_aggr_path.mkdir()
    branch_payload = json.dumps({"id": "frozen_default_aggregation_Host heute"})
    (frozen_aggr_path / "Host heute").write_text(branch_payload)
    (hints := frozen_aggr_path / "origin_hints_default_aggregation").mkdir()
    (hints / "Host heute").touch()
