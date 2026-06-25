load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-relay-protocols",
    srcs = [
        "cmk/relay_protocols/__init__.py",
        "cmk/relay_protocols/configuration.py",
        "cmk/relay_protocols/monitoring_data.py",
        "cmk/relay_protocols/relays.py",
        "cmk/relay_protocols/tasks.py",
    ],
    data = ["cmk/relay_protocols/py.typed"],
    imports = ["."],
    visibility = ["//:__subpackages__"],
    deps = [
        requirement("pydantic"),
        requirement("cryptography"),
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-relay-protocols"],
    tags = ["no-mypy"],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]),
    deps = [
        ":cmk-relay-protocols",
        requirement("cryptography"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-relay-protocols",
    strip_path_prefixes = ["packages/cmk-relay-protocols"],
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":cmk-relay-protocols",
        ":py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/relay_protocols/py.typed"],
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
    libs = [
        ":cmk-relay-protocols",
    ],
    requirements_in = "requirements.in",
)
