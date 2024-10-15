load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")
load("@rules_python//python:packaging.bzl", "py_wheel")

exports_files([
    "pyproject.toml",
    "requirements.txt",
])

py_library(
    name = "cmk-graphing",
    srcs = [
        "cmk/graphing/__init__.py",
        "cmk/graphing/v1/__init__.py",
        "cmk/graphing/v1/_localize.py",
        "cmk/graphing/v1/_type_defs.py",
        "cmk/graphing/v1/graphs.py",
        "cmk/graphing/v1/metrics.py",
        "cmk/graphing/v1/perfometers.py",
        "cmk/graphing/v1/translations.py",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-graphing",
    strip_path_prefixes = ["packages/cmk-graphing"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-graphing",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
