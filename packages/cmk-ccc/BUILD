load("@aspect_rules_lint//format:defs.bzl", "format_multirun")
load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.txt",
])

py_library(
    # TODO(ml): Split into separate libs.  This package is really
    #           a collection of more or less unrelated modules.
    name = "cmk-ccc",
    srcs = [
        "cmk/ccc/__init__.py",
        "cmk/ccc/crash_reporting.py",
        "cmk/ccc/daemon.py",
        "cmk/ccc/debug.py",
        "cmk/ccc/exceptions.py",
        "cmk/ccc/i18n.py",
        "cmk/ccc/plugin_registry.py",
        "cmk/ccc/profile.py",
        "cmk/ccc/site.py",
        "cmk/ccc/store/__init__.py",
        "cmk/ccc/store/_file.py",
        "cmk/ccc/store/_locks.py",
        "cmk/ccc/version.py",
    ],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-livestatus-client:py_livestatus",
        "//packages/cmk-trace",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-ccc"],
    tags = ["no-mypy"],
)

py_pytest_main(
    name = "__test__",
    deps = [
        requirement("pytest"),
    ],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":cmk-ccc",
        requirement("pytest"),
    ],
)

format_multirun(
    name = "format",
    python = "@aspect_rules_lint//format:ruff",
)

py_wheel(
    name = "wheel",
    distribution = "cmk-ccc",
    strip_path_prefixes = ["packages/cmk-ccc"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [":cmk-ccc"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
