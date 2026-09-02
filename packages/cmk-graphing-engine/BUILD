load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-graphing-engine",
    srcs = [
        "cmk/graphing_engine/__init__.py",
        "cmk/graphing_engine/_api_plugins.py",
        "cmk/graphing_engine/_display.py",
        "cmk/graphing_engine/_fetch.py",
        "cmk/graphing_engine/_fetched.py",
        "cmk/graphing_engine/_graph.py",
        "cmk/graphing_engine/_graph_evaluate.py",
        "cmk/graphing_engine/_graph_from_api.py",
        "cmk/graphing_engine/_graph_matching.py",
        "cmk/graphing_engine/_naming.py",
        "cmk/graphing_engine/_operations.py",
        "cmk/graphing_engine/_quantities.py",
        "cmk/graphing_engine/_quantity.py",
        "cmk/graphing_engine/_quantity_from_api.py",
        "cmk/graphing_engine/_timeseries.py",
        "cmk/graphing_engine/_title.py",
        "cmk/graphing_engine/_units.py",
    ],
    data = [":py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:graphing",
    ],
)

_ALL = [
    "cmk-graphing-engine",
]

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]),
    deps = [
        ":cmk-graphing-engine",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-graphing-engine",
    strip_path_prefixes = ["packages/cmk-graphing-engine"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = _ALL + [
        ":py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/graphing_engine/py.typed"],
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
    libs = _ALL,
    requirements_in = "requirements.in",
)
