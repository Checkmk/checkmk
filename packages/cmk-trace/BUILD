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
    name = "cmk-trace",
    srcs = [
        "cmk/trace/__init__.py",
        "cmk/trace/_config.py",
        "cmk/trace/_propagate.py",
        "cmk/trace/_tracer.py",
        "cmk/trace/export.py",
        "cmk/trace/logs.py",
    ],
    data = ["cmk/trace/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("opentelemetry-api"),
        requirement("opentelemetry-sdk"),
        requirement("opentelemetry-exporter-otlp"),
        requirement("opentelemetry-exporter-otlp-proto-grpc"),
        requirement("opentelemetry-semantic-conventions"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-trace"],
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
        ":cmk-trace",
        requirement("opentelemetry-api"),
        requirement("opentelemetry-sdk"),
        requirement("opentelemetry-exporter-otlp"),
        requirement("opentelemetry-exporter-otlp-proto-grpc"),
        requirement("opentelemetry-semantic-conventions"),
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-trace",
    strip_path_prefixes = ["packages/cmk-trace"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-trace",
        ":py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/trace/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
