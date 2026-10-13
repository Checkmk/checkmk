load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")

exports_files([
    "dev-requirements.in",
    "requirements.in",
])

py_library(
    name = "cmk-fastapi",
    srcs = [
        "cmk/fastapi/__init__.py",
        "cmk/fastapi/sse.py",
    ],
    data = ["cmk/fastapi/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        requirement("fastapi"),
        requirement("pydantic"),
    ],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]),
    deps = [
        ":cmk-fastapi",
        requirement("fastapi"),
        requirement("httpx2"),
        requirement("openapi-spec-validator"),
        requirement("pydantic"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-fastapi",
    strip_path_prefixes = ["packages/cmk-fastapi"],
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":cmk-fastapi",
        ":py_typed",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/fastapi/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":cmk-fastapi",
    ],
    requirements_in = "requirements.in",
)
