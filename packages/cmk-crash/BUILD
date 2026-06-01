load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "crash",
    srcs = [
        "cmk/crash/__init__.py",
    ],
    data = [":crash_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
)

py_library(
    name = "crash_reporting",
    srcs = [
        "cmk/crash_reporting/__init__.py",
    ],
    data = [":crash_reporting_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":crash",
    ],
)

filegroup(
    name = "crash_py_typed",
    srcs = ["cmk/crash/py.typed"],
)

filegroup(
    name = "crash_reporting_py_typed",
    srcs = ["cmk/crash_reporting/py.typed"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-crash",
    strip_path_prefixes = ["packages/cmk-crash"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":crash",
        ":crash_py_typed",
        ":crash_reporting",
        ":crash_reporting_py_typed",
    ],
)

# This wheel is only used for providing the entry point "cmk-upload-crashes" from the .venv under
# .venv/bin. We explicitly need to *not* add dependencies here because venv/IDE would take the
# static wheels and not the editable sources from the repo which are included via sitecustomize.py.
# The CLI implementation lands in Epic 2 (CMK-202); the entry point is wired here as a placeholder.
py_wheel(
    name = "wheel_entrypoint_only",
    console_scripts = {"cmk-upload-crashes": "cmk.crash_reporting.cli:main"},
    distribution = "cmk-crash-entrypoint",
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [],
)

build_test(
    name = "build_test",
    targets = [
        "wheel",
        "wheel_entrypoint_only",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":crash",
        ":crash_reporting",
    ],
    requirements_in = "requirements.in",
)
