load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")

py_library(
    name = "cmk-server-side-calls",
    srcs = [
        "cmk/server_side_calls/__init__.py",
        "cmk/server_side_calls/v1/__init__.py",
        "cmk/server_side_calls/v1/_active_checks.py",
        "cmk/server_side_calls/v1/_special_agents.py",
        "cmk/server_side_calls/v1/_utils.py",
    ],
)

py_wheel(
    name = "wheel",
    distribution = "cmk-server-side-calls",
    strip_path_prefixes = ["packages/cmk-server-side-calls"],
    # TODO: Duplicated from pyproject.toml
    version = "1.0.0",
    deps = [
        ":cmk-server-side-calls",
    ],
)

package_wheel(wheel_target = "wheel")
