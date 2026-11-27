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
    Always disables pytest's legacypath plugin (tmpdir and other py.path APIs).
    Always enables the built-in pytest entry-point and makes pytest and
    coverage available as deps. pytest collects tests only from the
    directories of srcs and below, so list shared test files in srcs (e.g.
    via a filegroup), not in deps or data. Paths in args or --test_arg
    replace those directories, so --test_arg=<test file> only narrows a run
    if args holds no path.

    Args:
        name: Name of the test target.
        use_project_pytest_config: If True, wires in the root pyproject.toml
            (addopts, filterwarnings, marker registrations). Leave False for
            standalone packages that ship as separate wheels and must remain
            usable outside the monorepo.
        args: Additional pytest arguments (appended after the defaults).
        data: Additional data files. rules_py's py_test needs plain lists for data
            and deps, so put a select() into a filegroup or py_library and list that.
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
        args = [
            "--import-mode=importlib",
            # Keep the py.path based tmpdir/testdir fixtures out, use tmp_path.
            "-p",
            "no:legacypath",
        ] + args + extra_args,
        data = data + extra_data,
        deps = deps + extra_deps + [
            requirement("coverage"),
            requirement("pytest"),
        ],
        **kwargs
    )
