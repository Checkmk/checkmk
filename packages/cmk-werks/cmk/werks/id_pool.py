#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from pathlib import Path

from .schemas.werk import Stash


def load_stash_from_file(werk_ids_path: Path) -> Stash:
    if not werk_ids_path.exists():
        return Stash()
    content = werk_ids_path.read_text(encoding="utf-8")
    if not content:
        return Stash()
    if content[0] == "[":
        # we have a legacy file, from cmk project, we need to adapt it:
        return Stash.model_validate({"ids_by_project": {"cmk": ast.literal_eval(content)}})
    return Stash.model_validate_json(content)


def dump_stash_to_file(werk_ids_path: Path, stash: Stash) -> None:
    werk_ids_path.write_text(stash.model_dump_json(by_alias=True), encoding="utf-8")
