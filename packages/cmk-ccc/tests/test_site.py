#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from pathlib import Path

import pytest

from cmk.ccc.site import resource_attributes_from_config


def test_resource_attributes_from_config_not_existing(tmp_path: Path) -> None:
    assert resource_attributes_from_config(tmp_path) == {}


def test_resource_attributes_from_config_read_valid_attributes(tmp_path: Path) -> None:
    attributes_path = tmp_path / "etc" / "omd" / "resource_attributes_from_config.json"
    attributes_path.parent.mkdir(parents=True)
    attributes_path.write_text(json.dumps(attrs := {"key": "value"}))
    assert resource_attributes_from_config(tmp_path) == attrs


def test_resource_attributes_from_config_fail_on_syntax_errors(tmp_path: Path) -> None:
    attributes_path = tmp_path / "etc" / "omd" / "resource_attributes_from_config.json"
    attributes_path.parent.mkdir(parents=True)
    attributes_path.write_text("invalid json")
    with pytest.raises(ValueError):
        resource_attributes_from_config(tmp_path)
