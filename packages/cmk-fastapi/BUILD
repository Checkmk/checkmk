load("@aspect_rules_py//py:defs.bzl", "py_library", "py_pytest_main", "py_test")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
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

py_pytest_main(
    name = "__test__",
    deps = [requirement("pytest")],
)

py_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]) + [":__test__.py"],
    main = "__test__.py",
    deps = [
        ":__test__",
        ":cmk-fastapi",
        requirement("fastapi"),
        requirement("httpx2"),
        requirement("pydantic"),
        requirement("pytest"),
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
