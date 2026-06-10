#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Extract a Windows MSI installer into a directory tree on Linux.

A re-implementation of msitools' ``msiextract`` in pure Python.  Avoids
building msitools' Vala-based ``msiextract`` from source (its
auto-generated C breaks against modern glib).

Drives two Bazel-managed tools:

* ``msiinfo`` (from ``@msitools``) — reads the MSI's Directory / Component
  / File / Media tables and extracts the embedded cabinet streams.
* ``cabextract`` (from ``@cabextract``) — unpacks the (potentially
  LZX-compressed) cabinets that msiinfo dumps to disk.  cabarchive is
  MSZIP/none-only and can't read python.org's LZX cabinets.

Mirrors the upstream Vala logic in tools/msiextract.vala (LGPL-2.1+):
extract each cabinet, then rename the cab-internal entries (named after
the MSI's File-table keys) to their final on-disk paths derived from the
Component → Directory chain.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _run(msiinfo: str, subcommand: str, msi: Path, *args: str) -> bytes:
    """Run ``msiinfo <subcommand> <msi> [args]`` and return raw stdout bytes.

    msiinfo's CLI takes the MSI path as the *first* positional after the
    subcommand: ``msiinfo export FILE TABLE``, ``msiinfo extract FILE STREAM``,
    etc.  See ``msiinfo <subcommand> --help``.
    """
    cmd = [msiinfo, subcommand, str(msi), *args]
    proc = subprocess.run(cmd, capture_output=True, check=False)
    if proc.returncode != 0:
        sys.stderr.buffer.write(proc.stderr)
        raise SystemExit(
            f"msiinfo {subcommand} {msi.name} {' '.join(args)} failed (exit {proc.returncode})"
        )
    return proc.stdout


def _parse_idt(data: bytes) -> list[list[str]]:
    """Parse an IDT (MSI table export) blob into a list of rows.

    IDT format: tab-separated columns, lines separated by ``\\r\\n``.  Three
    header rows precede the data:
      1. column names
      2. column types
      3. table name + primary key column names
    """
    text = data.decode("utf-8", errors="replace")
    lines = text.split("\r\n")
    return [line.split("\t") for line in lines[3:] if line]


def _long_name(s: str) -> str:
    """An MSI file/directory name is ``short|long``; use long if present."""
    if "|" in s:
        return s.split("|", 1)[1]
    return s


def _resolve_directory(
    directories: dict[str, tuple[str, str]],
    dir_id: str,
) -> str:
    """Walk parent chain to build the install path for a Directory key.

    Mirrors ``msiextract.vala::extract``: per-entry rules are
      * ``ProgramFilesFolder`` → "Program Files"
      * ``.`` → empty (preserves parent path)
      * ``SourceDir`` → stop walking (this is the install root anchor)
    """

    def name_for(entry_key: str) -> str | None:
        _, default_dir = directories[entry_key]
        name = _long_name(default_dir)
        if entry_key == "ProgramFilesFolder":
            return "Program Files"
        if name == ".":
            return ""
        if name == "SourceDir":
            return None
        return name

    parts: list[str] = []
    cursor: str | None = dir_id
    while cursor is not None and cursor in directories:
        component_name = name_for(cursor)
        if component_name is None:
            break
        if component_name:
            parts.insert(0, component_name)
        cursor = directories[cursor][0] or None
    return "/".join(parts)


def _extract_msi(msiinfo: str, cabextract: str, msi: Path, out: Path) -> None:
    # Directory table: columns (Directory, Directory_Parent, DefaultDir).
    directories: dict[str, tuple[str, str]] = {}
    for row in _parse_idt(_run(msiinfo, "export", msi, "Directory")):
        if len(row) >= 3:
            directories[row[0]] = (row[1], row[2])

    # Component table: columns (Component, ComponentId, Directory_, Attributes, Condition, KeyPath).
    components_dir: dict[str, str] = {}
    for row in _parse_idt(_run(msiinfo, "export", msi, "Component")):
        if len(row) >= 3:
            components_dir[row[0]] = _resolve_directory(directories, row[2])

    # File table: columns (File, Component_, FileName, FileSize, Version, Language, Attributes, Sequence).
    cab_to_path: dict[str, str] = {}
    for row in _parse_idt(_run(msiinfo, "export", msi, "File")):
        if len(row) < 3:
            continue
        file_key, component_key, filename = row[0], row[1], row[2]
        target_dir = components_dir.get(component_key, "")
        cab_to_path[file_key] = (
            f"{target_dir}/{_long_name(filename)}" if target_dir else _long_name(filename)
        )

    # Media table: columns (DiskId, LastSequence, DiskPrompt, Cabinet, VolumeLabel, Source).
    cabinets: list[str] = []
    for row in _parse_idt(_run(msiinfo, "export", msi, "Media")):
        if len(row) >= 4 and row[3]:
            cabinets.append(row[3])

    # Each cabinet reference starts with '#' for an internal stream.  External
    # cabinets (no '#') aren't supported by this rule; the python.org per-feature
    # MSIs only ship internal cabs.
    for cab in cabinets:
        if not cab.startswith("#"):
            print(f"warning: external cabinet {cab!r} skipped in {msi.name}", file=sys.stderr)
            continue
        stream_name = cab[1:]
        cab_bytes = _run(msiinfo, "extract", msi, stream_name)
        if not cab_bytes:
            # Empty cabinet (e.g. pip.msi).  Nothing to extract.
            continue
        _extract_cab(cabextract, cab_bytes, cab_to_path, out)


def _extract_cab(
    cabextract: str,
    cab_bytes: bytes,
    cab_to_path: dict[str, str],
    out: Path,
) -> None:
    """Extract a cabinet (potentially LZX-compressed) and remap entries.

    cabextract unpacks files with their cab-internal names (which for MSIs
    are the File-table keys).  We then move each into its install-path slot
    via ``cab_to_path``.
    """
    with tempfile.TemporaryDirectory(prefix="msi-cab-") as staging:
        staging_path = Path(staging)
        cab_path = staging_path / "stream.cab"
        cab_path.write_bytes(cab_bytes)
        unpack_dir = staging_path / "unpacked"
        unpack_dir.mkdir()
        result = subprocess.run(
            [cabextract, "-q", "-d", str(unpack_dir), str(cab_path)],
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            sys.stderr.buffer.write(result.stderr)
            raise SystemExit(f"cabextract failed (exit {result.returncode})")

        for src in unpack_dir.rglob("*"):
            if not src.is_file():
                continue
            cab_name = str(src.relative_to(unpack_dir)).replace(os.sep, "/")
            target_rel = cab_to_path.get(cab_name, cab_name)
            target = out / target_rel.replace("\\", "/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(target))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--msiinfo", required=True, help="path to the msiinfo binary")
    parser.add_argument("--cabextract", required=True, help="path to the cabextract binary")
    parser.add_argument("--libmsi-dir", required=True, help="dir containing libmsi.so.0")
    parser.add_argument("-C", "--directory", required=True, type=Path, help="output dir")
    parser.add_argument("msi", nargs="+", type=Path, help="MSI files to extract")
    args = parser.parse_args()

    # msiinfo is dynamically linked against libmsi; make sure it can find it.
    env_ld = os.environ.get("LD_LIBRARY_PATH", "")
    os.environ["LD_LIBRARY_PATH"] = f"{args.libmsi_dir}:{env_ld}" if env_ld else args.libmsi_dir

    args.directory.mkdir(parents=True, exist_ok=True)
    for msi in args.msi:
        _extract_msi(args.msiinfo, args.cabextract, msi, args.directory)
    return 0


if __name__ == "__main__":
    sys.exit(main())
