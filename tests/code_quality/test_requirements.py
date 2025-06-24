#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import ast
import csv
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

from tests.testlib.common.repo import (
    branch_from_env,
    current_base_branch_name,
    is_enterprise_repo,
    repo_path,
)

import requirements

IGNORED_LIBS = {
    "agent_receiver",
    "cmc_proto",
    "cmk",
    "livestatus",
    "mk_jolokia",
    "omdlib",
    "cmk_graphing",
}  # our stuff
IGNORED_LIBS |= isort.stdlibs._all.stdlib  # builtin stuff
IGNORED_LIBS |= {"__future__"}  # other builtin stuff

# currently runtime requirements are stored in multiple files
DEV_REQ_FILES_LIST = [repo_path() / "dev-requirements.in"]
RUNTIME_REQ_FILES_LIST = (
    [
        repo_path() / "cmk/requirements.in",
    ]
    + list((repo_path() / "packages").glob("*/requirements.in"))
    + list((repo_path() / "non-free" / "packages").glob("*/requirements.in"))
)

REQUIREMENTS_FILES = {
    "dev": DEV_REQ_FILES_LIST,
    "runtime": RUNTIME_REQ_FILES_LIST,
    "all": DEV_REQ_FILES_LIST + RUNTIME_REQ_FILES_LIST,
}

PackageName = NewType("PackageName", str)  # Name in requirements file
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


def parse_requirements_file(file_path: Path) -> dict[str, str]:
    """Parse a requirements file and return a dictionary of package names and their versions."""
    requirements_dict: dict[str, str] = {}
    with open(file_path) as fd:
        req = requirements.parse(fd)
        for r in req:
            if len(r.specs) != 0:
                # r.spec is a list of tuples (operator, version)
                version = r.specs[0][1]
            else:
                version = ""
            if r.name is not None:
                requirements_dict[r.name] = version
    return requirements_dict


def load_requirements(requirements_type: str) -> dict[str, str]:
    """Load requirements of the given type (dev, runtime, all) and return
    a dictionary of package names and their versions."""
    requirements_dict = {}
    file_path_list = REQUIREMENTS_FILES[requirements_type]
    for requirements_file_path in file_path_list:
        requirements_dict.update(parse_requirements_file(requirements_file_path))
    return requirements_dict


@pytest.fixture(name="loaded_requirements")
def loaded_requirements():
    return load_requirements("all")


@pytest.mark.skipif(
    branch_from_env(env_var="GERRIT_BRANCH", fallback=current_base_branch_name) == "master",
    reason="pinning is only enforced in release branches",
)
def test_all_packages_pinned(loaded_requirements: dict[str, str]) -> None:
    # Test implements process as described in:
    # https://wiki.lan.tribe29.com/books/how-to/page/creating-a-new-beta-branch#bkmrk-pin-dev-dependencies
    unpinned_packages = [req for req in loaded_requirements.keys() if not loaded_requirements[req]]
    assert not unpinned_packages, (
        "The following packages are not pinned: %s. "
        "For the sake of reproducibility, all packages must be pinned to a version!"
    ) % " ,".join(unpinned_packages)


def is_python_file(file_path: Path) -> bool:
    """Checks if a file is a python file by checking the file extension or the shebang line"""
    shebang_pattern = re.compile(r"^#!.*python3$")
    if file_path.suffix == ".py":
        return True
    with open(file_path, encoding="utf-8", errors="replace") as f:
        first_line = f.readline().rstrip("\n")
    return bool(shebang_pattern.match(first_line))


def iter_sourcefiles(basepath: Path) -> Iterable[Path]:
    """iter over the repo and return all source files

    this could have been a easy glob, but we do not care for hidden files here:
    https://bugs.python.org/issue26096"""
    for sub_path in basepath.iterdir():
        # TODO: remove after CMK-20852 is finished
        if sub_path == repo_path() / "packages/cmk-shared-typing":
            continue
        # the following paths may contain python files and should not be scanned
        if sub_path.name == "container_shadow_workspace_local":
            continue
        # TODO: We need to find a better way for the bazel-* folders created by bazel
        if "bazel-" in sub_path.name:
            continue
        if sub_path.name == "node_modules":
            continue
        if sub_path.name.startswith("."):
            continue
        if sub_path.is_file() and is_python_file(sub_path):
            yield sub_path

        # Given the fact that the googletest directory contains a hash, it is
        # easier to filter out here than in prune_build_artifacts later.
        if sub_path.is_dir() and not sub_path.name.startswith("googletest-"):
            yield from iter_sourcefiles(sub_path)


def iter_relevant_files(basepath: Path) -> Iterable[Path]:
    exclusions = [
        basepath / "agents",  # There are so many optional imports...
        basepath / "node_modules",
        basepath / "omd/license_sources",  # update_licenses.py contains imports
        basepath / "tests",
    ]
    if is_enterprise_repo():
        # Not deployed with the Checkmk site Python environment, but required by tests in the
        # cmk-update-agent package
        exclusions.append(basepath / "non-free/packages/cmk-update-agent")

    exclusions_from_exclusions = (basepath / "agents/plugins/mk_jolokia.py",)

    for source_file_path in iter_sourcefiles(basepath):
        if (
            any(source_file_path.resolve().is_relative_to(e.resolve()) for e in exclusions)
            and source_file_path not in exclusions_from_exclusions
        ):
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
                    if first_part in {"/", "..", "__pycache__"} or first_part.endswith(
                        ".dist-info"
                    ):
                        continue
                    if first_part.endswith(".py") or first_part.endswith(".so"):
                        names.add(
                            NormalizedPackageName(
                                first_part.removesuffix(".py").removesuffix(".so")
                            )
                        )
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
def get_requirements_libs(
    repopath: Path,
) -> dict[PackageName, list[NormalizedPackageName]]:
    """Collect info from requirement files with additions from site-packages

    The dict has as key the requirement file package name and as value a list with all import names
    from top_level.txt

    packagenames may differ from the import names,
    also the site-package folder can be different."""
    site_packages = packagenames_to_libnames(repopath)
    requirements_to_libs: dict[PackageName, list[NormalizedPackageName]] = {}

    parsed_req = load_requirements("runtime")
    for req in parsed_req.keys():
        if (normalized_name := NormalizedPackageName(req)) in site_packages:
            requirements_to_libs[PackageName(req)] = site_packages[normalized_name]
            continue

        raise NotImplementedError("Could not find package %s in site_packages" % req)
    return requirements_to_libs


def get_unused_dependencies() -> Iterable[PackageName]:
    """Iterate over declared dependencies which are not imported"""
    imported_libs = {d.normalized_name for d in get_imported_libs(repo_path())}
    requirements_libs = get_requirements_libs(repo_path())
    for packagename, import_names in requirements_libs.items():
        if set(import_names).isdisjoint(imported_libs):
            yield packagename


def get_undeclared_dependencies() -> Iterable[Import]:
    """Iterate over imported dependencies which could not be found in the requirement files"""
    imported_libs = get_imported_libs(repo_path())
    requirements_libs = get_requirements_libs(repo_path())
    declared_libs = set(chain.from_iterable(requirements_libs.values()))

    yield from (
        imported_lib
        for imported_lib in imported_libs
        if imported_lib.normalized_name not in declared_libs
    )


CEE_UNUSED_PACKAGES = [
    "setuptools-scm",
    "snmpsim-lextudio",
    "python-multipart",  # needed by fastapi
    "pytest-xdist",  # pytest distributed testing
    # stub packages
    "types-python-dateutil",
    "types-markdown",
    "types-pika-ts",
]


def test_dependencies_are_used() -> None:
    known_unused_packages = set(CEE_UNUSED_PACKAGES)
    known_unused_packages.add("setuptools")  # pinned transitive dependency
    # used for deploying the agent receiver, but in a bash script, so undetectable by this test
    known_unused_packages.add("gunicorn")

    if not is_enterprise_repo():
        known_unused_packages.update(("PyPDF", "numpy", "roman"))

    unused_dependencies = set(get_unused_dependencies())

    assert unused_dependencies >= known_unused_packages, (
        "The exceptionlist is outdated, these are the 'offenders':"
        + str(known_unused_packages - unused_dependencies)
    )

    unused_dependencies -= known_unused_packages
    assert unused_dependencies == set(), (
        f"There are dependencies that are declared in the requirements files but not used: {unused_dependencies}"
    )


def test_dependencies_are_declared() -> None:
    """Test for unknown imports which could not be mapped to the requirements files

    mostly optional imports and OMD-only shiped packages."""
    undeclared_dependencies = list(get_undeclared_dependencies())
    undeclared_dependencies_str = {d.name for d in undeclared_dependencies}
    known_undeclared_dependencies = {
        "buildscripts",  # used in build helper scripts in buildscripts/scripts
        "netsnmp",  # We ship it with omd/packages
        "pymongo",  # Optional except ImportError...
        "tinkerforge",  # agents/plugins/mk_tinkerforge.py has its own install routine
        "mypy_boto3_logs",  # used by mypy within typing.TYPE_CHECKING
        "docker",  # optional
        "msrest",  # used in publish_cloud_images.py and not in the product
        "pip",  # is included by default in python
        "rrdtool",  # is built as part of the project
        # the following packages must be installed additionally by the user
        "ibm_db",  # active_checks/check_sql
        "ibm_db_dbi",  # active_checks/check_sql
        "sqlanydb",  # active_checks/check_sql
        "libcst",  # doc/treasures/migration_helpers
        "tests",  # buildscripts/scripts/assert_build_artifactsa.py and buildscripts/scripts/lib/registry.py
    }

    assert undeclared_dependencies_str >= known_undeclared_dependencies, (
        "The exceptionlist is outdated, these are the 'offenders':"
        + str(known_undeclared_dependencies - undeclared_dependencies_str)
    )
    undeclared_dependencies_str -= known_undeclared_dependencies
    assert undeclared_dependencies_str == set(), (
        "There are imports that are not declared in the requirements files:\n    "
        + "\n    ".join(
            str(d) for d in undeclared_dependencies if d.name not in known_undeclared_dependencies
        )
    )


def test_runtime_requirements_are_a_strict_subset_of_all_requirements() -> None:
    reqs = frozenset(parse_requirements_file(repo_path() / "requirements.txt").items())
    runtime = frozenset(parse_requirements_file(repo_path() / "runtime-requirements.txt").items())
    assert runtime.issubset(reqs), (
        f"The following dependencies are incorrectly pinned: {dict(runtime - reqs)}"
    )


def test_constraints() -> None:
    """Make sure all constraints have a ticket to be removed"""
    offenses = []
    with (repo_path() / "constraints.txt").open() as constraint_file:
        req = requirements.parse(constraint_file)
        for r in req:
            if re.search(r"\bCMK-\d{5}\b", r.line):
                continue
            offenses.append(f"Constraint for {r.name} has no ticket to be removed")
    assert not offenses, "\n".join(offenses)
