#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from saml2.config import SPConfig

from cmk.utils.paths import saml2_attribute_mappings_dir


@pytest.mark.skip
def test_attribute_mapdir_exists() -> None:
    assert saml2_attribute_mappings_dir.exists()


@pytest.mark.skip
def test_attribute_mapdir_contains_files() -> None:
    assert len(list(saml2_attribute_mappings_dir.glob("*.py"))) > 0


@pytest.mark.skip
def test_attribute_mappings_are_noop() -> None:
    config = SPConfig()
    config.load({"attribute_map_dir": str(saml2_attribute_mappings_dir)})
    assert config.attribute_converters

    converter = config.attribute_converters[0]
    assert not converter.name_format
    assert not converter._to
    assert not converter._fro
