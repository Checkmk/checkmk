"""Generates a py_test that verifies:
  - every third-party import in the package is declared in requirements.in
  - every package declared in requirements.in is actually imported
"""

load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

_TEST_TPL = '''\
"""Auto-generated requirements test for {package_id}."""
import pytest

from tests.code_quality.bazel_utils import bazel_repo_root
from tests.code_quality.requirements.utils import (
    collect_third_party_imports,
    declared_pkg_imports,
)

_SOURCE_FILES = [
{source_files}
]
_REQUIREMENTS_IN = "{requirements_in}"
_KNOWN_UNDECLARED: set[str] = set([{known_undeclared}])
_KNOWN_UNUSED: set[str] = set([{known_unused}])


@pytest.fixture(scope="module")
def imported() -> set[str]:
    return collect_third_party_imports(_SOURCE_FILES)


def test_dependencies_are_declared(imported: set[str]) -> None:
    """All third-party imports in the package are declared in requirements.in"""
    requirements_file_path = bazel_repo_root() / _REQUIREMENTS_IN
    all_declared = {{imp for imps in declared_pkg_imports(requirements_file_path).values() for imp in imps}}
    undeclared = imported - all_declared - _KNOWN_UNDECLARED
    assert not undeclared, f"Imported but not declared in requirements.in: {{undeclared}}"


def test_dependencies_are_used(imported: set[str]) -> None:
    """All packages declared in requirements.in are actually imported"""
    requirements_file_path = bazel_repo_root() / _REQUIREMENTS_IN
    unused = {{
        pkg for pkg, imps in declared_pkg_imports(requirements_file_path).items()
        if not imps & imported and pkg not in _KNOWN_UNUSED
    }}
    assert not unused, f"Declared in requirements.in but not imported: {{unused}}"


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
    libs = libs if type(libs) == type([]) else [libs]
    runner_name = name.replace("-", "_") + "_runner.py"
    _gen_runner(
        name = runner_name,
        libs = libs,
        requirements_in = requirements_in,
        known_undeclared = known_undeclared,
        known_unused = known_unused,
        testonly = True,
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
