#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from pathlib import Path
from urllib.parse import quote as urlquote

SERVER_SIDE_PROGRAM_STORAGE_PATH = "var/check_mk/server_side_program_storage"


class Storage:
    """
    Storage interface for server side programs (special agents and active checks).
    These programs may have the need to save some form of data in between runs.
    Therefore, this interface transparently provides a possibility to read and write text to a persistent storage.
    """

    def __init__(self, program_ident: str, host: str) -> None:
        """
        Initializes the storage interface. program_ident and host provide an identifier to namespace
        the storage.

        Raises a RuntimeError if OMD_ROOT environment variable is not set.
        """
        self._full_dir = Path(
            self._get_base_path(), self._sanitize_key(program_ident), self._sanitize_key(host)
        )

    @staticmethod
    def _get_base_path() -> Path:
        if omd_root := os.getenv("OMD_ROOT"):
            return Path(omd_root, SERVER_SIDE_PROGRAM_STORAGE_PATH)
        raise RuntimeError("OMD_ROOT environment variable is not set.")

    @staticmethod
    def _sanitize_key(key: str) -> str:
        skey = urlquote(key, safe="")
        if len(skey) > 255:
            raise ValueError(f"too long (max 255 characters after URL quoting): {skey!r}")
        return skey

    def _get_path(self, key: str) -> Path:
        safe_key = self._sanitize_key(key)
        return self._full_dir / safe_key

    def write(self, key: str, content: str) -> None:
        """
        Write text content to the storage.
        """
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def read[T](self, key: str, default: T) -> str | T:
        """
        Read content from the storage.

        If the key is unknown or the content is corrupted, return default.
        """
        path = self._get_path(key)
        try:
            return path.read_text()
        except (OSError, ValueError):
            return default
