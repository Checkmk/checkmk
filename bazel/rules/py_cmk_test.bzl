"""Wrapper macro for py_test that enforces standard Checkmk pytest defaults."""

load("@aspect_rules_py//py:defs.bzl", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")

def py_cmk_test(
        name,
        use_project_pytest_config = False,
        args = [],
        data = [],
        deps = [],
        **kwargs):
    """Wraps py_test with standard Checkmk pytest defaults.

    Always sets --import-mode=importlib so tests are isolated from each other
    and work correctly with namespace packages and duplicate test filenames.
    Always enables the built-in pytest entry-point and makes pytest and
    coverage available as deps.

    Args:
        name: Name of the test target.
        use_project_pytest_config: If True, wires in the root pyproject.toml
            (addopts, filterwarnings, marker registrations). Leave False for
            standalone packages that ship as separate wheels and must remain
            usable outside the monorepo.
        args: Additional pytest arguments (appended after the defaults).
        data: Additional data files.
        deps: Additional dependencies.
        **kwargs: Passed through to py_test unchanged.
    """
    extra_args = ["--config-file=$(location @//:pyproject.toml)"] if use_project_pytest_config else []
    extra_data = ["@//:pyproject.toml"] if use_project_pytest_config else []

    # //:pyproject-toml carries marshmallow as a dep; pytest needs it at
    # startup to resolve the filterwarnings entry in pyproject.toml.
    extra_deps = ["//:pyproject-toml"] if use_project_pytest_config else []

    py_test(
        name = name,
        pytest_main = True,
        args = ["--import-mode=importlib"] + args + extra_args,
        data = data + extra_data,
        deps = deps + extra_deps + [
            requirement("coverage"),
            requirement("pytest"),
        ],
        **kwargs
    )
