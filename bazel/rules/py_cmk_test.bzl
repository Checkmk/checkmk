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
    Always keeps pytest from collecting the generated runner, see below.
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
        # --ignore-glob keeps pytest from collecting the runner rules_py generates
        # for this target. It lands in the runfiles next to the sources as
        # <name>.pytest_main.py, which matches pytest's own test_*.py glob
        # whenever the target is named test_*. Collecting it re-imports the
        # runner mid-session, and its module-level coverage.start() then pushes a
        # second collector that the outer cov.stop() trips over -- so the target
        # passes under `bazel test` and fails under `bazel coverage`.
        args = [
            "--import-mode=importlib",
            "--ignore-glob=*pytest_main.py",
        ] + args + extra_args,
        data = data + extra_data,
        deps = deps + extra_deps + [
            requirement("coverage"),
            requirement("pytest"),
        ],
        **kwargs
    )
