#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import sys
import traceback
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import requests

from .in_out_elements import bail_out, TTY_NORMAL, TTY_RED
from .schemas.werk import LegacyStash, Stash, WerkId

# Use a single short timeout for every request so commands fail fast when the werk IDs
# server is unreachable (e.g. outside the VPN, where DNS/connect behaviour differs)
# instead of blocking.
_TIMEOUT: Final = 5


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
        stash_file=home / ".local/state/cmk-werk-ids-reserved",
        secret_file=home / ".config/cmk-werk-ids-secret",
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
    if paths.legacy_stash_file.exists() and paths.stash_file.exists():
        bail_out(
            f"{TTY_RED}Found both a legacy and a new werk IDs file:\n"
            f"  {paths.legacy_stash_file}\n"
            f"  {paths.stash_file}\n"
            f"Please run 'werk init' to merge them into a single file.{TTY_NORMAL}"
        )
    if paths.secret_file.exists():
        return (
            Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8"))
            if paths.stash_file.exists()
            else Stash()
        )
    return load_legacy_stash_from_file(paths)


def dump_stash_to_file(paths: Paths, stash: LegacyStash | Stash) -> None:
    raw_stash = stash.model_dump_json(by_alias=True) + "\n"
    match stash:
        case LegacyStash():
            target = paths.legacy_stash_file
        case Stash():
            target = paths.stash_file
        case other:
            raise TypeError(other)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(raw_stash, encoding="utf-8")


def _read_legacy_stash_file(paths: Paths) -> Sequence[int]:
    if not paths.legacy_stash_file.exists():
        return []

    if not (content := paths.legacy_stash_file.read_text(encoding="utf-8")):
        return []

    if content[0] == "[":
        # we have a legacy file, from cmk project, we need to adapt it:
        raw_cmk_werk_ids = ast.literal_eval(content)
    else:
        parsed = json.loads(content)
        # The new-style JSON legacy file has {"__version__": ..., "ids_by_project": {...}}
        raw_cmk_werk_ids = parsed.get("ids_by_project", parsed).get("cmk", [])

    return [int(id_) for id_ in raw_cmk_werk_ids]


def migrate_werk_ids_file(paths: Paths) -> None:
    assert paths.secret_file.exists()

    stash = (
        Stash.model_validate_json(paths.stash_file.read_text(encoding="utf-8"))
        if paths.stash_file.exists()
        else Stash()
    )
    stash.add_ids([WerkId(id_) for id_ in _read_legacy_stash_file(paths)])

    dump_stash_to_file(paths, stash)
    paths.legacy_stash_file.unlink(missing_ok=True)


def _server_error_message(response: requests.Response) -> str:
    """Extract the error message from a JSON error response, falling back to the raw body."""
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict) and "error" in payload:
        return str(payload["error"])
    return response.text.strip()


class WerkIDsClient:
    URL: Final = "https://werk-ids.lan.checkmk.net"

    def ensure_connection(self) -> bool:
        try:
            response = requests.get(self.URL, timeout=_TIMEOUT)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException:
            traceback.print_exc(file=sys.stderr)
            sys.stderr.write("Failed: could not connect\n")
            return False

    def test_connection(self, secret_file_path: Path) -> bool:
        secret = secret_file_path.read_text(encoding="utf-8").strip()
        try:
            response = requests.get(
                f"{self.URL}/v1/connect",
                verify=True,
                headers={"Authorization": f"Bearer {secret}"},
                timeout=_TIMEOUT,
            )
        except requests.exceptions.RequestException:
            traceback.print_exc(file=sys.stderr)
            sys.stderr.write("Failed: could not connect\n")
            return False

        if response.status_code == 200:
            return True

        sys.stderr.write(
            f"{TTY_RED}Connection test failed "
            f"(status {response.status_code}): {_server_error_message(response)}{TTY_NORMAL}\n"
        )
        return False

    def reserve_werk_ids(self, secret_file_path: Path, local_werk_ids_count: int) -> Sequence[int]:
        secret = secret_file_path.read_text(encoding="utf-8").strip()
        try:
            response = requests.post(
                f"{self.URL}/v1/reserve",
                verify=True,
                headers={"Authorization": f"Bearer {secret}"},
                json={"local_werk_ids_count": local_werk_ids_count},
                timeout=_TIMEOUT,
            )
        except requests.exceptions.RequestException:
            # The server is unreachable (e.g. outside the VPN). Stay quiet and let the
            # caller decide: recover from locally reserved IDs, or bail out with a
            # descriptive message when none are left.
            return []

        if response.status_code == 200:
            reserved_werk_ids = response.json()["reserved_werk_ids"]
            return [int(i) for i in reserved_werk_ids]

        sys.stderr.write(
            f"{TTY_RED}Could not reserve werk IDs "
            f"(status {response.status_code}, server: {self.URL}): "
            f"{_server_error_message(response)}{TTY_NORMAL}\n"
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
        bail_out(
            f"\n{TTY_RED}No werk IDs available, and reserving new IDs from the werk IDs "
            "server failed.\n"
            "Please ensure that you're in the VPN and the werk IDs server is reachable, "
            f"then try again.{TTY_NORMAL}"
        )

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
