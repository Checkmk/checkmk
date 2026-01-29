load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-mkp-tool",
    srcs = [
        "cmk/mkp_tool/__init__.py",
        "cmk/mkp_tool/__main__.py",
        "cmk/mkp_tool/__version__.py",
        "cmk/mkp_tool/_installed.py",
        "cmk/mkp_tool/_mkp.py",
        "cmk/mkp_tool/_parts.py",
        "cmk/mkp_tool/_reload.py",
        "cmk/mkp_tool/_reporter.py",
        "cmk/mkp_tool/_standalone.py",
        "cmk/mkp_tool/_type_defs.py",
        "cmk/mkp_tool/_unsorted.py",
        "cmk/mkp_tool/cli.py",
    ],
    data = [":py_typed"],
    imports = ["."],
    visibility = [
        "//cmk:__pkg__",
        "//packages/cmk-ec:__pkg__",
    ],
    deps = [
        requirement("pydantic"),
        requirement("toml"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-mkp-tool"],
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
        ":cmk-mkp-tool",
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-mkp-tool",
    strip_path_prefixes = ["packages/cmk-mkp-tool"],
    # TODO: Duplicated from pyproject.toml
    version = "3.0.0",
    deps = [
        ":cmk-mkp-tool",
        ":py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/mkp_tool/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_wheel(
    name = "wheel_entrypoint_only",
    console_scripts = {"mkp": "cmk.mkp_tool.cli:main"},
    distribution = "cmk-mkp-tool-entrypoint",
    version = "2.0.0",
    visibility = ["//visibility:public"],
    deps = [],
)
