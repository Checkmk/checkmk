#!/usr/bin/env python3
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from contextlib import suppress
from pathlib import Path

from ._parts import PackagePart


def all_rule_pack_files() -> set[Path]:
    with suppress(FileNotFoundError):
        return {
            f.relative_to(PackagePart.EC_RULE_PACKS.path)
            for f in PackagePart.EC_RULE_PACKS.path.iterdir()
        }
    return set()
