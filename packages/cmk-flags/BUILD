load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "cmk-flags",
    srcs = [
        "cmk/flags/__init__.py",
        "cmk/flags/_config.py",
    ],
    data = [":py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("pydantic"),
    ],
)

_ALL = [
    "cmk-flags",
]

py_wheel(
    name = "wheel",
    distribution = "cmk-flags",
    strip_path_prefixes = ["packages/cmk-flags"],
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
    srcs = ["cmk/flags/py.typed"],
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
