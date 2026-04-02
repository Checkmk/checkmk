#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="unreachable"


import ast
import csv
import re
import subprocess
import warnings
from collections import defaultdict
from collections.abc import Iterable, Mapping
from functools import cache
from itertools import chain
from pathlib import Path
from typing import NamedTuple, NewType

import isort
import pytest
import requirements

from tests.testlib.common.repo import (
    is_pro_repo,
    repo_path,
)

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


def requirements_files() -> dict[str, list[Path]]:
    dev_req_files_list = (
        [
            repo_path() / "tests/dev-requirements.in",
        ]
        + list((repo_path() / "packages").glob("*/dev-requirements.in"))
        + list((repo_path() / "non-free" / "packages").glob("*/dev-requirements.in"))
    )

    runtime_req_files_list = (
        [
            repo_path() / "cmk/requirements.in",
            repo_path() / "scripts/requirements.in",
        ]
        + list((repo_path() / "packages").glob("*/requirements.in"))
        + list((repo_path() / "packages").glob("*/requirements.in-*"))
        + list((repo_path() / "non-free" / "packages").glob("*/requirements.in"))
    )

    return {
        "dev": dev_req_files_list,
        "runtime": runtime_req_files_list,
        "all": dev_req_files_list + runtime_req_files_list,
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

    def __repr__(self) -> str:
        return f"NormalizedPackageName({self.original!r})"


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
    file_path_list = requirements_files()[requirements_type]
    for requirements_file_path in file_path_list:
        requirements_dict.update(parse_requirements_file(requirements_file_path))
    return requirements_dict


@pytest.fixture(name="loaded_requirements")
def loaded_requirements():
    return load_requirements("all")


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
        # the following paths may contain python files and should not be scanned
        if sub_path.name == "container_shadow_workspace_local":
            continue
        # TODO: We need to find a better way for the bazel-* folders created by bazel
        if "bazel-" in sub_path.name:
            continue
        if sub_path.name == "external":  # Bazel external dependencies
            continue
        if sub_path.name == "node_modules":
            continue
        if sub_path.name == "tests":
            continue
        if "testlib" in sub_path.name:
            continue
        if "test_lib" in sub_path.name:
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
        basepath / "packages/cmk-shared-typing/utils",  # only build time dependencies
    ]
    if is_pro_repo():
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
        # NOTE: In summary, this takes quite some time: parse: 5s, scan: 3.3s
        return {
            toplevel_importname(imp)
            for node in ast.walk(ast.parse(source_file.read(), str(path)))
            for imp in imports_for_node(node)
        }


@cache
def get_imported_libs(repopath: Path) -> list[Import]:
    """Scan the repo for import statements, return only non local ones"""
    imports_to_files: dict[ImportName, set[Path]] = defaultdict(set)

    for path in iter_relevant_files(repopath):
        for imp in imports_for_file(path):
            imports_to_files[imp].add(path.relative_to(repopath))

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


def find_packages() -> Iterable[object]:
    """Find all package paths in the repo"""
    packages_paths = ["packages"]
    if is_pro_repo():
        packages_paths.append("non-free/packages")

    for packages_path in packages_paths:
        for package_path in (repo_path() / packages_path).iterdir():
            if not package_path.is_dir():
                continue
            if not list(package_path.glob("requirements.in*")):
                # No python package
                continue
            yield pytest.param(package_path, id=package_path.relative_to(repo_path()).as_posix())


@pytest.mark.parametrize("package_path", find_packages())
def test_package_declared_all_python_deps(package_path: Path) -> None:
    if package_path.relative_to(repo_path()).as_posix() == "non-free/packages/cmk-core-helpers":
        pytest.skip("cmk-core-helpers needs netsnmp which does not come from pypi")
    venv_libs = get_requirements_libs(repo_path())
    imported_libs = {d.normalized_name for d in get_imported_libs(package_path)}
    required_packages = {
        p for file in package_path.glob("requirements.in*") for p in parse_requirements_file(file)
    }

    required_import_names = chain.from_iterable(
        import_names
        for packagename, import_names in venv_libs.items()
        if packagename in required_packages
    )
    unknown_but_imported_libs = imported_libs - set(required_import_names)
    assert not unknown_but_imported_libs, (
        f"These libs are imported but not part of the requirements: {sorted(u.normalized for u in unknown_but_imported_libs)} in {package_path.relative_to(repo_path()).as_posix()}"
    )


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
    # buildtime-dependencies required in cmk-shared-typing
    "black",
    "datamodel_code_generator",
    # ----
    "setuptools-scm",
    "snmpsim",
    "python-multipart",  # needed by fastapi
]

KNOWN_UNDECLARED_DEPENDENCIES = {
    ImportName("buildscripts"): {
        Path("buildscripts/scripts/assert_build_artifacts.py"),
        Path("buildscripts/scripts/get_distros.py"),
        Path("buildscripts/scripts/build-cmk-container.py"),
        Path("buildscripts/scripts/unpublish-container-image.py"),
    },
    ImportName("tests"): {
        Path("buildscripts/scripts/assert_build_artifacts.py"),
        Path("buildscripts/scripts/lib/registry.py"),
    },
    ImportName("pip"): {  # is included by default in python
        Path("omd/packages/Python/pip")
    },
    ImportName("ibm_db"): {Path("cmk/plugins/sql/active_check/check_sql.py")},
    ImportName("sqlanydb"): {Path("cmk/plugins/sql/active_check/check_sql.py")},
    ImportName("ibm_db_dbi"): {Path("cmk/plugins/sql/active_check/check_sql.py")},
    ImportName("tinkerforge"): {Path("cmk/plugins/tinkerforge/special_agent/agent_tinkerforge.py")},
    ImportName("rados"): {Path("cmk/plugins/ceph/agents/mk_ceph.py")},
    ImportName("netsnmp"): {  # We ship it with omd/packages
        Path("non-free/packages/cmk-core-helpers/cmk/inline_snmp/inline.py")
    },
    ImportName("rrdtool"): {  # is built as part of the project
        Path("bin/cmk-create-rrd.py"),
        Path("cmk/rrd/convert_rrds/__main__.py"),
    },
    ImportName("docker"): (
        Path("buildscripts/docker_image_aliases/register.py"),
        Path("buildscripts/scripts/lib/registry.py"),
        Path("buildscripts/scripts/build-cmk-container.py"),
    ),
    ImportName("scripts"): {
        Path("scripts/gerrit_api/scrape_werks.py"),
        Path("scripts/gerrit_api/werks.py"),
    },
    ImportName("bep_to_junit"): {
        Path("buildscripts/scripts/bep_to_junit/__main__.py"),
    },
}

KNOWN_UNDECLAREABLE_DEPENDENCIES = {
    # https://github.com/python/typeshed/tree/main/stdlib/_typeshed
    # Shipped with the standard library part of typeshed, which is bundled with mypy:
    # https://github.com/python/typeshed/tree/main#using
    "_typeshed",
}


def _asym_diff(
    minuend: Mapping[ImportName, Iterable[Path]], subtrahend: Mapping[ImportName, Iterable[Path]]
) -> Mapping[ImportName, Iterable[Path]]:
    return {
        key: left_paths
        for key, paths in minuend.items()
        if (left_paths := set(paths) - set(subtrahend.get(key, ())))
    }


def test_dependencies_are_used() -> None:
    known_unused_packages = set(CEE_UNUSED_PACKAGES)
    known_unused_packages.add("setuptools")  # pinned transitive dependency
    # used for deploying the agent receiver, but in a bash script, so undetectable by this test
    known_unused_packages.add("gunicorn")

    if not is_pro_repo():
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
    undeclared_dependencies = {
        i.name: i.paths
        for i in get_undeclared_dependencies()
        if i.name not in KNOWN_UNDECLAREABLE_DEPENDENCIES
    }

    assert not (outdated := _asym_diff(KNOWN_UNDECLARED_DEPENDENCIES, undeclared_dependencies)), (
        f"The exceptionlist is outdated, these are the 'offenders': {outdated!r}"
    )

    assert not (offending := _asym_diff(undeclared_dependencies, KNOWN_UNDECLARED_DEPENDENCIES)), (
        f"There are imports that are not declared in the requirements files: {offending!r}"
    )


# Packages intentionally excluded from the python_requirements filegroups
# because they are development-only tools, not part of the product build.
_PYTHON_REQUIREMENTS_EXCLUDED: dict[str, set[str]] = {
    "packages": {"cmk-astrein"},
    "non-free/packages": set(),
}
_DEV_PYTHON_REQUIREMENTS_EXCLUDED: dict[str, set[str]] = {
    "packages": set(),
    "non-free/packages": set(),
}


@pytest.mark.parametrize(
    "packages_rel_path", ["packages", "non-free/packages"] if is_pro_repo() else ["packages"]
)
def test_python_requirements_filegroup_complete(packages_rel_path: str) -> None:
    """Every cmk-* package with requirements.in must be listed in python_requirements."""
    packages_dir = repo_path() / packages_rel_path

    listed = _parse_filegroup_packages(packages_rel_path, "python_requirements")
    on_disk = _packages_with_requirements(packages_dir, "requirements.in")
    excluded = _PYTHON_REQUIREMENTS_EXCLUDED[packages_rel_path]

    missing = on_disk - listed - excluded
    assert not missing, (
        f"Packages with requirements.in not listed in {packages_rel_path}/BUILD "
        f"python_requirements: {sorted(missing)}"
    )


@pytest.mark.parametrize(
    "packages_rel_path", ["packages", "non-free/packages"] if is_pro_repo() else ["packages"]
)
def test_dev_python_requirements_filegroup_complete(packages_rel_path: str) -> None:
    """Every cmk-* package with dev-requirements.in must be listed in dev_python_requirements."""
    packages_dir = repo_path() / packages_rel_path

    listed = _parse_filegroup_packages(packages_rel_path, "dev_python_requirements")
    on_disk = _packages_with_requirements(packages_dir, "dev-requirements.in")
    excluded = _DEV_PYTHON_REQUIREMENTS_EXCLUDED[packages_rel_path]

    missing = on_disk - listed - excluded
    assert not missing, (
        f"Packages with dev-requirements.in not listed in {packages_rel_path}/BUILD "
        f"dev_python_requirements: {sorted(missing)}"
    )


def _parse_filegroup_packages(packages_rel_path: str, group_name: str) -> set[str]:
    """Extract cmk-* package names referenced in a BUILD filegroup via bazel query."""
    target = f"//{packages_rel_path}:{group_name}"
    result = subprocess.run(
        ["bazel", "query", f"deps({target}, 1) - {target}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return set(re.findall(r"/(cmk-[^:]+):", result.stdout))


def _packages_with_requirements(packages_dir: Path, filename: str) -> set[str]:
    """Find cmk-* packages that provide the given requirements file.

    Uses filesystem scanning instead of bazel query because a package that forgot
    to add exports_files for its requirements.in would be invisible to Bazel.
    Which is exactly the oversight this test is meant to catch.
    """
    result = set()
    for d in packages_dir.iterdir():
        if not d.is_dir() or not d.name.startswith("cmk-"):
            continue

        # Most packages have requirements.in as a plain file on disk
        if (d / filename).is_file():
            result.add(d.name)
            continue

        # Some packages (e.g. cmk-plugins) generate requirements.in as a Bazel
        # target (via concat_files) instead of shipping a plain file.
        if (
            build_file := d / "BUILD"
        ).is_file() and f'name = "{filename}"' in build_file.read_text():
            result.add(d.name)

    return result
