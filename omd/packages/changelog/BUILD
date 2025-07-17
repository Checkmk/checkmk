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
)

py_binary(
    name = "werks_utils_binary",
    srcs = [":werks_utils.py"],
    deps = ["//packages/cmk-werks"],
)

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
        edition,
        "$(location werks_precompiled_%s)" % edition,
    ],
    tool = ":werks_utils_binary",
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
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
    tool = ":werks_utils_binary",
    visibility = ["@@//omd:__subpackages__"],
) for edition in [
    "cre",
    "cce",
    "cee",
    "cme",
    "cse",
]]

[pkg_files(
    name = "changelog_pkg_" + edition,
    srcs = [":changelog_" + edition],
    prefix = "share/doc/check_mk" + postfix,
    renames = {":changelog_" + edition: "ChangeLog"},
) for (edition, postfix) in [
    ("cre", ""),
    ("cce", "_cloud"),
    ("cee", "_enterprise"),
    ("cme", "_managed"),
    ("cse", "_saas"),
]]

pkg_files(
    name = "werks_pkg_cre",
    srcs = [":werks_precompiled_cre"],
    prefix = "share/check_mk/werks",
    renames = {":werks_precompiled_cre": "werks"},
)

[pkg_files(
    name = "werks_pkg_" + edition,
    srcs = [":werks_precompiled_" + edition],
    prefix = "share/check_mk/werks",
    renames = {":werks_precompiled_" + edition: "werks_" + edition},
) for edition in [
    "cce",
    "cee",
    "cme",
    "cse",
]]

pkg_mklink(
    name = "changelog_link",
    link_name = "share/doc/ChangeLog",
    target = "check_mk/ChangeLog",
)

pkg_tar(
    name = "changelog",
    srcs = [
        "changelog_link",
        "changelog_pkg_cre",
        "werks_pkg_cre",
    ] + select({
        "//bazel/cmk/edition:cre": [],
        "//bazel/cmk/edition:cee": [
            "changelog_pkg_cee",
            "werks_pkg_cee",
        ],
        "//bazel/cmk/edition:cce": [
            "changelog_pkg_cce",
            "werks_pkg_cce",
        ],
        "//bazel/cmk/edition:cme": [
            "changelog_pkg_cme",
            "werks_pkg_cme",
        ],
        "//bazel/cmk/edition:cse": [
            "changelog_pkg_cse",
            "werks_pkg_cse",
        ],
    }),
    visibility = ["@@//omd:__subpackages__"],
)
