load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.txt",
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
    data = [":pyproject.toml"],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        requirement("pydantic"),
        requirement("toml"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-mkp-tool",
    strip_path_prefixes = ["packages/cmk-mkp-tool"],
    # TODO: Duplicated from pyproject.toml
    version = "0.2.0",
    deps = [
        ":cmk-mkp-tool",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
