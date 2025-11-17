#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
from pathlib import Path

from pysmi.codegen.pysnmp import PySnmpCodeGen
from pysmi.compiler import MibCompiler, status_failed
from pysmi.parser.smiv1compat import SmiV1CompatParser
from pysmi.reader.callback import CallbackReader
from pysmi.reader.localfile import FileReader
from pysmi.searcher.pyfile import PyFileSearcher
from pysmi.searcher.pypackage import PyPackageSearcher
from pysmi.searcher.stub import StubSearcher
from pysmi.writer.pyfile import PyFileWriter

parser = argparse.ArgumentParser(prog="compile", description="Compiles MIBs for use with pysnmp")
parser.add_argument("destination_dir", type=Path)
parser.add_argument("source_files", nargs="+", type=str)

args = parser.parse_args()

args.destination_dir.mkdir(parents=True)

mibs = {Path(mib_path).stem: mib_path for mib_path in args.source_files}

search_dirs = {Path(mib_path).parent for mib_path in args.source_files}


def load_file(mib_name, _):
    if mib_name not in mibs:
        return None
    with open(mibs[mib_name]) as file:
        return file.read()


compiler = (
    MibCompiler(
        SmiV1CompatParser(),
        PySnmpCodeGen(),
        PyFileWriter(args.destination_dir).set_options(pyCompile=False),
    )
    .add_sources(
        # Provides the just uploaded MIB module
        CallbackReader(load_file, None),
        # Directories containing ASN1 MIB files which may be used for dependency resolution
        *[FileReader(search_dir) for search_dir in search_dirs],
    )
    .add_searchers(
        # check for additional already compiled MIBs
        *[PyFileSearcher(search_dir) for search_dir in search_dirs],
        # check compiled MIBs shipped with PySNMP
        *[PyPackageSearcher(package) for package in PySnmpCodeGen.defaultMibPackages],
        # never recompile MIBs with MACROs
        StubSearcher(*PySnmpCodeGen.baseMibs),
    )
)

for mib_name in mibs:
    results = compiler.compile(mib_name, ignoreErrors=False, genTexts=True)
    if status_failed in set(results.values()):
        raise Exception(f"Could not compile mib {mib_name}")
