#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import hashlib
import os
import stat
import sys
import zipfile
from pathlib import Path

import pytest
import set_runpath_tree
import set_runpath_whl

ELF_BLOB = b"\x7fELF binary payload"
TEXT_BLOB = b"plain text, not an executable\n"


@pytest.fixture(name="patchelf")
def fixture_patchelf(tmp_path: Path) -> Path:
    """A stand-in for patchelf that records the RUNPATH inside the patched file."""
    script = tmp_path / "patchelf"
    script.write_text(
        '#!/bin/sh\ntest "$1" = "--set-rpath" || exit 1\nprintf " RPATH=%s" "$2" >> "$3"\n'
    )
    script.chmod(0o755)
    return script


def _record_line(name: str, blob: bytes) -> str:
    digest = base64.urlsafe_b64encode(hashlib.sha256(blob).digest()).rstrip(b"=").decode()
    return f"{name},sha256={digest},{len(blob)}"


def _make_wheel(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as wheel:
        wheel.writestr("pkg/", b"")
        executable = zipfile.ZipInfo("pkg/bin/tool")
        executable.external_attr = (stat.S_IFREG | 0o755) << 16
        executable.compress_type = zipfile.ZIP_DEFLATED
        wheel.writestr(executable, ELF_BLOB)
        wheel.writestr("pkg/lib/nested/deep.so", ELF_BLOB)
        wheel.writestr("pkg/README", TEXT_BLOB)
        wheel.writestr(
            "pkg-1.0.dist-info/RECORD",
            "\n".join(
                [
                    _record_line("pkg/bin/tool", ELF_BLOB),
                    _record_line("pkg/lib/nested/deep.so", ELF_BLOB),
                    _record_line("pkg/README", TEXT_BLOB),
                    "pkg/not-in-wheel,sha256=abc,3",
                    "pkg-1.0.dist-info/RECORD,,",
                    "",
                ]
            ),
        )


def test_wheel_elf_files_get_depth_relative_runpath(
    tmp_path: Path, patchelf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src.whl"
    out = tmp_path / "out.whl"
    _make_wheel(src)
    monkeypatch.setattr(
        sys, "argv", ["set_runpath_whl.py", str(src), str(out), str(patchelf), "$ORIGIN/../lib"]
    )

    set_runpath_whl.main()

    with zipfile.ZipFile(out) as wheel:
        assert wheel.read("pkg/bin/tool") == ELF_BLOB + b" RPATH=$ORIGIN/../lib/.."
        assert wheel.read("pkg/lib/nested/deep.so") == ELF_BLOB + b" RPATH=$ORIGIN/../lib/../.."
        assert wheel.read("pkg/README") == TEXT_BLOB


def test_wheel_record_is_rewritten_for_patched_files(
    tmp_path: Path, patchelf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src.whl"
    out = tmp_path / "out.whl"
    _make_wheel(src)
    monkeypatch.setattr(
        sys, "argv", ["set_runpath_whl.py", str(src), str(out), str(patchelf), "$ORIGIN/../lib"]
    )

    set_runpath_whl.main()

    with zipfile.ZipFile(out) as wheel:
        record = wheel.read("pkg-1.0.dist-info/RECORD").decode().splitlines()
        tool = wheel.read("pkg/bin/tool")
        deep = wheel.read("pkg/lib/nested/deep.so")
    assert record == [
        _record_line("pkg/bin/tool", tool),
        _record_line("pkg/lib/nested/deep.so", deep),
        _record_line("pkg/README", TEXT_BLOB),
        "pkg/not-in-wheel,sha256=abc,3",
        "pkg-1.0.dist-info/RECORD,,",
    ]


def test_wheel_entry_metadata_is_preserved(
    tmp_path: Path, patchelf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src.whl"
    out = tmp_path / "out.whl"
    _make_wheel(src)
    monkeypatch.setattr(
        sys, "argv", ["set_runpath_whl.py", str(src), str(out), str(patchelf), "$ORIGIN/../lib"]
    )

    set_runpath_whl.main()

    with zipfile.ZipFile(out) as wheel:
        assert "pkg/" in wheel.namelist()
        tool = wheel.getinfo("pkg/bin/tool")
    assert stat.S_IMODE(tool.external_attr >> 16) == 0o755
    assert tool.compress_type == zipfile.ZIP_DEFLATED


def test_wheel_without_record_is_patched_anyway(
    tmp_path: Path, patchelf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src.whl"
    out = tmp_path / "out.whl"
    with zipfile.ZipFile(src, "w") as wheel:
        wheel.writestr("tool", ELF_BLOB)
    monkeypatch.setattr(
        sys, "argv", ["set_runpath_whl.py", str(src), str(out), str(patchelf), "$ORIGIN"]
    )

    set_runpath_whl.main()

    with zipfile.ZipFile(out) as wheel:
        assert wheel.read("tool") == ELF_BLOB + b" RPATH=$ORIGIN"


def _make_tree(root: Path) -> None:
    (root / "bin").mkdir(parents=True)
    (root / "lib/nested").mkdir(parents=True)
    (root / "bin/tool").write_bytes(ELF_BLOB)
    (root / "lib/nested/deep.so").write_bytes(ELF_BLOB)
    (root / "top").write_bytes(ELF_BLOB)
    (root / "README").write_bytes(TEXT_BLOB)
    os.symlink("tool", root / "bin/tool-link")


def test_tree_is_copied_and_elf_files_patched_by_depth(
    tmp_path: Path, patchelf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    src = tmp_path / "src"
    out = tmp_path / "out"
    _make_tree(src)
    monkeypatch.setattr(
        sys, "argv", ["set_runpath_tree.py", str(src), str(out), str(patchelf), "$ORIGIN/../lib"]
    )

    set_runpath_tree.main()

    assert (out / "top").read_bytes() == ELF_BLOB + b" RPATH=$ORIGIN/../lib"
    assert (out / "bin/tool").read_bytes() == ELF_BLOB + b" RPATH=$ORIGIN/../lib"
    assert (out / "lib/nested/deep.so").read_bytes() == ELF_BLOB + b" RPATH=$ORIGIN/../lib/.."
    assert (out / "README").read_bytes() == TEXT_BLOB
    assert (src / "bin/tool").read_bytes() == ELF_BLOB, "the source tree is left untouched"


def test_tree_symlinks_are_not_patched_twice(
    tmp_path: Path, patchelf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When copying, symlinks are dereferenced into plain files. Only the in-place mode
    keeps them, and there the link target must not be patched a second time via the link."""
    tree = tmp_path / "tree"
    _make_tree(tree)
    monkeypatch.setattr(
        sys, "argv", ["set_runpath_tree.py", str(tree), str(tree), str(patchelf), "$ORIGIN"]
    )

    set_runpath_tree.main()

    assert (tree / "bin/tool-link").is_symlink()
    assert (tree / "bin/tool").read_bytes().count(b"RPATH=") == 1


def test_tree_can_be_patched_in_place(
    tmp_path: Path, patchelf: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tree = tmp_path / "tree"
    _make_tree(tree)
    monkeypatch.setattr(
        sys, "argv", ["set_runpath_tree.py", str(tree), str(tree), str(patchelf), "$ORIGIN"]
    )

    set_runpath_tree.main()

    assert (tree / "top").read_bytes() == ELF_BLOB + b" RPATH=$ORIGIN"
