#!/usr/bin/env python3
# Copyright (C) 2023 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from saml2.config import SPConfig

from cmk.utils.paths import (
    saml2_attribute_mappings_dir,
    saml2_builtin_cert_dir,
    saml2_builtin_signature_cert_dir,
    saml2_cert_dir,
    saml2_custom_cert_dir,
)


def test_attribute_mapdir_exists() -> None:
    assert saml2_attribute_mappings_dir.exists()


def test_attribute_mapdir_contains_files() -> None:
    assert len(list(saml2_attribute_mappings_dir.glob("*.py"))) > 0


def test_attribute_mappings_are_noop() -> None:
    config = SPConfig()
    config.load({"attribute_map_dir": str(saml2_attribute_mappings_dir)})
    assert config.attribute_converters

    converter = config.attribute_converters[0]
    assert not converter.name_format
    assert not converter._to
    assert not converter._fro


def _assert_mode(dir_: Path, mode: int) -> None:
    __tracebackhide__ = True  # pylint: disable=unused-variable
    assert dir_.stat().st_mode & 0o777 == mode


@pytest.mark.parametrize(
    "cert_dir",
    [
        pytest.param(saml2_cert_dir, id="Top level certificates dir"),
        pytest.param(saml2_builtin_cert_dir, id="Dir for builtin certificates"),
        pytest.param(saml2_custom_cert_dir, id="Dir for custom certificates"),
        pytest.param(saml2_builtin_signature_cert_dir, id="Dir for builtin signature certificate"),
    ],
)
def test_cert_dirs_exist(cert_dir: Path) -> None:
    assert cert_dir.exists()
    _assert_mode(cert_dir, 0o700)
