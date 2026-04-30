#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import sys
import traceback
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import requests

from .in_out_elements import bail_out
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


def load_stash_from_file(paths: Paths) -> LegacyStash | Stash:
    if paths.secret_file.exists():
        return (
            Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8"))
            if paths.stash_file.exists()
            else Stash()
        )
    return load_legacy_stash_from_file(paths)


def dump_stash_to_file(paths: Paths, stash: LegacyStash | Stash) -> None:
    raw_stash = stash.model_dump_json(by_alias=True)
    match stash:
        case LegacyStash():
            paths.legacy_stash_file.write_text(raw_stash, encoding="utf-8")
        case Stash():
            paths.stash_file.write_text(raw_stash, encoding="utf-8")
        case other:
            raise TypeError(other)


class WerkIDsClient:
    URL: Final = "https://werk-ids.lan.checkmk.net"

    def reserve_werk_ids(self, secret_file_path: Path, local_werk_ids_count: int) -> Sequence[int]:
        secret = secret_file_path.read_text(encoding="utf-8").strip()
        try:
            response = requests.post(
                f"{self.URL}/reserve",
                verify=True,
                headers={"Authorization": f"Bearer {secret}"},
                json={"local_werk_ids_count": local_werk_ids_count},
                timeout=10,
            )
        except requests.exceptions.RequestException:
            traceback.print_exc(file=sys.stderr)
            sys.stderr.write(f"Could not connect to the werk IDs server {self.URL}\n")
            return []

        if response.status_code == 200:
            return [int(i) for i in response.json()["reserved_werk_ids"]]

        sys.stderr.write(
            f"Could not reserve werk IDs (Status code: {response.status_code}, server: {self.URL}): {response.text}\n"
        )
        return []


def load_or_update_stash(paths: Paths, werk_ids_client: WerkIDsClient) -> LegacyStash | Stash:
    stash = load_stash_from_file(paths)

    if isinstance(stash, LegacyStash):
        return stash

    if not paths.secret_file.exists():
        bail_out(f"No such secret file {paths.secret_file}")

    local_werk_ids_count = stash.count()

    if reserved_werk_ids := werk_ids_client.reserve_werk_ids(
        paths.secret_file, local_werk_ids_count
    ):
        stash.add_ids([WerkId(raw_id) for raw_id in reserved_werk_ids])
        dump_stash_to_file(paths, stash)
        return load_stash_from_file(paths)

    if not local_werk_ids_count:
        bail_out("No local or reserved werk IDs available.")

    return stash


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
