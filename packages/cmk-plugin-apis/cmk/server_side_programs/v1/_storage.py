#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import os
import tempfile
from pathlib import Path
from typing import Final, final, Protocol
from urllib.parse import quote as urlquote

_STORAGE_PATH_ENV: Final = "SERVER_SIDE_PROGRAM_STORAGE_PATH"


def _get_base_path() -> Path:
    if p := os.getenv(_STORAGE_PATH_ENV):
        return Path(p)
    raise RuntimeError(f"{_STORAGE_PATH_ENV} environment variable is not set.")


def _sanitize_key(key: str) -> str:
    skey = urlquote(key, safe="")
    if len(skey) > 255:
        raise ValueError(f"too long (max 255 characters after URL quoting): {skey!r}")
    return skey


def _storage_dir(*, host: str, ident: str) -> Path:
    return Path(_get_base_path(), _sanitize_key(host), _sanitize_key(ident))


def _key_path(directory: Path, key: str) -> Path:
    return directory / _sanitize_key(key)


def _write_atomically(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # The "%t" prefix can never be the result of URL quoting, so the temporary
    # file never collides with a key. The replace stays inside the with, so any
    # exception deletes the temp file instead.
    with tempfile.NamedTemporaryFile(
        "wb", dir=path.parent, prefix="%tmp", delete_on_close=False
    ) as tmp:
        tmp.write(content)
        tmp.close()
        os.replace(tmp.name, path)


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

    def _path(self, key: str) -> Path:
        return _key_path(_storage_dir(host=self._host, ident=self._ident), key)

    def write(self, key: str, content: str) -> None:
        """
        Write text content to the storage.

        The content is replaced atomically: a concurrent `read` returns either the
        previous or the new content, never a partially written one.

        Args:
            key: The unique key to identify the content. It will be sanitized and used as file name.
                After url quoting, the key must not be longer than 255 characters, otherwise a ValueError is raised.
            content: The serialized content to be stored.

        Raises:
            A RuntimeError is raised if SERVER_SIDE_PROGRAM_STORAGE_PATH environment variable is not set.
        """
        _write_atomically(self._path(key), content.encode("utf-8"))

    def unset(self, key: str) -> None:
        """
        Remove key and its content from the storage.

        Args:
            key: The unique key to identify the content.

        Raises:
            A RuntimeError is raised if SERVER_SIDE_PROGRAM_STORAGE_PATH environment variable is not set.
        """
        self._path(key).unlink(missing_ok=True)

    def read[T](self, key: str, default: T) -> str | T:
        """
        Read content from the storage.

        Args:
            key: The unique key to identify the content.
            default: The default value to return if the key is unknown or the content is corrupted.

        Raises:
            A RuntimeError is raised if SERVER_SIDE_PROGRAM_STORAGE_PATH environment variable is not set.
        """
        path = self._path(key)
        try:
            return path.read_bytes().decode("utf-8")
        except OSError, ValueError:
            return default


class ObfuscatorP[T](Protocol):
    """
    Turns values into bytes that do not reveal them, and back.

    See :class:`ObfuscatedStorage`.
    For secrets, use `cmk.password_store.v1.Obfuscator`.
    """

    def obfuscate(self, value: T, /) -> bytes:
        """Return the obfuscated form of the value."""
        ...

    def deobfuscate(self, raw: bytes, /) -> T:
        """
        Return the value from its obfuscated form.

        Raises:
            ValueError: If the data cannot be deobfuscated.
        """
        ...


@final
class ObfuscatedStorage[T]:
    """
    Storage interface for values that should not be stored in plain text.

    This works like :class:`Storage`, but the values pass through an obfuscator
    before they are written, and after they are read.
    Note that obfuscation is not encryption in the strict sense: anyone who can
    read the site's files can usually also read the key used for obfuscation.

    .. warning::

        Failing to deobfuscate a value is **not** reported as an error.
        If the obfuscator raises a :class:`ValueError` (for instance because the
        key used for obfuscation has changed, or the stored data is corrupted),
        :meth:`read` silently returns the passed default value, just as if the
        key had never been written.
        Callers must be prepared to recreate the value in that case.

    The storage uses the same namespace as a :class:`Storage` created with the same
    program identifier and host name.
    Do not use the same key with both of them.

    Args:
        program_ident: A string identifying the program using the storage. This is used to
            namespace the storage.
        host: The host name the program is working for. This is used to namespace the storage.
        obfuscator: The obfuscator turning the values into bytes and back.
            For secrets, use `cmk.password_store.v1.Obfuscator`.

    Example::

        class Rot13:
            def obfuscate(self, value: str) -> bytes:
                return codecs.encode(value, "rot13").encode()

            def deobfuscate(self, raw: bytes) -> str:
                return codecs.decode(raw.decode(), "rot13")

        storage = ObfuscatedStorage("my_special_agent", host_name, Rot13())
        storage.write("token", token)
        token = storage.read("token", None)

    """

    def __init__(self, program_ident: str, host: str, obfuscator: ObfuscatorP[T]) -> None:
        self._ident: Final = program_ident
        self._host: Final = host
        self._obfuscator: Final = obfuscator

    def _path(self, key: str) -> Path:
        return _key_path(_storage_dir(host=self._host, ident=self._ident), key)

    def write(self, key: str, value: T) -> None:
        """
        Write an obfuscated value to the storage.

        The value is replaced atomically: a concurrent `read` returns either the
        previous or the new value, never a partially written one.

        Args:
            key: The unique key to identify the value. It will be sanitized and used as file name.
                After url quoting, the key must not be longer than 255 characters, otherwise a ValueError is raised.
            value: The value to be stored.

        Raises:
            A RuntimeError is raised if SERVER_SIDE_PROGRAM_STORAGE_PATH environment variable is not set.
        """
        _write_atomically(self._path(key), self._obfuscator.obfuscate(value))

    def unset(self, key: str) -> None:
        """
        Remove key and its value from the storage.

        Args:
            key: The unique key to identify the value.

        Raises:
            A RuntimeError is raised if SERVER_SIDE_PROGRAM_STORAGE_PATH environment variable is not set.
        """
        self._path(key).unlink(missing_ok=True)

    def read[D](self, key: str, default: D) -> T | D:
        """
        Read a value from the storage.

        Args:
            key: The unique key to identify the value.
            default: The default value to return if the key is unknown or the value
                cannot be deobfuscated.

        Raises:
            A RuntimeError is raised if SERVER_SIDE_PROGRAM_STORAGE_PATH environment variable is not set.
        """
        path = self._path(key)
        try:
            return self._obfuscator.deobfuscate(path.read_bytes())
        except OSError, ValueError:
            return default
