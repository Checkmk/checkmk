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
    branch_from_env,
    current_base_branch_name,
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
            if not (package_path / "requirements.in").exists():
                # No python package
                continue
            yield pytest.param(package_path, id=package_path.relative_to(repo_path()).as_posix())


@pytest.mark.parametrize("package_path", find_packages())
def test_package_declared_all_python_deps(package_path: Path) -> None:
    if package_path.relative_to(repo_path()).as_posix() == "non-free/packages/cmk-core-helpers":
        pytest.skip("cmk-core-helpers needs netsnmp which does not come from pypi")
    venv_libs = get_requirements_libs(repo_path())
    imported_libs = {d.normalized_name for d in get_imported_libs(package_path)}
    required_packages = set(parse_requirements_file(package_path / "requirements.in"))

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
    },
    ImportName("tests"): {
        Path("buildscripts/scripts/assert_build_artifacts.py"),
        Path("buildscripts/scripts/lib/registry.py"),
    },
    # TODO: added reminder to drop these file paths post-migration:
    ImportName("cmk_addons"): {
        Path("doc/treasures/cisco_meraki/agent_based/appliance_performance.py"),
        Path("doc/treasures/cisco_meraki/libexec/agent_cisco_meraki"),
        Path("doc/treasures/cisco_meraki/rulesets/meraki_agent.py"),
        Path("doc/treasures/cisco_meraki/lib/agent.py"),
        Path("doc/treasures/cisco_meraki/agent_based/appliance_vpns.py"),
        Path("doc/treasures/cisco_meraki/agent_based/device_uplinks.py"),
        Path("doc/treasures/cisco_meraki/agent_based/switch_ports_statuses.py"),
        Path("doc/treasures/cisco_meraki/agent_based/networks.py"),
        Path("doc/treasures/cisco_meraki/agent_based/appliance_performance.py"),
        Path("doc/treasures/cisco_meraki/agent_based/cellular_uplinks.py"),
        Path("doc/treasures/cisco_meraki/agent_based/wireless_ethernet_statuses.py"),
        Path("doc/treasures/cisco_meraki/agent_based/organisations_api.py"),
        Path("doc/treasures/cisco_meraki/agent_based/device_status.py"),
        Path("doc/treasures/cisco_meraki/agent_based/licenses_overview.py"),
        Path("doc/treasures/cisco_meraki/agent_based/appliance_uplinks.py"),
        Path("doc/treasures/cisco_meraki/agent_based/device_info.py"),
        Path("doc/treasures/cisco_meraki/agent_based/wireless_device_ssid_status.py"),
    },
    ImportName("pip"): {  # is included by default in python
        Path("omd/packages/Python/pip")
    },
    ImportName("ibm_db"): {Path("cmk/plugins/sql/active_check/check_sql.py")},
    ImportName("sqlanydb"): {Path("cmk/plugins/sql/active_check/check_sql.py")},
    ImportName("ibm_db_dbi"): {Path("cmk/plugins/sql/active_check/check_sql.py")},
    ImportName("mypy_boto3_logs"): {  # used by mypy within typing.TYPE_CHECKING
        Path("cmk/plugins/aws/special_agent/agent_aws.py")
    },
    ImportName("tinkerforge"): {Path("cmk/plugins/tinkerforge/special_agent/agent_tinkerforge.py")},
    ImportName("rados"): {Path("cmk/plugins/ceph/agents/mk_ceph.py")},
    # Package is called sarif-tools
    ImportName("sarif"): {Path("scripts/sarif_preparse.py")},
    ImportName("netsnmp"): {  # We ship it with omd/packages
        Path("non-free/packages/cmk-core-helpers/cmk/inline_snmp/inline.py")
    },
    ImportName("rrdtool"): {  # is built as part of the project
        Path("bin/cmk-convert-rrds"),
        Path("bin/cmk-create-rrd"),
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


@pytest.mark.skip("CMK-28820")
def test_dependencies_are_declared() -> None:
    """Test for unknown imports which could not be mapped to the requirements files

    mostly optional imports and OMD-only shiped packages."""
    undeclared_dependencies = {i.name: i.paths for i in get_undeclared_dependencies()}

    assert not (outdated := _asym_diff(KNOWN_UNDECLARED_DEPENDENCIES, undeclared_dependencies)), (
        f"The exceptionlist is outdated, these are the 'offenders': {outdated!r}"
    )

    assert not (offending := _asym_diff(undeclared_dependencies, KNOWN_UNDECLARED_DEPENDENCIES)), (
        f"There are imports that are not declared in the requirements files: {offending!r}"
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


def test_no_development_packages_in_runtime_requirements() -> None:
    """Test that development/testing libraries are not included in runtime requirements"""
    runtime_requirements = get_requirements_libs(repo_path())

    forbidden_prefixes = ["pytest-", "types-"]
    offending_packages = []

    for package_name in runtime_requirements.keys():
        for prefix in forbidden_prefixes:
            if package_name.startswith(prefix):
                offending_packages.append(package_name)

    assert not offending_packages, (
        f"The following development/testing libraries should not be "
        f"in runtime requirements: {offending_packages}"
    )
