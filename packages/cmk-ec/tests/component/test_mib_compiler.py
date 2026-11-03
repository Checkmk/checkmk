#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

import gc
from pathlib import Path
from types import FrameType

import pytest
from pysmi.codegen.pysnmp import PySnmpCodeGen
from pysmi.compiler import MibCompiler as PySmiCompiler
from pysmi.parser.smiv1compat import SmiV1CompatParser
from pysmi.reader.callback import CallbackReader
from pysmi.reader.localfile import FileReader
from pysmi.writer.pyfile import PyFileWriter

from cmk.ec.mib_compiler import MibCompiler
from cmk.ec.mib_status import MibName, MibStatus

_TEST_MIB = MibName("TEST-MIB")
_BROKEN_MIB = MibName("BROKEN-MIB")
_SELF_CONTAINED_MIB = """TEST-MIB DEFINITIONS ::= BEGIN
testRoot OBJECT IDENTIFIER ::= { iso 3 6 1 4 1 99999 }
END
"""


def test_valid_mib_is_written_to_destination(tmp_path: Path) -> None:
    results = MibCompiler().compile(
        mibname=_TEST_MIB,
        content=_SELF_CONTAINED_MIB,
        source_dirs=[],
        search_dirs=[],
        destination_dir=tmp_path,
    )

    assert results[_TEST_MIB].status == "compiled"
    assert (tmp_path / "TEST-MIB.py").exists()


def test_invalid_mib_is_reported_as_failed_with_the_error(tmp_path: Path) -> None:
    results = MibCompiler().compile(
        mibname=_BROKEN_MIB,
        content="BROKEN-MIB DEFINITIONS ::= BEGIN nonsense",
        source_dirs=[],
        search_dirs=[],
        destination_dir=tmp_path,
    )

    assert results[_BROKEN_MIB] == MibStatus(
        status="failed", error="Bad grammar near offset 33 at MIB BROKEN-MIB, line 1"
    )


def test_a_remembered_parse_error_keeps_no_state_of_the_compilation(tmp_path: Path) -> None:
    # The compiler remembers the errors of recently parsed MIBs, but neither the errors of lark
    # causing them, which keep the state of its parser and the MIB text, nor their frames, which
    # keep the ones calling them, with the whole state of pysmi's compilation.
    compiler = MibCompiler()
    compiler.compile(
        mibname=_BROKEN_MIB,
        content="BROKEN-MIB DEFINITIONS ::= BEGIN nonsense",
        source_dirs=[],
        search_dirs=[],
        destination_dir=tmp_path,
    )

    gc.collect()

    assert [
        type(obj).__name__
        for obj in gc.get_objects()
        if isinstance(obj, BaseException) and type(obj).__module__.startswith("lark")
    ] == []
    assert [
        frame.f_code.co_qualname
        for frame in gc.get_objects()
        if isinstance(frame, FrameType) and frame.f_globals.get("__name__", "").startswith("pysmi")
    ] == []


def test_a_compiler_compiles_a_mib_after_one_which_failed(tmp_path: Path) -> None:
    compiler = MibCompiler()

    failed = compiler.compile(
        mibname=_BROKEN_MIB,
        content="BROKEN-MIB DEFINITIONS ::= BEGIN nonsense",
        source_dirs=[],
        search_dirs=[],
        destination_dir=tmp_path,
    )

    assert failed[_BROKEN_MIB].status == "failed"

    results = compiler.compile(
        mibname=_TEST_MIB,
        content=_SELF_CONTAINED_MIB,
        source_dirs=[],
        search_dirs=[],
        destination_dir=tmp_path,
    )

    assert results[_TEST_MIB].status == "compiled"


def _mib_importing_broken_mib(mibname: MibName) -> str:
    return f"""{mibname} DEFINITIONS ::= BEGIN
IMPORTS
    broken FROM BROKEN-MIB;
testRoot OBJECT IDENTIFIER ::= {{ broken 1 }}
END
"""


def test_a_mib_failing_to_parse_has_the_same_error_in_every_compilation_importing_it(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "BROKEN-MIB.txt").write_text("BROKEN-MIB DEFINITIONS ::= BEGIN nonsense")
    compiler = MibCompiler()

    first, second = (
        compiler.compile(
            mibname=mibname,
            content=_mib_importing_broken_mib(mibname),
            source_dirs=[source_dir],
            search_dirs=[],
            destination_dir=tmp_path,
        )[_BROKEN_MIB]
        for mibname in (MibName("FIRST-MIB"), MibName("SECOND-MIB"))
    )

    assert second == MibStatus(status="failed", error=first.error)


# Rooted at iso and using only macros of SNMPv2-SMI and SNMPv2-TC, so that it compiles without them
_BASE_MIB = """TEST-BASE-MIB DEFINITIONS ::= BEGIN
IMPORTS
    MODULE-IDENTITY FROM SNMPv2-SMI
    TEXTUAL-CONVENTION FROM SNMPv2-TC;

testBase MODULE-IDENTITY
    LAST-UPDATED "202610280000Z"
    ORGANIZATION "Checkmk"
    CONTACT-INFO "nobody"
    DESCRIPTION "The base of the test MIBs"
    ::= { iso 3 6 1 4 1 99999 }

TestState ::= TEXTUAL-CONVENTION
    STATUS current
    DESCRIPTION "A state"
    SYNTAX INTEGER { up(1), down(2) }

testObjects OBJECT IDENTIFIER ::= { testBase 1 }
END
"""


def _mib_importing_base_mib(mibname: MibName, number: int) -> str:
    """An SMIv1 MIB, whose imports pysmi converts to SMIv2 ones in the parse tree"""
    return f"""{mibname} DEFINITIONS ::= BEGIN
IMPORTS
    OBJECT-TYPE FROM RFC-1212
    TRAP-TYPE FROM RFC-1215
    testObjects, TestState FROM TEST-BASE-MIB;

entryTable OBJECT-TYPE
    SYNTAX SEQUENCE OF Entry
    ACCESS not-accessible
    STATUS mandatory
    DESCRIPTION "The entries"
    ::= {{ testObjects {number} }}

entry OBJECT-TYPE
    SYNTAX Entry
    ACCESS not-accessible
    STATUS mandatory
    DESCRIPTION "An entry"
    INDEX {{ entryName }}
    ::= {{ entryTable 1 }}

Entry ::= SEQUENCE {{ entryName OCTET STRING, entryState TestState }}

entryName OBJECT-TYPE
    SYNTAX OCTET STRING (SIZE (0..255))
    ACCESS read-only
    STATUS mandatory
    DESCRIPTION "The name of an entry"
    ::= {{ entry 1 }}

entryState OBJECT-TYPE
    SYNTAX TestState
    ACCESS read-only
    STATUS mandatory
    DESCRIPTION "The state of an entry"
    ::= {{ entry 2 }}

entryChanged TRAP-TYPE
    ENTERPRISE testObjects
    VARIABLES {{ entryName, entryState }}
    DESCRIPTION "An entry changed its state"
    ::= {number}
END
"""


def _generated_code(directory: Path) -> dict[str, list[str]]:
    """The code of the compiled MIBs, without the comments, which tell e.g. the time"""
    return {
        path.name: [line for line in path.read_text().splitlines() if not line.startswith("#")]
        for path in directory.glob("*.py")
    }


def _compile_with_pysmi(
    mibname: MibName, content: str, source_dir: Path, destination_dir: Path
) -> None:
    """Compiles the MIB with pysmi alone, i.e. with a parser of its own remembering nothing"""
    PySmiCompiler(SmiV1CompatParser(), PySnmpCodeGen(), PyFileWriter(destination_dir)).add_sources(
        CallbackReader(lambda name, _context: content if name == mibname else "", None),
        FileReader(source_dir),
    ).compile(mibname, ignoreErrors=True, genTexts=True)


@pytest.mark.parametrize(
    "remember_parse_trees",
    [
        pytest.param(True, id="remembering the parse trees"),
        pytest.param(False, id="only sharing the parser"),
    ],
)
def test_a_compiler_generates_the_same_code_as_pysmi_after_compiling_other_mibs(
    tmp_path: Path, remember_parse_trees: bool
) -> None:
    # The compiler parses all MIBs with the same parser, which assumes that it keeps no state
    # between parses. It may also remember their parse trees, e.g. the one of TEST-BASE-MIB when
    # compiling FIRST-MIB, and hand out copies of them, which assumes that a parse tree depends only
    # on the MIB text and stays the same when copied. Updates of pysmi may break both.
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    (source_dir / "TEST-BASE-MIB.txt").write_text(_BASE_MIB)
    second_mib = MibName("SECOND-MIB")
    compiler = MibCompiler(remember_parse_trees=remember_parse_trees)
    compiler.compile(
        mibname=MibName("FIRST-MIB"),
        content=_mib_importing_base_mib(MibName("FIRST-MIB"), 1),
        source_dirs=[source_dir],
        search_dirs=[],
        destination_dir=tmp_path / "first",
    )

    compiler.compile(
        mibname=second_mib,
        content=_mib_importing_base_mib(second_mib, 2),
        source_dirs=[source_dir],
        search_dirs=[],
        destination_dir=tmp_path / "compiler",
    )
    _compile_with_pysmi(
        second_mib, _mib_importing_base_mib(second_mib, 2), source_dir, tmp_path / "pysmi"
    )

    pysmi_code = _generated_code(tmp_path / "pysmi")
    assert sorted(pysmi_code) == ["SECOND-MIB.py", "TEST-BASE-MIB.py"]
    assert _generated_code(tmp_path / "compiler") == pysmi_code
