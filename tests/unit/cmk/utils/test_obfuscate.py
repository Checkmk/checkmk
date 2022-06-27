#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final

import pytest

import cmk.utils.paths
from cmk.utils.obfuscate import deobfuscate_file, obfuscate_file

_text: Final = b"the text\n"


@pytest.fixture(name="to_obfuscate")
def data_file() -> Path:
    file_path = Path(cmk.utils.paths.tmp_dir) / "data.raw"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("wb") as f:
        f.write(_text)
    return file_path


@pytest.fixture(name="exec_obfuscate")
def obfuscate(to_obfuscate: Path) -> Path:
    file_out = to_obfuscate.parent / "data.obf"
    obfuscate_file(to_obfuscate, file_out=file_out)
    return file_out


@pytest.fixture(name="exec_deobfuscate")
def deobfuscate(exec_obfuscate: Path) -> Path:
    file_out = exec_obfuscate.parent / "data.end"
    deobfuscate_file(exec_obfuscate, file_out=file_out)
    return file_out


def test_value_encrypter_transparent(exec_deobfuscate: Path) -> None:
    assert exec_deobfuscate.read_bytes() == _text
