#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import logging
import typing as t
import warnings
from functools import lru_cache
from itertools import chain, permutations
from pathlib import Path

import isort
import pytest
from pipfile import Pipfile  # type: ignore[import]

from tests.testlib import repo_path
from tests.testlib.utils import is_enterprise_repo

IGNORED_LIBS = set(["cmk", "livestatus", "mk_jolokia"])  # our stuff
IGNORED_LIBS |= isort.stdlibs._all.stdlib  # builtin stuff
IGNORED_LIBS |= set(["__future__", "typing_extensions"])  # other builtin stuff

PACKAGE_REPLACEMENTS = ".-_"


PackageName = t.NewType("PackageName", str)  # Name in Pip(file)
ImportName = t.NewType("ImportName", str)  # Name in Source (import ...)


@pytest.fixture(name="loaded_pipfile")
def load_pipfile():
    return Pipfile.load(filename=repo_path() + "/Pipfile")


def test_all_deployment_packages_pinned(loaded_pipfile) -> None:
    unpinned_packages = [f"'{n}'" for n, v in loaded_pipfile.data["default"].items() if v == "*"]
    assert not unpinned_packages, (
        "The following packages are not pinned: %s. "
        "For the sake of reproducibility, all deployment packages must be pinned to a version!"
    ) % " ,".join(unpinned_packages)


def test_pipfile_syntax(loaded_pipfile) -> None:
    # pipenv is currently (e.g. in version 2022.1.8) accepting false Pipfile syntax like:
    # pysmb = "1.2"
    # So it will not throw an error or warning if the comparision operator is missing.
    # Remove this test as soon pipenv is getting smarter..
    packages_with_faulty_syntax = []

    for type_ in ("default", "develop"):
        packages_with_faulty_syntax.extend(
            [
                (n, s)
                for n, s in loaded_pipfile.data[type_].items()
                if isinstance(s, str) and s[0].isnumeric()
            ]
        )
    assert not any(packages_with_faulty_syntax), (
        "The following packages seem to have a faulty Pipfile syntax: %s. "
        "Assuming you forgot to add a comparision operator, like '<', '==' etc. '"
        "Have a look at: https://github.com/pypa/pipfile"
        % ",".join([f"Package {n} with Version: {v}" for n, v in packages_with_faulty_syntax])
    )


def iter_sourcefiles(basepath: Path) -> t.Iterable[Path]:
    """iter over the repo and return all source files

    this could have been a easy glob, but we do not care for hidden files here:
    https://bugs.python.org/issue26096"""
    for sub_path in basepath.iterdir():
        if sub_path.name.startswith("."):
            continue
        if sub_path.is_file() and sub_path.name.endswith(".py"):
            yield sub_path
        if sub_path.is_dir():
            yield from iter_sourcefiles(sub_path)


def prune_build_artifacts(basepath: Path, paths: t.Iterable[Path]) -> t.Iterable[Path]:
    # TODO: Change to p.is_relative_to() with Python 3.9
    def is_relative_to(p: Path, base_dir: Path) -> bool:
        try:
            p.relative_to(base_dir)
            return True
        except ValueError:
            return False

    yield from (p for p in paths if not is_relative_to(p, basepath.joinpath("omd/build")))


def scan_for_imports(root_node: ast.Module) -> t.Iterable[ImportName]:
    """walk the tree and yield all imported packages"""
    for node in ast.walk(root_node):
        if isinstance(node, ast.Import):
            yield from (ImportName(n.name) for n in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0:
                # relative imports
                continue
            assert node.module is not None
            yield ImportName(node.module)


def toplevel_importname(name: ImportName) -> ImportName:
    """return top level import

    >>> toplevel_importname("foo")
    'foo'
    >>> toplevel_importname("foo.bar")
    'foo'
    >>> toplevel_importname("foo.bar.baz")
    'foo'
    """
    try:
        top_level_lib, _sub_libs = name.split(".", maxsplit=1)
        return ImportName(top_level_lib)
    except ValueError:
        return name


def prune_imports(import_set: t.Set[ImportName]) -> t.Set[ImportName]:
    """throw out all our own libraries and use only top-level names"""
    return {
        top_level_lib
        for import_name in import_set
        for top_level_lib in [toplevel_importname(import_name)]
        if top_level_lib not in IGNORED_LIBS
    }


@lru_cache(maxsize=None)
def get_imported_libs(repopath: Path) -> t.Set[ImportName]:
    """Scan the repo for import statements, return only non local ones"""
    logger = logging.getLogger()

    imports: t.Set[ImportName] = set()
    for source_path in prune_build_artifacts(repopath, iter_sourcefiles(repopath)):
        if source_path.name.startswith("."):
            continue

        # We don't care about warnings from 3rd party packages
        with source_path.open("rb") as source_file, warnings.catch_warnings():
            try:
                root = ast.parse(source_file.read(), source_path)  # type: ignore
                imports.update(scan_for_imports(root))
            except SyntaxError as e:
                # We have various py2 scripts which raise SyntaxErrors.
                # e.g. agents/pugins/*_2.py also some google test stuff...
                # If we should check them they would fail the unittests,
                # providing a whitelist here is not really maintainable
                logger.warning("Failed to read %r: %r", source_file, e)
                continue

    return prune_imports(imports)


def packagename_for(path: Path) -> PackageName:
    """Check a METADATA file and return the PackageName"""
    with path.open() as metadata:
        for line in metadata.readlines():
            if line.startswith("Name:"):
                return PackageName(line[5:].strip())

    raise NotImplementedError("No 'Name:' in METADATA file")


def importnames_for(packagename: PackageName, path: Path) -> t.List[ImportName]:
    """return a list of importable libs which belong to the package"""
    top_level_txt_path = path.with_name("top_level.txt")
    if not top_level_txt_path.is_file():
        return [ImportName(packagename)]

    with top_level_txt_path.open() as top_level_file:
        return [ImportName(x.strip()) for x in top_level_file.readlines() if x.strip()]


def packagenames_to_libnames(repopath: Path) -> t.Dict[PackageName, t.List[ImportName]]:
    """scan the site-packages folder for package infos"""
    return {
        packagename: importnames_for(packagename, metadata_path)
        for metadata_path in repopath.glob(".venv/lib/python*/site-packages/*.dist-info/METADATA")
        for packagename in [packagename_for(metadata_path)]
    }


@lru_cache(maxsize=None)
def get_pipfile_libs(repopath: Path) -> t.Dict[PackageName, t.List[ImportName]]:
    """Collect info from Pipfile with additions from site-packages

    The dict has as key the Pipfile package name and as value a list with all import names
    from top_level.txt

    packagenames may differ from the import names,
    also the site-package folder can be different."""
    site_packages = packagenames_to_libnames(repopath)
    pipfile_to_libs: t.Dict[PackageName, t.List[ImportName]] = {}

    parsed_pipfile = Pipfile.load(filename=repopath / "Pipfile")
    for name, details in parsed_pipfile.data["default"].items():
        if "path" in details:
            # Ignoring some of our own sub-packages e.g. agent-receiver
            continue

        if name in site_packages:
            pipfile_to_libs[name] = site_packages[name]
            continue

        for char_to_be_replaced, replacement in permutations(PACKAGE_REPLACEMENTS, 2):
            fuzzy_name = PackageName(name.replace(char_to_be_replaced, replacement))
            if fuzzy_name in site_packages:
                pipfile_to_libs[name] = site_packages[fuzzy_name]
                break
        else:
            raise NotImplementedError("Could not find package %s in site_packages" % name)
    return pipfile_to_libs


def get_unused_dependencies() -> t.Iterable[PackageName]:
    """Iterate over declared dependencies which are not imported"""
    imported_libs = get_imported_libs(Path(repo_path()))
    pipfile_libs = get_pipfile_libs(Path(repo_path()))
    for packagename, import_names in pipfile_libs.items():
        if set(import_names).isdisjoint(imported_libs):
            yield packagename


def get_undeclared_dependencies() -> t.Iterable[ImportName]:
    """Iterate over imported dependencies which could not be found in the Pipfile"""
    imported_libs = get_imported_libs(Path(repo_path()) / "cmk")
    pipfile_libs = get_pipfile_libs(Path(repo_path()))
    declared_libs = set(chain.from_iterable(pipfile_libs.values()))

    yield from imported_libs - declared_libs


CEE_UNUSED_PACKAGES = [
    "Cython",
    "Flask",
    "MarkupSafe",
    "PyJWT",
    "PyMySQL",
    "PyNaCl",
    "attrs",
    "bcrypt",
    "cachetools",
    "certifi",
    "cffi",
    "chardet",
    "click",
    "defusedxml",
    "docutils",
    "exchangelib",  # TODO: Clean this up once the call sites have been added
    "gunicorn",
    "idna",
    "importlib_metadata",
    "itsdangerous",
    "jmespath",
    "jsonschema",
    "more-itertools",
    "multidict",
    "ordered-set",
    "pbr",
    "ply",
    "psycopg2-binary",
    "pyasn1-modules",
    "pycparser",
    "pykerberos",
    "pymssql",
    "pyprof2calltree",
    "pyrsistent",
    "requests-kerberos",
    "requests-toolbelt",
    "rsa",
    "s3transfer",
    "semver",
    "setuptools-git",
    "setuptools_scm",
    "snmpsim",
    "tenacity",
    "typing_extensions",
    "uvicorn",
    "websocket_client",
    "wrapt",
    "yarl",
    "zipp",
]


@pytest.mark.skipif(not is_enterprise_repo(), reason="Test is only for CEE")
def test_dependencies_are_used_cee() -> None:
    assert sorted(get_unused_dependencies()) == CEE_UNUSED_PACKAGES


@pytest.mark.skipif(is_enterprise_repo(), reason="Test is only for CRE")
def test_dependencies_are_used_cre() -> None:
    unused_packages = CEE_UNUSED_PACKAGES + [
        "PyPDF3",  # is only used in CEE
        "numpy",  # is only used in CEE
        "roman",  # is only used in CEE
    ]
    assert sorted(get_unused_dependencies()) == sorted(unused_packages)


def test_dependencies_are_declared() -> None:
    """Test for unknown imports which could not be mapped to the Pipfile

    mostly optional imports and OMD-only shiped packages.
    issubset() is used since the dependencies vary between the versions."""

    assert set(get_undeclared_dependencies()).issubset(
        set(
            [
                "NaElement",  # Optional import cmk/special_agents/agent_netapp.py
                "NaServer",  # Optional import cmk/special_agents/agent_netapp.py
                "lxml",  # Optional import cmk/special_agents/agent_netapp.py
                "matplotlib",  # Disabled debug code in enterprise/cmk/gui/cee/sla.py
                "mock",  # Mixin prod and test code... cmk/gui/plugins/openapi/restful_objects/constructors.py
                "mpld3",  # Disabled debug code in enterprise/cmk/gui/cee/sla.py
                "netsnmp",  # We ship it with omd/packages
                "pymongo",  # Optional except ImportError...
                "pytest",  # In __main__ guarded section in cmk/special_agents/utils/misc.py
                "tinkerforge",  # agents/plugins/mk_tinkerforge.py has its own install routine
            ]
        )
    )


def _get_lockfile_hash(lockfile_path) -> str:
    lockfile = json.loads(lockfile_path.read_text())
    if "_meta" in lockfile and hasattr(lockfile, "keys"):
        return lockfile["_meta"].get("hash", {}).get("sha256")
    return ""


def test_pipfile_lock_up_to_date(loaded_pipfile):
    lockfile_hash = _get_lockfile_hash(Path(repo_path(), "Pipfile.lock"))
    assert loaded_pipfile.hash == lockfile_hash
