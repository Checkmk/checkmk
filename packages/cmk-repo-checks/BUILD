load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_python//python:defs.bzl", "py_binary")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")

py_library(
    name = "library",
    srcs = [
        "cmk/repo_checks/__init__.py",
        "cmk/repo_checks/bazel_lint_coverage.py",
        "cmk/repo_checks/deballast.py",
        "cmk/repo_checks/license_header_checker.py",
        "cmk/repo_checks/python_extension_checker.py",
    ],
    data = ["cmk/repo_checks/py.typed"],
    imports = ["."],
    visibility = ["//tests:__subpackages__"],
)

# Per-target checker behind the deballast_aspect in deballast.bzl; not
# meant to be run directly.
py_binary(
    name = "deballast_bin",
    srcs = ["cmk/repo_checks/deballast.py"],
    imports = ["."],
    main = "cmk/repo_checks/deballast.py",
    visibility = ["//visibility:public"],
    deps = [":library"],
)

# Per-target checker behind the license_header aspect in lint_license_header.bzl;
# not meant to be run directly.
py_binary(
    name = "license_header_checker_bin",
    srcs = ["cmk/repo_checks/license_header_checker.py"],
    imports = ["."],
    main = "cmk/repo_checks/license_header_checker.py",
    visibility = ["//visibility:public"],
    deps = [":library"],
)

# Per-target checker behind the python_extension aspect in
# lint_python_extensions.bzl; not meant to be run directly.
py_binary(
    name = "python_extension_checker_bin",
    srcs = ["cmk/repo_checks/python_extension_checker.py"],
    imports = ["."],
    main = "cmk/repo_checks/python_extension_checker.py",
    visibility = ["//visibility:public"],
    deps = [":library"],
)

# Runs `bazel query` itself, so it must be started with `bazel run` from the
# repository root. Used by the "Bazel sanity check" stage in
# buildscripts/scripts/stages.yml.
py_binary(
    name = "bazel_lint_coverage",
    srcs = ["cmk/repo_checks/bazel_lint_coverage.py"],
    imports = ["."],
    main = "cmk/repo_checks/bazel_lint_coverage.py",
    deps = [":library"],
)

py_cmk_test(
    name = "test",
    size = "small",
    srcs = glob(["tests/test_*.py"]),
    deps = [":library"],
)
