"""Generates a py_test that verifies:
  - every third-party import in the package is declared in requirements.in
  - every package declared in requirements.in is actually imported
  - every known_undeclared / known_unused suppression entry still applies
"""

load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

_TEST_TPL = '''\
"""Auto-generated requirements test for {package_id}."""
from collections.abc import Mapping

import pytest

from tests.code_quality.bazel_utils import bazel_repo_root
from tests.code_quality.requirements.utils import (
    collect_third_party_imports,
    declared_pkg_imports,
    normalize,
)

_SOURCE_FILES = [
{source_files}
]
_REQUIREMENTS_IN = "{requirements_in}"
_KNOWN_UNDECLARED_RAW: list[str] = [{known_undeclared}]
_KNOWN_UNDECLARED: set[str] = {{normalize(x) for x in _KNOWN_UNDECLARED_RAW}}
_KNOWN_UNUSED: set[str] = set([{known_unused}])


@pytest.fixture(scope="module")
def imported_modules() -> set[str]:
    """Third-party imports found in the package's source files"""
    return collect_third_party_imports(_SOURCE_FILES)


@pytest.fixture(scope="module")
def modules_by_declared_pkg() -> Mapping[str, set[str]]:
    """Mapping of each package declared in requirements.in to the module names it provides,
    e.g. {{"pyyaml": {{"yaml"}}}}"""
    return declared_pkg_imports(bazel_repo_root() / _REQUIREMENTS_IN)


@pytest.fixture(scope="module")
def declared_modules(modules_by_declared_pkg: Mapping[str, set[str]]) -> set[str]:
    """Flat set of module names provided by all declared packages (the values of
    modules_by_declared_pkg, without the package names), e.g. {{"yaml"}}"""
    return {{imp for imps in modules_by_declared_pkg.values() for imp in imps}}


def test_dependencies_are_declared(imported_modules: set[str], declared_modules: set[str]) -> None:
    """All third-party imports in the package are declared in requirements.in"""
    undeclared = imported_modules - declared_modules - _KNOWN_UNDECLARED
    assert not undeclared, f"Imported but not declared in requirements.in: {{undeclared}}"


def test_dependencies_are_used(
    imported_modules: set[str], modules_by_declared_pkg: Mapping[str, set[str]]
) -> None:
    """All packages declared in requirements.in are actually imported"""
    unused = {{
        pkg for pkg, imps in modules_by_declared_pkg.items()
        if not imps & imported_modules and pkg not in _KNOWN_UNUSED
    }}
    assert not unused, f"Declared in requirements.in but not imported: {{unused}}"


def test_known_undeclared_entries_still_apply(
    imported_modules: set[str], declared_modules: set[str]
) -> None:
    """All known_undeclared suppressions are still imported and still undeclared"""
    import_removed = {{x for x in _KNOWN_UNDECLARED if x not in imported_modules}}
    now_declared = {{x for x in _KNOWN_UNDECLARED if x in declared_modules}}
    assert not import_removed, (
        f"Stale known_undeclared entries (import no longer present), remove them from"
        f" the BUILD file: {{import_removed}}"
    )
    assert not now_declared, (
        f"Stale known_undeclared entries (now declared in requirements.in), remove"
        f" them from the BUILD file: {{now_declared}}"
    )


def test_known_unused_entries_still_apply(
    imported_modules: set[str], modules_by_declared_pkg: Mapping[str, set[str]]
) -> None:
    """All known_unused suppressions are still declared and still not imported"""
    no_longer_declared = {{pkg for pkg in _KNOWN_UNUSED if pkg not in modules_by_declared_pkg}}
    now_imported = {{
        pkg for pkg in _KNOWN_UNUSED
        if pkg in modules_by_declared_pkg and modules_by_declared_pkg[pkg] & imported_modules
    }}
    assert not no_longer_declared, (
        f"Stale known_unused entries (no longer declared in requirements.in), remove"
        f" them from the BUILD file: {{no_longer_declared}}"
    )
    assert not now_imported, (
        f"Stale known_unused entries (now imported), remove them from the BUILD"
        f" file: {{now_imported}}"
    )


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
'''

def _gen_runner_impl(ctx):
    package_prefix = ctx.label.package + "/"
    all_sources = depset(transitive = [src[PyInfo].transitive_sources for src in ctx.attr.libs])
    source_files = [
        f
        for f in all_sources.to_list()
        # filter source files in the package, excluding dependencies
        if f.is_source and f.path.startswith(package_prefix)
    ]
    content = _TEST_TPL.format(
        package_id = ctx.label.package,
        source_files = "\n".join(['    "%s",' % f.short_path for f in source_files]),
        requirements_in = ctx.file.requirements_in.short_path,
        known_undeclared = ", ".join(['"%s"' % x for x in ctx.attr.known_undeclared]),
        known_unused = ", ".join(['"%s"' % x for x in ctx.attr.known_unused]),
    )
    runner = ctx.actions.declare_file(ctx.attr.name)
    ctx.actions.write(runner, content)
    return [DefaultInfo(files = depset([runner]))]

_gen_runner = rule(
    implementation = _gen_runner_impl,
    attrs = {
        "known_undeclared": attr.string_list(default = []),
        "known_unused": attr.string_list(default = []),
        "libs": attr.label_list(mandatory = True, providers = [DefaultInfo, PyInfo]),
        "requirements_in": attr.label(mandatory = True, allow_single_file = True),
    },
)

def py_requirements_test(
        name,
        libs,
        requirements_in,
        known_undeclared = [],
        known_unused = [],
        **kwargs):
    """Test that a package's imports match its requirements.in declarations.

    Args:
        name: Name of the test target.
        libs: A py_library target or list of py_library targets whose sources and dependencies are scanned.
        requirements_in: Label or path to the requirements.in file (default: "requirements.in").
        known_undeclared: Imports that are intentionally not declared.
        known_unused: Declared packages that are intentionally not directly imported.
        **kwargs: Passed through to py_test (e.g. size, tags).
    """
    libs = libs if type(libs) in ("list", "select") else [libs]
    runner_name = name.replace("-", "_") + "_runner.py"
    _gen_runner(
        name = runner_name,
        libs = libs,
        requirements_in = requirements_in,
        known_undeclared = known_undeclared,
        known_unused = known_unused,
        testonly = True,
        target_compatible_with = kwargs.get("target_compatible_with", []),
    )
    py_test(
        name = name,
        srcs = [runner_name],
        main = runner_name,
        tags = kwargs.pop("tags", []) + ["requirements"],
        data = libs + [
            requirements_in,
            "//tests/code_quality/requirements:mapping",
        ],
        env = {
            "PIP_PACKAGE_MAPPING": "$(rootpath //tests/code_quality/requirements:mapping)",
        },
        deps = [
            requirement("pytest"),
            "//tests/code_quality:bazel_utils",
            "//tests/code_quality/requirements:requirements_utils",
        ],
        **kwargs
    )
