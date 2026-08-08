load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_python//python:packaging.bzl", "py_wheel")
load("//bazel/rules:doctest.bzl", "py_doc_test")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:package_wheel.bzl", "package_wheel")
load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:py_requirements_test.bzl", "py_requirements_test")
load("//bazel/rules:replace_string_in_file.bzl", "replace_string_in_file")

exports_files([
    "dev-requirements.in",
    "pyproject.toml",
    "requirements.in",
])

py_library(
    name = "livestatus-connection",
    srcs = [
        "cmk/livestatus_client/_connection.py",
    ],
    imports = ["."],
    deps = [
        "//packages/cmk-ccc:site",
        "//packages/cmk-ccc:user",
        "//packages/cmk-trace",
    ],
)

py_library(
    name = "livestatus-api",
    srcs = [
        "cmk/livestatus_client/_api/__init__.py",
        "cmk/livestatus_client/_api/client.py",
        "cmk/livestatus_client/_api/commands.py",
        "cmk/livestatus_client/expressions.py",
        "cmk/livestatus_client/queries.py",
        "cmk/livestatus_client/testing.py",
        "cmk/livestatus_client/types.py",
    ] + glob([
        "cmk/livestatus_client/tables/*.py",
    ]),
    imports = ["."],
    visibility = ["//tests:__subpackages__"],
    deps = [
        ":livestatus-connection",
        "//packages/cmk-ccc:hostaddress",
        requirement("jinja2"),
    ],
)

py_library(
    name = "cmk-livestatus-client",
    srcs = [
        "cmk/livestatus_client/__init__.py",
    ],
    data = ["cmk/livestatus_client/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [
        ":livestatus-api",
        ":livestatus-connection",
    ],
)

# Deprecated compatibility shim for the old 'livestatus' module name, announced
# in werk #20119. To be removed in a future version of Checkmk (after 3.0),
# together with the "livestatus_whl" wheel below.
py_library(
    name = "py_livestatus",
    srcs = ["livestatus/__init__.py"],
    data = ["livestatus/py.typed"],
    imports = ["."],
    visibility = ["//visibility:public"],
    deps = [":cmk-livestatus-client"],
)

py_library(
    name = "examples",
    srcs = [
        "example_api.py",
        "example_multisite.py",
        "example_singlesite.py",
    ],
    imports = ["."],
    deps = [
        ":py_livestatus",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:user",
    ],
)

# The livedump command line tool. Not part of the cmk.livestatus_client
# library or its wheel; it is shipped as bin/livedump via the package tar.
py_library(
    name = "livedump",
    srcs = ["livedump.py"],
    imports = ["."],
    deps = [":cmk-livestatus-client"],
)

# Stamp the shipped livedump with the actual version, like bin/omd does.
replace_string_in_file(
    name = "livedump_version_in",
    src = "livedump.py",
    out = "livedump_in.py",
    replace_dict = {'__version__ = "UNSET"': '__version__ = "{CMK_VERSION}"'},
)

file_from_flag(
    name = "livedump_versioned",
    src = "livedump_version_in",
    out = "livedump_bin.py",
    replace_labels = {"CMK_VERSION": "@cmk//version"},
)

pkg_files(
    name = "livedump_bin",
    srcs = [":livedump_versioned"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    renames = {"livedump_bin.py": "bin/livedump"},
)

py_doc_test(
    name = "doctest",
    size = "small",
    srcs = [
        "cmk-livestatus-client",
        "livestatus-api",
        "livestatus-connection",
    ],
)

py_cmk_test(
    name = "unit",
    size = "small",
    srcs = glob(["tests/**/*.py"]),
    deps = [
        ":cmk-livestatus-client",
    ],
)

py_wheel(
    name = "cmk-livestatus-client_whl",
    distribution = "cmk-livestatus-client",
    strip_path_prefixes = ["packages/cmk-livestatus-client"],
    # TODO: VERSION is duplicated in pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":cmk-livestatus-client",
        ":cmk_livestatus_client_py_typed",
        ":livestatus-api",
        ":livestatus-connection",
    ],
)

build_test(
    name = "build_test",
    targets = ["cmk-livestatus-client_whl"],
)

filegroup(
    name = "cmk_livestatus_client_py_typed",
    srcs = ["cmk/livestatus_client/py.typed"],
)

py_wheel(
    name = "livestatus_whl",
    distribution = "livestatus",
    strip_path_prefixes = ["packages/cmk-livestatus-client"],
    # TODO: VERSION is duplicated in pyproject.toml
    version = "1.0.0",
    visibility = ["//visibility:public"],
    deps = [
        ":livestatus_py_typed",
        ":py_livestatus",
    ],
)

filegroup(
    name = "livestatus_py_typed",
    srcs = ["livestatus/py.typed"],
)

package_wheel(
    name = "cmk_livestatus_client_pkg_tar",
    additional_files = [":livedump_bin"],
    visibility = ["//visibility:public"],
    whl = "cmk-livestatus-client_whl",
)

package_wheel(
    name = "cmk_livestatus_pkg_tar",
    visibility = ["//visibility:public"],
    whl = "livestatus_whl",
)

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
        "run",
    ],
)

py_requirements_test(
    name = "requirements-test",
    libs = [
        ":cmk-livestatus-client",
        ":examples",
        ":livedump",
    ],
    requirements_in = "requirements.in",
)
