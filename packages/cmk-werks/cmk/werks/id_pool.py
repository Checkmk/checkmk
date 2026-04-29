#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from dataclasses import dataclass
from pathlib import Path

from .schemas.werk import LegacyStash, Stash, WerkId


@dataclass(frozen=True, kw_only=True)
class Paths:
    legacy_stash_file: Path
    stash_file: Path
    secret_file: Path

    @property
    def active_stash_file(self) -> Path:
        return self.stash_file if self.secret_file.exists() else self.legacy_stash_file


def make_paths_object(home: Path) -> Paths:
    return Paths(
        legacy_stash_file=home / ".cmk-werk-ids",
        stash_file=home / ".local/cmk-werks/reserved-ids",
        secret_file=home / ".local/cmk-werks/secret",
    )


def load_legacy_stash_from_file(paths: Paths) -> LegacyStash:
    if not paths.legacy_stash_file.exists():
        return LegacyStash()

    content = paths.legacy_stash_file.read_text(encoding="utf-8")
    if not content:
        return LegacyStash()

    if content[0] == "[":
        # we have a legacy file, from cmk project, we need to adapt it:
        return LegacyStash.model_validate({"ids_by_project": {"cmk": ast.literal_eval(content)}})

    return LegacyStash.model_validate_json(content)


def dump_stash_to_file(paths: Paths, stash: LegacyStash | Stash) -> None:
    raw_stash = stash.model_dump_json(by_alias=True)
    match stash:
        case LegacyStash():
            paths.legacy_stash_file.write_text(raw_stash, encoding="utf-8")
        case Stash():
            paths.stash_file.write_text(raw_stash, encoding="utf-8")
        case other:
            raise TypeError(other)


def pick_id_from_stash(stash: LegacyStash | Stash, project: str) -> WerkId:
    match stash:
        case LegacyStash():
            return stash.pick_id(project=project)
        case Stash():
            return stash.pick_id()
        case other:
            raise TypeError(other)


def add_id_to_stash(stash: LegacyStash | Stash, werk_id: WerkId, project: str) -> None:
    match stash:
        case LegacyStash():
            stash.add_id(werk_id, project=project)
        case Stash():
            stash.add_ids([werk_id])
        case other:
            raise TypeError(other)
