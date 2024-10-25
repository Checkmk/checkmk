load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@omd_packages//omd/packages/rules:package_wheel.bzl", "package_wheel")
load("@rules_python//python:packaging.bzl", "py_wheel")

exports_files([
    "pyproject.toml",
    "requirements.txt",
])

# TODO: VERSION is duplicated in pyproject.toml
VERSION = "1.0.0"

py_library(
    name = "cmk-livestatus-client",
    srcs = ["cmk/livestatus_client/__init__.py"],
    imports = ["."],
    visibility = ["//cmk:__pkg__"],
)

py_library(
    name = "py_livestatus",
    srcs = ["livestatus/__init__.py"],
    imports = ["."],
    visibility = [
        "//cmk:__pkg__",
        "//tests:__subpackages__",
    ],
    deps = [":cmk-livestatus-client"],
)

py_wheel(
    name = "cmk-livestatus-client_whl",
    distribution = "cmk-livestatus-client",
    strip_path_prefixes = ["packages/cmk-livestatus-client"],
    version = VERSION,
    deps = [
        ":cmk-livestatus-client",
    ],
)

py_wheel(
    name = "livestatus_whl",
    distribution = "livestatus",
    strip_path_prefixes = ["packages/cmk-livestatus-client"],
    version = VERSION,
    deps = [":py_livestatus"],
)

package_wheel(
    name = "cmk_livestatus_client_pkg_tar",
    visibility = ["//visibility:public"],
    whl = "cmk-livestatus-client_whl",
)

package_wheel(
    name = "cmk_livestatus_pkg_tar",
    visibility = ["//visibility:public"],
    whl = "livestatus_whl",
)
