load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")

py_library(
    name = "cmk-messaging",
    srcs = [
        "cmk/messaging/__init__.py",
        "cmk/messaging/_config.py",
        "cmk/messaging/_connection.py",
        "cmk/messaging/_constants.py",
        "cmk/messaging/rabbitmq.py",
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

package_wheel(wheel_target = "wheel")
