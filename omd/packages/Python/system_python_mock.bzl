# This repository rule creates `@system_python//:version.bzl` and the
# `none` target (config_setting).
# This is necessery to build protobuf, as protobuf is per default built
# with the system python.
# We register our own `@python//:python` and register it as toolchain

load("@omd_packages//:package_versions.bzl", "PYTHON_MAJOR_DOT_MINOR", "PYTHON_VERSION_MAJOR", "PYTHON_VERSION_MINOR")

build_file = """
load("@bazel_skylib//rules:common_settings.bzl", "string_flag")

string_flag(
    name = "internal_python_support",
    build_setting_default = "None",
    values = [
        "None",
    ]
)

config_setting(
    name = "none",
    flag_values = {
        ":internal_python_support": "Supported",
    },
    visibility = ["//visibility:public"],
)
"""

def _system_python_impl(repository_ctx):
    repository_ctx.file("BUILD.bazel", build_file)
    repository_ctx.file("version.bzl", "SYSTEM_PYTHON_VERSION = '{}{}'".format(PYTHON_VERSION_MAJOR, PYTHON_VERSION_MINOR))

system_python = repository_rule(
    implementation = _system_python_impl,
    local = True,
    attrs = {
        "minimum_python_version": attr.string(default = PYTHON_MAJOR_DOT_MINOR),
    },
)
