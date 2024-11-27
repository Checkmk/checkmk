load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:package_wheel.bzl", "package_wheel")

exports_files([
    "pyproject.toml",
    "requirements.txt",
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
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
    deps = [
        requirement("pika"),
        requirement("pydantic"),
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-messaging",
    strip_path_prefixes = ["packages/cmk-messaging"],
    # TODO: Duplicated from pyproject.toml
    version = "0.1.0",
    deps = [
        ":cmk-messaging",
    ],
)

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
