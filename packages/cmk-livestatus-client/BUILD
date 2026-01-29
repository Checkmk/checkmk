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
    name = "livestatus-connection",
    srcs = [
        "cmk/livestatus_client/_connection.py",
    ],
    imports = ["."],
    deps = [
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-trace",
        requirement("opentelemetry-api"),
    ],
)

py_library(
    name = "livestatus-api",
    srcs = [
        "cmk/livestatus_client/_api/__init__.py",
        "cmk/livestatus_client/_api/client.py",
        "cmk/livestatus_client/_api/commands.py",
        "cmk/livestatus_client/expressions.py",
        "cmk/livestatus_client/queries.py",
        "cmk/livestatus_client/testing.py",
        "cmk/livestatus_client/types.py",
    ] + glob([
        "cmk/livestatus_client/tables/*.py",
    ]),
    imports = ["."],
    deps = [
        ":livestatus-connection",
        "//packages/cmk-ccc:hostaddress",
        requirement("jinja2"),
    ],
)

py_library(
    name = "cmk-livestatus-client",
    srcs = [
        "cmk/livestatus_client/__init__.py",
    ],
    data = ["cmk/livestatus_client/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":livestatus-api",
        ":livestatus-connection",
    ],
)

py_library(
    name = "py_livestatus",
    srcs = ["livestatus/__init__.py"],
    data = ["livestatus/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [":cmk-livestatus-client"],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-livestatus-client"],
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
        ":cmk-livestatus-client",
        requirement("pytest"),
    ],
)

py_wheel(
    name = "cmk-livestatus-client_whl",
    distribution = "cmk-livestatus-client",
    strip_path_prefixes = ["packages/cmk-livestatus-client"],
    # TODO: VERSION is duplicated in pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-livestatus-client",
        ":cmk_livestatus_client_py_typed",
        ":livestatus-api",
        ":livestatus-connection",
    ],
)

build_test(
    name = "build_test",
    targets = ["cmk-livestatus-client_whl"],
)

filegroup(
    name = "cmk_livestatus_client_py_typed",
    srcs = ["cmk/livestatus_client/py.typed"],
)

py_wheel(
    name = "livestatus_whl",
    distribution = "livestatus",
    strip_path_prefixes = ["packages/cmk-livestatus-client"],
    # TODO: VERSION is duplicated in pyproject.toml
    version = "1.0.0",
    deps = [
        ":livestatus_py_typed",
        ":py_livestatus",
    ],
)

filegroup(
    name = "livestatus_py_typed",
    srcs = ["livestatus/py.typed"],
)

package_wheel(
    name = "cmk_livestatus_client_pkg_tar",
    visibility = ["//visibility:public"],
    whl = "cmk-livestatus-client_whl",
)

package_wheel(
    name = "cmk_livestatus_pkg_tar",
    visibility = ["//visibility:public"],
    whl = "livestatus_whl",
)
