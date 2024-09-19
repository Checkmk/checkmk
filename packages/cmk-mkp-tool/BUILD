load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")
load("@rules_python//python:packaging.bzl", "py_wheel")

py_library(
    name = "cmk-mkp-tool",
    srcs = [
        "cmk/mkp_tool/__init__.py",
        "cmk/mkp_tool/__main__.py",
        "cmk/mkp_tool/__version__.py",
        "cmk/mkp_tool/_installed.py",
        "cmk/mkp_tool/_mkp.py",
        "cmk/mkp_tool/_parts.py",
        "cmk/mkp_tool/_reporter.py",
        "cmk/mkp_tool/_standalone.py",
        "cmk/mkp_tool/_type_defs.py",
        "cmk/mkp_tool/_unsorted.py",
        "cmk/mkp_tool/cli.py",
    ],
    visibility = ["//visibility:public"],
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

package_wheel(wheel_target = "wheel")
