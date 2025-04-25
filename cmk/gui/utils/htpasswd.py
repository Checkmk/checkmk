#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

from cmk.ccc import store
from cmk.ccc.user import UserId

from cmk.crypto.password_hashing import PasswordHash

Entries = dict[UserId, PasswordHash]


class Htpasswd:
    """A wrapper for manipulating the htpasswd file"""

    def __init__(self, path: Path) -> None:
        self._path = path

    @staticmethod
    def serialize_entries(entries: Sequence[tuple[UserId, PasswordHash]]) -> str:
        return "\n".join(f"{user_id}:{password_hash}" for user_id, password_hash in entries)

    def load(self, allow_missing_file: bool = False) -> Entries:
        """Loads the contents of a valid htpasswd file into a dictionary and returns the dictionary

        If the file does not exist, an empty result is returned if allow_missing_file is True,
        otherwise an OSError is raised.
        """
        entries = {}

        try:
            filecontent = self._path.read_text(encoding="utf-8").splitlines()
        except OSError:
            if not allow_missing_file:
                raise
            return {}

        for entry in filecontent:
            try:
                user_id, pw_hash = entry.split(":", 1)
                entries[UserId(user_id)] = PasswordHash(pw_hash)
            except ValueError:
                # ignore lines without ":" and invalid user names
                continue

        return entries

    def save_all(self, entries: Entries) -> None:
        """Save entries to the htpasswd file, overriding the original file"""
        store.save_text_to_file(self._path, self.serialize_entries(sorted(entries.items())) + "\n")

    def exists(self, user_id: UserId) -> bool:
        """Whether or not a user exists according to the htpasswd file"""
        return user_id in self.load()

    def get_hash(self, user_id: UserId) -> None | PasswordHash:
        return self.load().get(user_id)

    def save(self, user_id: UserId, pw_hash: PasswordHash) -> None:
        entries = self.load()
        entries[user_id] = pw_hash
        self.save_all(entries)
