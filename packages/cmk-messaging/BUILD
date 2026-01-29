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
    name = "cmk-messaging",
    srcs = [
        "cmk/messaging/__init__.py",
        "cmk/messaging/_config.py",
        "cmk/messaging/_connection.py",
        "cmk/messaging/_constants.py",
        "cmk/messaging/_logging.py",
        "cmk/messaging/rabbitmq.py",
    ],
    data = ["cmk/messaging/py.typed"],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        requirement("pika"),
        requirement("pydantic"),
        "//packages/cmk-ccc:site",
    ],
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = ["cmk-messaging"],
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
        ":cmk-messaging",
        requirement("pika"),
        requirement("pytest"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-messaging",
    strip_path_prefixes = ["packages/cmk-messaging"],
    # TODO: Duplicated from pyproject.toml
    version = "0.1.0",
    deps = [
        "py_typed",
        ":cmk-messaging",
    ],
)

build_test(
    name = "build_test",
    targets = ["wheel"],
)

filegroup(
    name = "py_typed",
    srcs = ["cmk/messaging/py.typed"],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
