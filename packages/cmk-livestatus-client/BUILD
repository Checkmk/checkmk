load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")
load("@rules_python//python:packaging.bzl", "py_wheel")

py_library(
    name = "cmk-livestatus-client",
    srcs = [
        "cmk/livestatus_client/__init__.py",
        "livestatus/__init__.py",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-livestatus-client",
    strip_path_prefixes = ["packages/cmk-livestatus-client"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-livestatus-client",
    ],
)

package_wheel(wheel_target = "wheel")
