#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import csv
import json
import logging
import re
import warnings
from collections import defaultdict
from collections.abc import Iterable
from functools import cache
from itertools import chain
from pathlib import Path
from typing import NamedTuple, NewType

import isort
import pytest
from pipfile import Pipfile  # type: ignore[import]

from tests.testlib import repo_path
from tests.testlib.utils import branch_from_env, current_base_branch_name, is_enterprise_repo

IGNORED_LIBS = {
    "agent_receiver",
    "cmc_proto",
    "cmk",
    "livestatus",
    "mk_jolokia",
    "omdlib",
}  # our stuff
IGNORED_LIBS |= isort.stdlibs._all.stdlib  # builtin stuff
IGNORED_LIBS |= {"__future__"}  # other builtin stuff

BUILD_DIRS = {
    repo_path() / "agent-receiver/build",
    repo_path() / "packages/livestatus/build",
    repo_path() / "packages/neb/build",
    repo_path() / "packages/cmc/test",
    repo_path() / "omd" / "build",
}

PackageName = NewType("PackageName", str)  # Name in Pip(file)
ImportName = NewType("ImportName", str)  # Name in Source (import ...)


class NormalizedPackageName:
    def __init__(self, name: str) -> None:
        self.normalized = re.sub(r"[-_.]+", "-", name).lower()
        self.original = name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, NormalizedPackageName):
            return False
        return self.normalized == other.normalized

    def __hash__(self) -> int:
        return hash(self.normalized)


class Import(NamedTuple):
    name: ImportName
    paths: set[Path]

    @property
    def normalized_name(self) -> NormalizedPackageName:
        return NormalizedPackageName(self.name)


@pytest.fixture(name="loaded_pipfile")
def load_pipfile() -> Pipfile:
    return Pipfile.load(filename=str(repo_path() / "Pipfile"))


@pytest.mark.skipif(
    branch_from_env(env_var="GERRIT_BRANCH", fallback=current_base_branch_name) == "master",
    reason="pinning is only enforced in release branches",
)
def test_all_deployment_packages_pinned(loaded_pipfile: Pipfile) -> None:
    unpinned_packages = [f"'{n}'" for n, v in loaded_pipfile.data["default"].items() if v == "*"]
    assert not unpinned_packages, (
        "The following packages are not pinned: %s. "
        "For the sake of reproducibility, all deployment packages must be pinned to a version!"
    ) % " ,".join(unpinned_packages)


def test_pipfile_syntax(loaded_pipfile: Pipfile) -> None:
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


def iter_sourcefiles(basepath: Path) -> Iterable[Path]:
    """iter over the repo and return all source files

    this could have been a easy glob, but we do not care for hidden files here:
    https://bugs.python.org/issue26096"""
    for sub_path in basepath.iterdir():
        if sub_path in BUILD_DIRS:
            # Ignore build directories: those may not be aligned with the actual status in git
            # and for python sources they would enforce testing the same file twice...
            continue
        if sub_path.name.startswith("."):
            continue
        if sub_path.is_file() and sub_path.name.endswith(".py"):
            yield sub_path

        # Given the fact that the googletest directory contains a hash, it is
        # easier to filter out here than in prune_build_artifacts later.
        if sub_path.is_dir() and not sub_path.name.startswith("googletest-"):
            yield from iter_sourcefiles(sub_path)


def iter_relevant_files(basepath: Path) -> Iterable[Path]:
    exclusions = (
        basepath / "tests",
        basepath / "agents",  # There are so many optional imports...
        basepath / "agent-receiver",  # uses setup.py
        basepath / "enterprise/core/src/test",  # test files
        basepath / "omd/license_sources",  # update_licenses.py contains imports
    )

    for source_file_path in iter_sourcefiles(basepath):
        if any(source_file_path.is_relative_to(e) for e in exclusions):
            continue

        yield source_file_path


def imports_for_file(path: Path) -> set[ImportName]:
    def imports_for_node(node: ast.AST) -> Iterable[ImportName]:
        if isinstance(node, ast.Import):
            return {ImportName(n.name) for n in node.names}
        if isinstance(node, ast.ImportFrom) and node.level == 0:  # ignore relative imports
            assert node.module is not None
            return {ImportName(node.module)}
        return set()

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

    # We don't care about warnings from 3rd party packages
    with path.open("rb") as source_file, warnings.catch_warnings():
        try:
            # NOTE: In summary, this takes quite some time: parse: 5s, scan: 3.3s
            return {
                toplevel_importname(imp)
                for node in ast.walk(ast.parse(source_file.read(), str(path)))
                for imp in imports_for_node(node)
            }
        except SyntaxError as e:
            # We have various py2 scripts which raise SyntaxErrors.
            # e.g. agents/pugins/*_2.py also some google test stuff...
            # If we should check them they would fail the unittests,
            # providing a whitelist here is not really maintainable
            logging.getLogger().warning("Failed to read %r: %r", source_file, e)
            return set()


@cache
def get_imported_libs(repopath: Path) -> list[Import]:
    """Scan the repo for import statements, return only non local ones"""
    imports_to_files: dict[ImportName, set[Path]] = defaultdict(set)

    for path in iter_relevant_files(repopath):
        for imp in imports_for_file(path):
            imports_to_files[imp].add(path)

    return [
        Import(name, paths) for name, paths in imports_to_files.items() if name not in IGNORED_LIBS
    ]


def packagenames_to_libnames(
    repopath: Path,
) -> dict[NormalizedPackageName, list[NormalizedPackageName]]:
    """scan the site-packages folder for package infos"""

    def packagename_for(path: Path) -> NormalizedPackageName:
        """Check a METADATA file and return the PackageName"""
        with path.open() as metadata:
            for line in metadata.readlines():
                if line.startswith("Name:"):
                    return NormalizedPackageName(line[5:].strip())

        raise NotImplementedError("No 'Name:' in METADATA file")

    def importnames_for(
        packagename: NormalizedPackageName, path: Path
    ) -> list[NormalizedPackageName]:
        """return a list of importable libs which belong to the package"""
        top_level_txt_path = path.with_name("top_level.txt")
        if top_level_txt_path.is_file():
            with top_level_txt_path.open() as top_level_file:
                return [
                    NormalizedPackageName(x.strip())
                    for x in top_level_file.readlines()
                    if x.strip()
                ]
        record_path = path.with_name("RECORD")
        if record_path.is_file():
            names = set()
            # https://packaging.python.org/en/latest/specifications/recording-installed-packages/#the-record-file
            with record_path.open() as record_file:
                reader = csv.reader(record_file, delimiter=",", quotechar='"')
                for file_path_str, _file_hash, _file_size in reader:
                    first_part = Path(file_path_str).parts[0]
                    if (
                        first_part == "/"
                        or first_part.endswith(".dist-info")
                        or first_part == ".."
                        or first_part == "__pycache__"
                    ):
                        continue
                    if first_part.endswith(".py"):
                        names.add(NormalizedPackageName(first_part.removesuffix(".py")))
                    else:
                        names.add(NormalizedPackageName(first_part))
            return list(names)

        return [packagename]

    return {
        packagename: importnames_for(packagename, metadata_path)
        for metadata_path in repopath.glob(".venv/lib/python*/site-packages/*.dist-info/METADATA")
        for packagename in [packagename_for(metadata_path)]
    }


@cache
def get_pipfile_libs(repopath: Path) -> dict[PackageName, list[NormalizedPackageName]]:
    """Collect info from Pipfile with additions from site-packages

    The dict has as key the Pipfile package name and as value a list with all import names
    from top_level.txt

    packagenames may differ from the import names,
    also the site-package folder can be different."""
    site_packages = packagenames_to_libnames(repopath)
    pipfile_to_libs: dict[PackageName, list[NormalizedPackageName]] = {}

    parsed_pipfile = Pipfile.load(filename=repopath / "Pipfile")
    for name, details in parsed_pipfile.data["default"].items():
        if "path" in details:
            # Ignoring some of our own sub-packages e.g. agent-receiver
            continue

        if (normalized_name := NormalizedPackageName(name)) in site_packages:
            pipfile_to_libs[name] = site_packages[normalized_name]
            continue

        raise NotImplementedError("Could not find package %s in site_packages" % name)
    return pipfile_to_libs


def get_unused_dependencies() -> Iterable[PackageName]:
    """Iterate over declared dependencies which are not imported"""
    imported_libs = {d.normalized_name for d in get_imported_libs(repo_path())}
    pipfile_libs = get_pipfile_libs(repo_path())
    for packagename, import_names in pipfile_libs.items():
        if set(import_names).isdisjoint(imported_libs):
            yield packagename


def get_undeclared_dependencies() -> Iterable[Import]:
    """Iterate over imported dependencies which could not be found in the Pipfile"""
    imported_libs = get_imported_libs(repo_path())
    pipfile_libs = get_pipfile_libs(repo_path())
    declared_libs = set(chain.from_iterable(pipfile_libs.values()))

    yield from (
        imported_lib
        for imported_lib in imported_libs
        if imported_lib.normalized_name not in declared_libs
    )


CEE_UNUSED_PACKAGES = [
    "attrs",
    "bcrypt",
    "cachetools",
    "certifi",
    "cffi",
    "chardet",
    "click",
    "cython",
    "defusedxml",
    "docutils",
    "grpcio",
    "gunicorn",
    "idna",
    "importlib-metadata",
    "itsdangerous",
    "jmespath",
    "jsonschema",  # TODO: move to dev-deps
    "markupsafe",
    "more-itertools",
    "multidict",
    "mypy-extensions",  # TODO: Can that be removed? looks like it
    "ordered-set",
    "pbr",
    "ply",
    "psycopg2-binary",
    "pyasn1-modules",
    "pycparser",
    "pykerberos",
    "pymssql",
    "pymysql",
    "pynacl",
    "pyprof2calltree",
    "pyrsistent",
    "requests-kerberos",
    "requests-toolbelt",
    "s3transfer",
    "setuptools-scm",
    "snmpsim",
    "tenacity",
    "uvicorn",  # TODO: move to agent-receiver/setup.py
    "websocket-client",
    "wrapt",
    "yarl",
    "zipp",
]


def test_dependencies_are_used() -> None:
    known_unused_packages = set(CEE_UNUSED_PACKAGES)
    if not is_enterprise_repo():
        known_unused_packages.update(("PyPDF3", "numpy", "roman"))

    unused_dependencies = set(get_unused_dependencies())

    assert (
        unused_dependencies >= known_unused_packages
    ), "The exceptionlist is outdated, these are the 'offenders':" + str(
        known_unused_packages - unused_dependencies
    )

    unused_dependencies -= known_unused_packages
    assert (
        unused_dependencies == set()
    ), f"There are dependencies that are declared in the Pipfile but not used: {unused_dependencies}"


def test_dependencies_are_declared() -> None:
    """Test for unknown imports which could not be mapped to the Pipfile

    mostly optional imports and OMD-only shiped packages."""
    undeclared_dependencies = list(get_undeclared_dependencies())
    undeclared_dependencies_str = {d.name for d in undeclared_dependencies}
    known_undeclared_dependencies = {
        "matplotlib",  # Disabled debug code in enterprise/cmk/gui/cee/sla.py
        "mpld3",  # Disabled debug code in enterprise/cmk/gui/cee/sla.py
        "netsnmp",  # We ship it with omd/packages
        "pymongo",  # Optional except ImportError...
        "pytest",  # In __main__ guarded section in cmk/special_agents/utils/misc.py
        "tinkerforge",  # agents/plugins/mk_tinkerforge.py has its own install routine
        "_typeshed",  # used by mypy within typing.TYPE_CHECKING
        "docker",  # optional
    }
    assert (
        undeclared_dependencies_str >= known_undeclared_dependencies
    ), "The exceptionlist is outdated, these are the 'offenders':" + str(
        known_undeclared_dependencies - undeclared_dependencies_str
    )
    undeclared_dependencies_str -= known_undeclared_dependencies
    assert (
        undeclared_dependencies_str == set()
    ), "There are imports that are not declared in the Pipfile:\n    " + "\n    ".join(
        str(d) for d in undeclared_dependencies if d.name not in known_undeclared_dependencies
    )


def _get_lockfile_hash(lockfile_path: Path) -> str:
    lockfile = json.loads(lockfile_path.read_text())
    if "_meta" in lockfile and hasattr(lockfile, "keys"):
        return lockfile["_meta"].get("hash", {}).get("sha256")
    return ""


def test_pipfile_lock_up_to_date(loaded_pipfile: Pipfile) -> None:
    lockfile_hash = _get_lockfile_hash(repo_path() / "Pipfile.lock")
    assert loaded_pipfile.hash == lockfile_hash
