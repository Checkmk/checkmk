load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "requirements.in",
])

py_library(
    name = "cmk-graphing-engine",
    srcs = [
        "cmk/graphing_engine/__init__.py",
        "cmk/graphing_engine/_data/__init__.py",
        "cmk/graphing_engine/_data/_fetched.py",
        "cmk/graphing_engine/_data/_naming.py",
        "cmk/graphing_engine/_data/_timeseries.py",
        "cmk/graphing_engine/_data/_units.py",
        "cmk/graphing_engine/_evaluation/__init__.py",
        "cmk/graphing_engine/_evaluation/_fetch.py",
        "cmk/graphing_engine/_evaluation/_graphs.py",
        "cmk/graphing_engine/_evaluation/_title.py",
        "cmk/graphing_engine/_graphs/__init__.py",
        "cmk/graphing_engine/_graphs/_drawn_curves.py",
        "cmk/graphing_engine/_graphs/_graph.py",
        "cmk/graphing_engine/_perfometers/__init__.py",
        "cmk/graphing_engine/_perfometers/_evaluation.py",
        "cmk/graphing_engine/_perfometers/_geometry.py",
        "cmk/graphing_engine/_plugins/__init__.py",
        "cmk/graphing_engine/_plugins/_display.py",
        "cmk/graphing_engine/_plugins/_graphs.py",
        "cmk/graphing_engine/_plugins/_matching.py",
        "cmk/graphing_engine/_plugins/_order.py",
        "cmk/graphing_engine/_plugins/_quantities.py",
        "cmk/graphing_engine/_plugins/_translations.py",
        "cmk/graphing_engine/_plugins/_types.py",
        "cmk/graphing_engine/_quantities/__init__.py",
        "cmk/graphing_engine/_quantities/_expressions.py",
        "cmk/graphing_engine/_quantities/_operations.py",
        "cmk/graphing_engine/_quantities/_quantity.py",
        "cmk/graphing_engine/_rrd/__init__.py",
        "cmk/graphing_engine/_rrd/_fetch.py",
        "cmk/graphing_engine/_rrd/_metrics.py",
        "cmk/graphing_engine/_rrd/_naming.py",
        "cmk/graphing_engine/_rrd/_performance_data.py",
        "cmk/graphing_engine/_rrd/_resample.py",
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

py_requirements_test(
    name = "requirements-test",
    libs = _ALL,
    requirements_in = "requirements.in",
)
