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

short_editions = {
    "cloud": "cce",
    "enterprise": "cee",
    "managed": "cme",
    "raw": "cre",
    "saas": "cse",
}

[run_binary(
    name = "run_werks_precompile_" + edition,
    srcs = [
        # //.:werks warns for dependency checking of directories is unsound but
        # we only use it to get the path with $location
        # the real dependency is the //:werks_group filegroup
        "//:werks_group",
    ],
    outs = ["werks_precompiled_" + edition],
    args = [
        "precompile",
        "$(location //:werks_group)",
        "--filter-by-edition",
        short_editions[edition],
        "$(location werks_precompiled_%s)" % edition,
    ],
    tags = ["manual"],
    tool = ":werks_utils_binary",
) for edition in [
    "raw",
    "cloud",
    "enterprise",
    "managed",
    "saas",
]]

[run_binary(
    name = "run_changelog_" + edition,
    srcs = ["werks_precompiled_" + edition],
    outs = ["changelog_" + edition],
    args = [
        "changelog",
        "$(location changelog_%s)" % edition,
        "$(location werks_precompiled_%s)" % edition,
    ],
    tags = ["manual"],
    tool = ":werks_utils_binary",
    visibility = ["@@//omd:__subpackages__"],
) for edition in [
    "raw",
    "cloud",
    "enterprise",
    "managed",
    "saas",
]]

[pkg_files(
    name = "changelog_pkg_" + edition,
    srcs = [":changelog_" + edition],
    prefix = "share/doc/check_mk_" + edition,
    renames = {":changelog_" + edition: "ChangeLog"},
    tags = ["manual"],
) for edition in [
    "raw",
    "cloud",
    "enterprise",
    "managed",
    "saas",
]]

pkg_files(
    name = "werks_pkg_raw",
    srcs = [":werks_precompiled_raw"],
    prefix = "share/check_mk/werks",
    renames = {":werks_precompiled_raw": "werks"},
    tags = ["manual"],
)

[pkg_files(
    name = "werks_pkg_" + edition,
    srcs = [":werks_precompiled_" + edition],
    prefix = "share/check_mk/werks",
    renames = {":werks_precompiled_" + edition: "werks_" + edition},
    tags = ["manual"],
) for edition in [
    "cloud",
    "enterprise",
    "managed",
    "saas",
]]

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
        "changelog_pkg_raw",
        "werks_pkg_raw",
    ] + select({
        "@cmk//edition:raw": [],
        "@cmk//edition:enterprise": [
            "changelog_pkg_enterprise",
            "werks_pkg_enterprise",
        ],
        "@cmk//edition:cloud": [
            "changelog_pkg_cloud",
            "werks_pkg_cloud",
        ],
        "@cmk//edition:managed": [
            "changelog_pkg_managed",
            "werks_pkg_managed",
        ],
        "@cmk//edition:saas": [
            "changelog_pkg_saas",
            "werks_pkg_saas",
        ],
    }),
    tags = ["manual"],
    visibility = ["@@//omd:__subpackages__"],
)
