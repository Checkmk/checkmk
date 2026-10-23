#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Compiles uploaded SNMP MIBs for the trap translation of the event console

This is kept separate from the trap handling in cmk.ec.snmp, so that users of the MIB
compilation do not need to load the SNMP engine.
"""

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Iterable, Mapping
from pathlib import Path

from pysmi.codegen.pysnmp import PySnmpCodeGen
from pysmi.compiler import MibCompiler, MibStatus
from pysmi.parser.smiv1compat import SmiV1CompatParser
from pysmi.reader.callback import CallbackReader
from pysmi.reader.localfile import FileReader
from pysmi.searcher.pyfile import PyFileSearcher
from pysmi.searcher.pypackage import PyPackageSearcher
from pysmi.searcher.stub import StubSearcher
from pysmi.writer.pyfile import PyFileWriter


def compile_mib(
    *,
    mibname: str,
    content: str,
    source_dirs: Iterable[Path],
    search_dirs: Iterable[Path],
    destination_dir: Path,
) -> Mapping[str, MibStatus]:
    # Compile the uploaded SNMP MIB but also resolving dependencies and compiling dependents
    return (  # type: ignore[no-any-return]
        MibCompiler(
            SmiV1CompatParser(),
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
