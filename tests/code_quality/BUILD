load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "bazel_utils",
    testonly = True,
    srcs = ["bazel_utils.py"],
    imports = ["../.."],
    visibility = ["//:__subpackages__"],
)

py_library(
    name = "code_quality",
    testonly = True,
    # Explicit list: bazel_utils.py has its own target above, and
    # test_python_extensions.py is git-dependent and must only run via the
    # dedicated target below.
    srcs = [
        "__init__.py",
        "conftest.py",
        "test_no_nargs_in_agents.py",
        "test_package_json.py",
        "utils.py",
    ],
    imports = ["../.."],
    deps = [
        "//tests/testlib/common:repo",
        requirement("pydantic"),
        requirement("pytest"),
        requirement("isort"),
        requirement("requirements-parser"),
    ],
)

# Filesystem-level Python-extension check.
# Tagged no-sandbox + requires-git because it shells out to `git ls-files` and
# reads files outside the Bazel sandbox (the "All unit tests" stage filters
# -requires-git). Run by the "Bazel sanity check" stage in the change
# validation (buildscripts/scripts/stages.yml), or by hand:
#   bazel test //tests/code_quality:python_extensions
py_cmk_test(
    name = "python_extensions",
    srcs = ["test_python_extensions.py"],
    imports = ["../.."],
    tags = [
        "no-sandbox",
        "requires-git",
    ],
    use_project_pytest_config = True,
    deps = [
        ":bazel_utils",
        "//packages/cmk-repo-checks:library",
    ],
)
