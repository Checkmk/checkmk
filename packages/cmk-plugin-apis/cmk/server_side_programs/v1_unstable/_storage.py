#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
from pathlib import Path
from typing import Final
from urllib.parse import quote as urlquote

_STORAGE_PATH_ENV: Final = "SERVER_SIDE_PROGRAM_STORAGE_PATH"


class Storage:
    """
    Storage interface for special agents and active checks.

    These programs may have the need to save some form of data in between runs.
    This interface provides a possibility to read and write text to a persistent storage.
    You can instantiate the storage interface with a program identifier and a host name,
    these are used to namespace the storage.

    Args:
        program_ident: A string identifying the program using the storage. This is used to
            namespace the storage.
        host: The host name the program is working for. This is used to namespace the storage.
    """

    def __init__(self, program_ident: str, host: str) -> None:
        self._ident: Final = program_ident
        self._host: Final = host

    @property
    def _full_dir(self) -> Path:
        return Path(
            self._get_base_path(),
            self._sanitize_key(self._host),
            self._sanitize_key(self._ident),
        )

    @staticmethod
    def _get_base_path() -> Path:
        if p := os.getenv(_STORAGE_PATH_ENV):
            return Path(p)
        raise RuntimeError(f"{_STORAGE_PATH_ENV} environment variable is not set.")

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

        Args:
            key: The unique key to identify the content. It will be sanitized and used as file name.
                After url quoting, the key must not be longer than 255 characters, otherwise a ValueError is raised.
            content: The serialized content to be stored.

        Raises:
            A RuntimeError is raised if SERVER_SIDE_PROGRAM_STORAGE_PATH environment variable is not set.
        """
        path = self._get_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def unset(self, key: str) -> None:
        """
        Remove key and its content from the storage.

        Args:
            key: The unique key to identify the content.

        Raises:
            A RuntimeError is raised if SERVER_SIDE_PROGRAM_STORAGE_PATH environment variable is not set.
        """
        path = self._get_path(key)
        path.unlink(missing_ok=True)

    def read[T](self, key: str, default: T) -> str | T:
        """
        Read content from the storage.

        Args:
            key: The unique key to identify the content.
            default: The default value to return if the key is unknown or the content is corrupted.

        Raises:
            A RuntimeError is raised if SERVER_SIDE_PROGRAM_STORAGE_PATH environment variable is not set.
        """
        path = self._get_path(key)
        try:
            return path.read_text()
        except (OSError, ValueError):
            return default
