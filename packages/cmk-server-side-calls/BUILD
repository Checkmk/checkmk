load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")
load("@rules_python//python:packaging.bzl", "py_wheel")

exports_files([
    "pyproject.toml",
    "requirements.txt",
])

py_library(
    name = "cmk-server-side-calls",
    srcs = [
        "cmk/server_side_calls/__init__.py",
        "cmk/server_side_calls/v1/__init__.py",
        "cmk/server_side_calls/v1/_active_checks.py",
        "cmk/server_side_calls/v1/_special_agents.py",
        "cmk/server_side_calls/v1/_utils.py",
    ],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
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

package_wheel(
    name = "pkg_tar",
    visibility = ["//visibility:public"],
    whl = "wheel",
)
