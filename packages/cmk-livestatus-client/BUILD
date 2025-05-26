load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-livestatus-client",
    srcs = ["cmk/livestatus_client/__init__.py"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:site",
        "//packages/cmk-trace",
        requirement("opentelemetry-api"),
    ],
)

py_library(
    name = "py_livestatus",
    srcs = ["livestatus/__init__.py"],
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
    deps = [":cmk-livestatus-client"],
)

py_wheel(
    name = "livestatus_whl",
    distribution = "livestatus",
    strip_path_prefixes = ["packages/cmk-livestatus-client"],
    # TODO: VERSION is duplicated in pyproject.toml
    version = "1.0.0",
    deps = [":py_livestatus"],
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
