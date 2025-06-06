#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
import marshal
import os
import py_compile
import struct
from collections.abc import Callable, Iterable, Mapping, Sequence
from importlib.util import MAGIC_NUMBER
from pathlib import Path
from types import CodeType
from typing import Self

from .v0_unstable import LegacyCheckDefinition


def find_plugin_files(directory: Path) -> tuple[str, ...]:
    return tuple(_plugin_pathnames_in_directory(directory))


def _plugin_pathnames_in_directory(path: Path) -> Iterable[str]:
    try:
        return sorted(
            [
                f"{path}/{f}"
                for f in os.listdir(path)
                if not f.startswith(".") and not f.endswith(".include") and not f == "__pycache__"
            ]
        )
    except FileNotFoundError:
        return ()


class _PYCHeader:
    """A pyc header according to https://www.python.org/dev/peps/pep-0552/"""

    SIZE = 16

    def __init__(self, magic: bytes, hash_: int, origin_mtime: int, f_size: int) -> None:
        self.magic = magic
        self.hash = hash_
        self.origin_mtime = origin_mtime
        self.f_size = f_size

    @classmethod
    def from_file(cls, path: str) -> Self:
        with open(path, "rb") as handle:
            raw_bytes = handle.read(cls.SIZE)
        init_args: tuple[bytes, int, int, int] = struct.unpack("4s3I", raw_bytes)
        return cls(*init_args)


class FileLoader:
    def __init__(self, *, precomile_path: Path, makedirs: Callable[[str], None]) -> None:
        self._precompile_path = precomile_path
        self._makedirs = makedirs

    def load_into(self, path: str, check_context: dict[str, object]) -> bool:
        """Loads the given check or check include plug-in into the given
        check context.

        To improve loading speed the files are not read directly. The files are
        python byte-code compiled before in case it has not been done before. In
        case there is already a compiled file that is newer than the current one,
        then the precompiled file is loaded.

        Returns `True` if something has been compiled, else `False`.
        """

        # https://docs.python.org/3/library/py_compile.html
        # HACK:
        precompiled_path = self._precompiled_plugin_path(path)

        do_compile = not self._is_plugin_precompiled(path, precompiled_path)
        if do_compile:
            self._makedirs(os.path.dirname(precompiled_path))
            py_compile.compile(path, precompiled_path, doraise=True)
            # The original file is from the version so the calculated mode is world readable...
            os.chmod(precompiled_path, 0o640)

        code: CodeType = marshal.loads(Path(precompiled_path).read_bytes()[_PYCHeader.SIZE :])  # nosec B302
        exec(code, check_context)  # nosec B102 # BNS:aee528

        return do_compile

    def _is_plugin_precompiled(self, path: str, precompiled_path: str) -> bool:
        # Check precompiled file header
        try:
            header = _PYCHeader.from_file(precompiled_path)
        except (FileNotFoundError, struct.error):
            return False

        if header.magic != MAGIC_NUMBER:
            return False

        # Skip the hash and assure that the timestamp format is used, i.e. the hash is 0.
        # For further details see: https://www.python.org/dev/peps/pep-0552/#id15
        assert header.hash == 0

        return int(os.stat(path).st_mtime) == header.origin_mtime

    def _precompiled_plugin_path(self, path: str) -> str:
        return str(self._precompile_path / "builtin" / os.path.basename(path))


@dataclasses.dataclass
class DiscoveredLegacyChecks:
    ignored_plugins_errors: Sequence[str]
    sane_check_info: Sequence[LegacyCheckDefinition]
    plugin_files: Mapping[str, str]
    did_compile: bool


def discover_legacy_checks(
    filelist: Iterable[str],
    loader: FileLoader,
    *,
    raise_errors: bool,
) -> DiscoveredLegacyChecks:
    loaded_files: set[str] = set()
    ignored_plugins_errors = []
    sane_check_info = []
    legacy_check_plugin_files: dict[str, str] = {}

    did_compile = False
    for f in filelist:
        if f[0] == "." or f[-1] == "~":
            continue  # ignore editor backup / temp files

        file_name = os.path.basename(f)
        if file_name in loaded_files:
            continue  # skip already loaded files (e.g. from local)

        try:
            check_context: dict[str, object] = {}
            did_compile |= loader.load_into(f, check_context)

            loaded_files.add(file_name)

            if not isinstance(defined_checks := check_context.get("check_info", {}), dict):
                raise TypeError(defined_checks)

        except Exception as e:
            if raise_errors:
                raise
            ignored_plugins_errors.append(
                f"Ignoring outdated plug-in file {f}: {e} -- this API is deprecated!"
            )
            continue

        for plugin in defined_checks.values():
            if isinstance(plugin, LegacyCheckDefinition):  # type: ignore[misc]  # contains Any
                sane_check_info.append(plugin)
                legacy_check_plugin_files[plugin.name] = f
            else:
                # Now just drop everything we don't like; this is not a supported API anymore.
                # Users affected by this will see a CRIT in their "Analyse Configuration" page.
                ignored_plugins_errors.append(
                    f"Ignoring outdated plug-in in {f!r}: Format no longer supported"
                    " -- this API is deprecated!"
                )

    return DiscoveredLegacyChecks(
        ignored_plugins_errors, sane_check_info, legacy_check_plugin_files, did_compile
    )
