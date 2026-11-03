#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import io
import zipfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

import cmk.ec.export as ec
from cmk.gui.mkeventd.mib_upload import upload_mibs

_MIB = b"TEST-MIB DEFINITIONS ::= BEGIN\nEND\n"


@dataclass(frozen=True, kw_only=True)
class _Compilation:
    mibname: ec.MibName
    content: str
    source_dirs: Sequence[Path]
    search_dirs: Sequence[Path]
    destination_dir: Path


class _FakeCompiler:
    """Records the compilations, without compiling anything

    The compiled MIB gets the status "compiled", other MIBs the given status, e.g. the ones it
    imports."""

    def __init__(self, statuses: Mapping[ec.MibName, ec.MibStatus] | None = None) -> None:
        self._statuses = statuses or {}
        self.compilations: list[_Compilation] = []

    def __call__(
        self,
        *,
        mibname: ec.MibName,
        content: str,
        source_dirs: Iterable[Path],
        search_dirs: Iterable[Path],
        destination_dir: Path,
    ) -> Mapping[ec.MibName, ec.MibStatus]:
        self.compilations.append(
            _Compilation(
                mibname=mibname,
                content=content,
                source_dirs=list(source_dirs),
                search_dirs=list(search_dirs),
                destination_dir=destination_dir,
            )
        )
        return {mibname: ec.MibStatus(status="compiled")} | dict(self._statuses)


class _FakeCompilerMaker:
    """Makes fake compilers, remembering them"""

    def __init__(self) -> None:
        self.made: list[_FakeCompiler] = []

    def __call__(self) -> _FakeCompiler:
        self.made.append(_FakeCompiler())
        return self.made[-1]


def _failed(error: str) -> ec.MibStatus:
    """The status of a MIB the compiler failed to compile, with the error"""
    return ec.MibStatus(status="failed", error=error)


@pytest.fixture(name="paths")
def fixture_paths(tmp_path: Path) -> ec.Paths:
    return ec.create_paths(tmp_path)


def _upload(
    file_name: str,
    content: bytes,
    paths: ec.Paths,
    compiler: _FakeCompiler | None = None,
    mimetype: str = "text/plain",
    *,
    make_compiler: Callable[[], _FakeCompiler] | None = None,
    on_stored: Callable[[str, str], None] = lambda _file_name, _msg: None,
) -> str:
    return upload_mibs(
        file_name,
        mimetype,
        content,
        make_compile_mib=make_compiler or (lambda: compiler or _FakeCompiler()),
        paths=paths,
        source_dirs=[],
        on_stored=on_stored,
    )


def _custom_mibs(paths: ec.Paths) -> list[str]:
    return sorted(path.name for path in paths.local_mibs_dir.value.glob("*"))


def test_uploading_a_mib_keeps_it_and_compiles_it_for_translating_traps(paths: ec.Paths) -> None:
    compiler = _FakeCompiler()

    _upload("test-mib.txt", _MIB, paths, compiler)

    assert _custom_mibs(paths) == ["test-mib.txt"]
    assert [(c.mibname, c.destination_dir) for c in compiler.compilations] == [
        ("TEST-MIB", paths.compiled_mibs_dir.value)
    ]


def test_an_uploaded_mib_may_import_the_mibs_compiled_before(paths: ec.Paths) -> None:
    compiler = _FakeCompiler()

    _upload("test-mib.txt", _MIB, paths, compiler)

    [compilation] = compiler.compilations
    assert paths.compiled_mibs_dir.value in compilation.search_dirs


def test_uploading_a_mib_reports_it_as_uploaded(paths: ec.Paths) -> None:
    message = _upload("test-mib.txt", _MIB, paths)

    assert message == "MIB file TEST-MIB uploaded."


def test_uploading_a_mib_tells_about_the_stored_file(paths: ec.Paths) -> None:
    told: list[tuple[str, str]] = []

    _upload("test-mib.txt", _MIB, paths, on_stored=lambda name, msg: told.append((name, msg)))

    assert told == [("test-mib.txt", "MIB file TEST-MIB uploaded.")]


def test_uploading_a_mib_reports_the_mibs_it_imports_which_are_missing(paths: ec.Paths) -> None:
    compiler = _FakeCompiler({ec.MibName("SNMPv2-SMI"): ec.MibStatus(status="missing")})

    message = _upload("test-mib.txt", _MIB, paths, compiler)

    assert message == (
        "MIB file TEST-MIB uploaded.<br>But there were errors:<br>SNMPv2-SMI - Dependency missing"
    )


def test_uploading_a_mib_which_is_no_utf8_keeps_it_unchanged(paths: ec.Paths) -> None:
    content = b"-- Copyright Caf\xe9 GmbH\n" + _MIB

    _upload("test-mib.txt", content, paths)

    assert (paths.local_mibs_dir.value / "test-mib.txt").read_bytes() == content


def test_uploading_a_mib_which_fails_to_compile_is_refused(paths: ec.Paths) -> None:
    compiler = _FakeCompiler({ec.MibName("BROKEN"): _failed("Bad grammar")})

    with pytest.raises(Exception, match="Failed to compile your module: Bad grammar"):
        _upload("broken.txt", b"BROKEN DEFINITIONS ::= BEGIN nonsense", paths, compiler)


def test_uploading_a_mib_named_otherwise_than_its_file_which_fails_to_compile_is_refused(
    paths: ec.Paths,
) -> None:
    # The compiler tells the status of a MIB by the name in its definition.
    compiler = _FakeCompiler({ec.MibName("IANAifType-MIB"): _failed("Bad grammar")})

    with pytest.raises(Exception, match="Failed to compile your module: Bad grammar"):
        _upload(
            "iana-iftype.mib",
            b"-- IANA ifTypes\nIANAifType-MIB DEFINITIONS ::= BEGIN nonsense",
            paths,
            compiler,
        )


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"IANAifType-MIB DEFINITIONS ::= BEGIN\nEND\n", id="plain"),
        pytest.param(b"IANAifType-MIB -- IANA ifTypes\nDEFINITIONS ::= BEGIN\nEND\n", id="comment after the name"),
        pytest.param(b"-- IANA ifTypes\rIANAifType-MIB DEFINITIONS ::= BEGIN\rEND\r", id="lines ending with CR"),
    ],
)  # fmt: skip
def test_uploading_a_mib_reports_it_by_the_name_in_its_definition(
    content: bytes, paths: ec.Paths
) -> None:
    message = _upload("iana-iftype.mib", content, paths)

    assert message == "MIB file IANAifType-MIB uploaded."


@pytest.mark.parametrize(
    "file_name, content, error",
    [
        pytest.param("empty.txt", b"", "The file is empty", id="empty file"),
        pytest.param(".test-mib.txt", _MIB, "Invalid file name", id="hidden file"),
        pytest.param("mibs.tar.gz", b"no zip file", "TAR/GZ files", id="tar file"),
    ],
)
def test_an_upload_refused_before_compiling_makes_no_compiler(
    file_name: str, content: bytes, error: str, paths: ec.Paths
) -> None:
    maker = _FakeCompilerMaker()

    with pytest.raises(Exception, match=error):
        _upload(file_name, content, paths, make_compiler=maker)

    assert maker.made == []


def _zip_file(entries: Mapping[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for name, content in entries.items():
            zip_file.writestr(name, content)
    return buffer.getvalue()


def test_uploading_a_zip_file_uploads_the_mibs_in_its_root_directory(paths: ec.Paths) -> None:
    zip_file = _zip_file(
        {
            "test-mib.txt": _MIB,
            "other-mib.txt": b"OTHER-MIB DEFINITIONS ::= BEGIN\nEND\n",
            "subdir/": b"",
            "subdir/skipped-mib.txt": b"SKIPPED-MIB DEFINITIONS ::= BEGIN\nEND\n",
        }
    )
    compiler = _FakeCompiler()

    _upload("mibs.zip", zip_file, paths, compiler, mimetype="application/zip")

    assert _custom_mibs(paths) == ["other-mib.txt", "test-mib.txt"]
    assert [c.mibname for c in compiler.compilations] == ["TEST-MIB", "OTHER-MIB"]


def test_uploading_a_zip_file_compiles_all_its_mibs_with_one_compiler(paths: ec.Paths) -> None:
    zip_file = _zip_file(
        {"test-mib.txt": _MIB, "other-mib.txt": b"OTHER-MIB DEFINITIONS ::= BEGIN\nEND\n"}
    )
    maker = _FakeCompilerMaker()

    _upload("mibs.zip", zip_file, paths, mimetype="application/zip", make_compiler=maker)

    assert [[c.mibname for c in compiler.compilations] for compiler in maker.made] == [
        ["TEST-MIB", "OTHER-MIB"]
    ]


def test_uploading_a_zip_file_tells_about_every_mib_file_right_after_storing_it(
    paths: ec.Paths,
) -> None:
    zip_file = _zip_file(
        {"test-mib.txt": _MIB, "other-mib.txt": b"OTHER-MIB DEFINITIONS ::= BEGIN\nEND\n"}
    )
    told: list[tuple[str, list[str]]] = []

    _upload(
        "mibs.zip",
        zip_file,
        paths,
        mimetype="application/zip",
        on_stored=lambda name, _msg: told.append((name, _custom_mibs(paths))),
    )

    assert told == [
        ("test-mib.txt", ["test-mib.txt"]),
        ("other-mib.txt", ["other-mib.txt", "test-mib.txt"]),
    ]


def test_uploading_a_zip_file_fails_if_telling_about_a_stored_mib_file_fails(
    paths: ec.Paths,
) -> None:
    # The MIB file is stored, so reporting it as skipped would be wrong.
    def fail(_name: str, _msg: str) -> None:
        raise OSError("Cannot save the change")

    with pytest.raises(OSError, match="Cannot save the change"):
        _upload(
            "mibs.zip",
            _zip_file({"test-mib.txt": _MIB}),
            paths,
            mimetype="application/zip",
            on_stored=fail,
        )


def test_uploading_a_zip_file_reports_how_many_mib_files_it_processed_and_skipped(
    paths: ec.Paths,
) -> None:
    zip_file = _zip_file(
        {
            "test-mib.txt": _MIB,
            "subdir/": b"",
            "subdir/other-mib.txt": b"OTHER-MIB DEFINITIONS ::= BEGIN\nEND\n",
        }
    )

    message = _upload("mibs.zip", zip_file, paths, mimetype="application/zip")

    assert message.endswith("Processed 1 MIB files, skipped 1 MIB files")
