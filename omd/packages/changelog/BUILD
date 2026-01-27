load("@aspect_rules_py//py:defs.bzl", "py_binary")
load("@bazel_skylib//rules:run_binary.bzl", "run_binary")
load("@bazel_skylib//rules:write_file.bzl", "write_file")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "pkg_mklink")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

write_file(
    name = "werks_utils",
    out = "werks_utils.py",
    content = [
        "import runpy",
        "runpy.run_module('cmk.werks.utils', run_name=('__main__'))",
    ],
    tags = ["manual"],
)

py_binary(
    name = "werks_utils_binary",
    srcs = [":werks_utils.py"],
    tags = ["manual"],
    deps = ["//packages/cmk-werks"],
)

run_binary(
    name = "run_werks_precompile",
    srcs = [
        "//:werks_group",
    ],
    outs = ["werks_precompiled"],
    args = [
        "precompile",
        "$(location //:werks_group)",
        "--filter-by-edition",
    ] + select({
        "@cmk//edition:cloud": ["cloud"],
        "@cmk//edition:community": ["community"],
        "@cmk//edition:pro": ["pro"],
        "@cmk//edition:ultimate": ["ultimate"],
        "@cmk//edition:ultimatemt": ["ultimatemt"],
    }) + [
        "$(location werks_precompiled)",
    ],
    tags = ["manual"],
    tool = ":werks_utils_binary",
)

run_binary(
    name = "run_changelog",
    srcs = ["werks_precompiled"],
    outs = ["changelog_file"],
    args = [
        "changelog",
        "$(location changelog_file)",
        "$(location werks_precompiled)",
    ],
    tags = ["manual"],
    tool = ":werks_utils_binary",
    visibility = ["@@//omd:__subpackages__"],
)

pkg_files(
    name = "changelog_pkg",
    srcs = [":changelog_file"],
    prefix = select({
        "@cmk//edition:cloud": "share/doc/check_mk_cloud",
        "@cmk//edition:community": "share/doc/check_mk_community",
        "@cmk//edition:pro": "share/doc/check_mk_pro",
        "@cmk//edition:ultimate": "share/doc/check_mk_ultimate",
        "@cmk//edition:ultimatemt": "share/doc/check_mk_ultimatemt",
    }),
    renames = {":changelog_file": "ChangeLog"},
    tags = ["manual"],
)

# Create edition-specific werks files with proper naming
pkg_files(
    name = "werks_pkg_base",
    srcs = [":werks_precompiled"],
    prefix = "share/check_mk/werks",
    renames = {":werks_precompiled": "werks"},
    tags = ["manual"],
)

pkg_files(
    name = "werks_pkg_editions",
    srcs = [":werks_precompiled"],
    prefix = "share/check_mk/werks",
    renames = select({
        "@cmk//edition:community": {},
        "@cmk//edition:pro": {":werks_precompiled": "werks_pro"},
        "@cmk//edition:ultimate": {":werks_precompiled": "werks_ultimate"},
        "@cmk//edition:ultimatemt": {":werks_precompiled": "werks_ultimatemt"},
        "@cmk//edition:cloud": {":werks_precompiled": "werks_cloud"},
    }),
    tags = ["manual"],
)

pkg_mklink(
    name = "changelog_link",
    link_name = "share/doc/ChangeLog",
    tags = ["manual"],
    target = "check_mk/ChangeLog",
)

pkg_tar(
    name = "changelog",
    srcs = [
        "changelog_link",
        "changelog_pkg",
    ] + select({
        "@cmk//edition:community": ["werks_pkg_base"],
        "//conditions:default": [
            "werks_pkg_base",
            "werks_pkg_editions",
        ],
    }),
    stamp = 1,
    tags = ["manual"],
    visibility = ["@@//omd:__subpackages__"],
)
