#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Compiles uploaded SNMP MIBs for the trap translation of the event console

This is kept separate from the trap handling in cmk.ec.snmp, so that users of the MIB
compilation do not need to load the SNMP engine.
"""

# mypy: disable-error-code="no-untyped-call"

import copy
import functools
from collections.abc import Callable, Iterable
from pathlib import Path

from pysmi import compiler
from pysmi.codegen.pysnmp import PySnmpCodeGen
from pysmi.error import PySmiError
from pysmi.parser.smiv1compat import SmiV1CompatParser
from pysmi.reader.callback import CallbackReader
from pysmi.reader.localfile import FileReader
from pysmi.searcher.pyfile import PyFileSearcher
from pysmi.searcher.pypackage import PyPackageSearcher
from pysmi.searcher.stub import StubSearcher
from pysmi.writer.pyfile import PyFileWriter

from cmk.ec.mib_status import MibName, MibStatus


class _RememberingParser:
    """Parses every recently parsed MIB text only once, all of them with the same parser

    The parser keeps no state between parses, just like pysmi parses all MIBs of a compilation
    with the same parser. The code generators add pysmi's implicit imports to a parse tree, again
    with every compilation, so every parse returns a copy of the remembered one, which is about 25
    times faster than parsing. Without the copies the generated code would stay the same, as pysmi
    drops duplicate imports, but the remembered parse trees would keep growing.

    A parse tree takes more than twice the memory of its MIB text, and an upload may contain
    hundreds of MIBs, so only the recently parsed ones are remembered, many more than a compilation
    parses. The MIBs most compilations parse, like SNMPv2-SMI, stay among them.

    A MIB failing to parse fails in every compilation importing it, so the parser remembers the
    error, too. pysmi adds to the errors it gets, e.g. the name of the MIB, so every failing parse
    raises a copy of the remembered one.
    """

    @functools.cached_property
    def _parse(self) -> Callable[[str], list[object] | PySmiError]:
        # Built only for the first MIB to parse, as building the parser takes long.
        parser = SmiV1CompatParser()

        def parse(data: str) -> list[object] | PySmiError:
            try:
                return parser.parse(data)  # type: ignore[no-any-return]
            except PySmiError as e:
                # Neither the error of lark causing it nor the frames are of any use, but the
                # error keeps the state of the parser and the MIB text, and the frames keep the
                # ones calling them, with the whole state of pysmi's compilation.
                e.__cause__ = e.__context__ = None
                return e.with_traceback(None)

        return functools.lru_cache(maxsize=50)(parse)

    def parse(self, data: str) -> list[object]:
        parsed = self._parse(data)
        if isinstance(parsed, PySmiError):
            raise copy.copy(parsed)
        return copy.deepcopy(parsed)


class MibCompiler:
    """Compiles MIBs, all of them with the same parser, which remembers recent parse trees

    Building the parser takes most of the time of compiling a MIB, so the compiler builds it only
    once, when it parses the first MIB. Every compilation parses all MIBs the compiled one imports
    before it looks for compiled ones, mostly the same MIBs like SNMPv2-SMI, so the parser remembers
    their parse trees.

    Uploading zip files of real MIBs, from a few dozen up to Cisco's 1014, takes about 55% less time
    with the shared parser, and about 70% less with the remembered parse trees, too. Uploading MIBs
    one by one gains nothing, as every upload has a compiler of its own.
    """

    def __init__(self, *, remember_parse_trees: bool = True) -> None:
        # Switch remembering the parse trees off to check, e.g. after updating pysmi, that it still
        # results in the same compiled MIBs, and how much faster it is. The parser is still shared.
        self._parser: _RememberingParser | SmiV1CompatParser = (
            _RememberingParser() if remember_parse_trees else SmiV1CompatParser()
        )

    def compile(
        self,
        *,
        mibname: MibName,
        content: str,
        source_dirs: Iterable[Path],
        search_dirs: Iterable[Path],
        destination_dir: Path,
    ) -> dict[MibName, MibStatus]:
        # Compile the uploaded SNMP MIB but also resolving dependencies and compiling dependents
        statuses: dict[str, compiler.MibStatus] = (
            compiler.MibCompiler(
                self._parser,
                PySnmpCodeGen(),
                PyFileWriter(destination_dir),
            )
            .add_sources(
                # Provides the just uploaded MIB module
                CallbackReader(lambda name, _context: content if name == mibname else "", None),
                # Directories containing ASN1 MIB files which may be used for dependency resolution
                *[FileReader(path) for path in source_dirs],
            )
            .add_searchers(
                # check for additional already compiled MIBs
                *[PyFileSearcher(path) for path in search_dirs],
                # check compiled MIBs shipped with PySNMP
                *[PyPackageSearcher(package) for package in PySnmpCodeGen.defaultMibPackages],
                # never recompile MIBs with MACROs
                StubSearcher(*PySnmpCodeGen.baseMibs),
            )
        ).compile(mibname, ignoreErrors=True, genTexts=True)
        # Only a failed status has an error, which is a PySmiError.
        return {
            MibName(name): MibStatus(status=str(status), error=str(getattr(status, "error", "")))
            for name, status in statuses.items()
        }
