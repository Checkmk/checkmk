load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "engine",
    srcs = [
        "cmk/diagnostics/engine/__init__.py",
        "cmk/diagnostics/engine/_unsorted.py",
    ],
    data = [":engine_py_typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-ccc:site",
        "//packages/cmk-plugin-apis:diagnostics",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [":engine"],
)

filegroup(
    name = "engine_py_typed",
    srcs = ["cmk/diagnostics/engine/py.typed"],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-diagnostics",
    strip_path_prefixes = ["packages/cmk-diagnostics"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":engine",
        ":engine_py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = [
        "wheel",
    ],
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
        ":engine",
    ],
    requirements_in = "requirements.in",
)
