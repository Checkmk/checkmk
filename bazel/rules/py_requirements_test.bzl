"""Generates a py_test that verifies:
  - every third-party import needed at runtime is declared in requirements.in
  - every import only needed for type checking (`if TYPE_CHECKING:`) or by dev sources
    (build/test tooling) is declared in requirements.in or the dev requirements file
  - every package declared in requirements.in is imported at runtime, so requirements.in,
    which is shipped with the product, contains no type-checking or build/test-only packages
  - every known_undeclared / known_unused suppression entry still applies
"""

load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

_TEST_TPL = '''\
\"\"\"Auto-generated requirements test for {package_id}.\"\"\"
from collections.abc import Mapping

import pytest

from tests.code_quality.bazel_utils import bazel_repo_root
from tests.code_quality.requirements.utils import (
    collect_third_party_imports,
    declared_pkg_imports,
    normalize,
)

# Sources shipped with the package: their runtime imports must be in requirements.in
_SOURCE_FILES: list[str] = [
{source_files}
]
# Sources only used at build or test time (e.g. code generators): their imports may be
# declared in the dev requirements file instead
_DEV_SOURCE_FILES: list[str] = [
{dev_source_files}
]
_REQUIREMENTS_IN = "{requirements_in}"
_DEV_REQUIREMENTS_IN: str | None = {dev_requirements_in}
_KNOWN_UNDECLARED_RAW: list[str] = [{known_undeclared}]
_KNOWN_UNDECLARED: set[str] = {{normalize(x) for x in _KNOWN_UNDECLARED_RAW}}
_KNOWN_UNUSED: set[str] = set([{known_unused}])


@pytest.fixture(scope="module")
def runtime_imports() -> set[str]:
    \"\"\"Third-party imports the shipped sources need at runtime (without `if TYPE_CHECKING:`)\"\"\"
    return collect_third_party_imports(_SOURCE_FILES, runtime_only=True)


@pytest.fixture(scope="module")
def all_imports() -> set[str]:
    \"\"\"All third-party imports: shipped sources incl. type checking, and dev sources\"\"\"
    return collect_third_party_imports(_SOURCE_FILES) | collect_third_party_imports(
        _DEV_SOURCE_FILES
    )


@pytest.fixture(scope="module")
def modules_by_declared_pkg() -> Mapping[str, set[str]]:
    \"\"\"Mapping of each package declared in requirements.in to the module names it provides,
    e.g. {{"pyyaml": {{"yaml"}}}}\"\"\"
    return declared_pkg_imports(bazel_repo_root() / _REQUIREMENTS_IN)


@pytest.fixture(scope="module")
def declared_runtime_modules(modules_by_declared_pkg: Mapping[str, set[str]]) -> set[str]:
    \"\"\"Flat set of module names provided by all declared packages (the values of
    modules_by_declared_pkg, without the package names), e.g. {{"yaml"}}\"\"\"
    return {{imp for imps in modules_by_declared_pkg.values() for imp in imps}}


@pytest.fixture(scope="module")
def declared_dev_modules() -> set[str]:
    \"\"\"Flat set of module names provided by the packages in the dev requirements file\"\"\"
    if _DEV_REQUIREMENTS_IN is None:
        return set()
    return {{
        imp
        for imps in declared_pkg_imports(bazel_repo_root() / _DEV_REQUIREMENTS_IN).values()
        for imp in imps
    }}


def test_runtime_dependencies_are_declared(
    runtime_imports: set[str], declared_runtime_modules: set[str]
) -> None:
    \"\"\"All third-party imports needed at runtime are declared in requirements.in\"\"\"
    undeclared = runtime_imports - declared_runtime_modules - _KNOWN_UNDECLARED
    assert not undeclared, f"Imported but not declared in requirements.in: {{undeclared}}"


def test_dev_dependencies_are_declared(
    runtime_imports: set[str],
    all_imports: set[str],
    declared_runtime_modules: set[str],
    declared_dev_modules: set[str],
) -> None:
    \"\"\"Imports only needed for type checking or by dev sources are declared somewhere\"\"\"
    undeclared = (
        all_imports - runtime_imports - declared_runtime_modules - declared_dev_modules
    ) - _KNOWN_UNDECLARED
    assert not undeclared, (
        f"Imported for type checking or by build/test tooling, but declared neither in"
        f" requirements.in nor in the dev requirements: {{undeclared}}"
    )


def test_runtime_dependencies_are_used(
    runtime_imports: set[str], modules_by_declared_pkg: Mapping[str, set[str]]
) -> None:
    \"\"\"All packages declared in requirements.in are needed at runtime

    requirements.in is shipped with the product. Packages only needed for type checking
    or by build/test tooling belong in the dev requirements.
    \"\"\"
    unused = {{
        pkg for pkg, imps in modules_by_declared_pkg.items()
        if not imps & runtime_imports and pkg not in _KNOWN_UNUSED
    }}
    assert not unused, (
        f"Declared in requirements.in but not imported at runtime (move packages only"
        f" needed for type checking or build/test tooling to the dev requirements): {{unused}}"
    )


def test_known_undeclared_entries_still_apply(
    runtime_imports: set[str],
    all_imports: set[str],
    declared_runtime_modules: set[str],
    declared_dev_modules: set[str],
) -> None:
    \"\"\"All known_undeclared suppressions are still imported and still undeclared\"\"\"
    import_removed = {{x for x in _KNOWN_UNDECLARED if x not in all_imports}}
    # A runtime import is only declared by requirements.in, the dev requirements don't count
    now_declared = {{
        x
        for x in _KNOWN_UNDECLARED
        if x in declared_runtime_modules
        or (x in declared_dev_modules and x not in runtime_imports)
    }}
    assert not import_removed, (
        f"Stale known_undeclared entries (import no longer present), remove them from"
        f" the BUILD file: {{import_removed}}"
    )
    assert not now_declared, (
        f"Stale known_undeclared entries (now declared), remove them from the BUILD"
        f" file: {{now_declared}}"
    )


def test_known_unused_entries_still_apply(
    runtime_imports: set[str], modules_by_declared_pkg: Mapping[str, set[str]]
) -> None:
    \"\"\"All known_unused suppressions are still declared and still not imported\"\"\"
    no_longer_declared = {{pkg for pkg in _KNOWN_UNUSED if pkg not in modules_by_declared_pkg}}
    now_imported = {{
        pkg for pkg in _KNOWN_UNUSED
        if pkg in modules_by_declared_pkg and modules_by_declared_pkg[pkg] & runtime_imports
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

def _package_sources(package_prefix, libs):
    all_sources = depset(transitive = [lib[PyInfo].transitive_sources for lib in libs])
    return [
        f
        for f in all_sources.to_list()
        # filter source files in the package, excluding dependencies
        if f.is_source and f.path.startswith(package_prefix)
    ]

def _gen_runner_impl(ctx):
    package_prefix = ctx.label.package + "/"
    source_files = _package_sources(package_prefix, ctx.attr.libs)
    dev_source_files = [
        f
        for f in _package_sources(package_prefix, ctx.attr.dev_libs)
        if f not in source_files
    ]
    dev_requirements_in = ctx.file.dev_requirements_in
    content = _TEST_TPL.format(
        package_id = ctx.label.package,
        source_files = "\n".join(['    "%s",' % f.short_path for f in source_files]),
        dev_source_files = "\n".join(['    "%s",' % f.short_path for f in dev_source_files]),
        requirements_in = ctx.file.requirements_in.short_path,
        dev_requirements_in = '"%s"' % dev_requirements_in.short_path if dev_requirements_in else "None",
        known_undeclared = ", ".join(['"%s"' % x for x in ctx.attr.known_undeclared]),
        known_unused = ", ".join(['"%s"' % x for x in ctx.attr.known_unused]),
    )
    runner = ctx.actions.declare_file(ctx.attr.name)
    ctx.actions.write(runner, content)
    return [DefaultInfo(files = depset([runner]))]

_gen_runner = rule(
    implementation = _gen_runner_impl,
    attrs = {
        "dev_libs": attr.label_list(default = [], providers = [DefaultInfo, PyInfo]),
        "dev_requirements_in": attr.label(allow_single_file = True),
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
        dev_libs = [],
        dev_requirements_in = None,
        known_undeclared = [],
        known_unused = [],
        **kwargs):
    """Test that a package's imports match its requirements.in declarations.

    Args:
        name: Name of the test target.
        libs: A py_library target or list of py_library targets whose sources and dependencies are scanned.
            These are the sources shipped with the product.
        requirements_in: Label or path to the requirements.in file (default: "requirements.in").
            Its packages are shipped with the product.
        dev_libs: py_library targets only used at build or test time (e.g. code generators).
            Their imports may be declared in dev_requirements_in.
        dev_requirements_in: Label or path to the dev requirements file. Imports of dev_libs and
            imports in `if TYPE_CHECKING:` blocks may be declared there instead of requirements.in.
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
        dev_libs = dev_libs,
        dev_requirements_in = dev_requirements_in,
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
        data = libs + dev_libs + [
            requirements_in,
            "//tests/code_quality/requirements:mapping",
        ] + ([dev_requirements_in] if dev_requirements_in else []),
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
