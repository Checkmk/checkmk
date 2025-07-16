load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "pkg_mklink")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

[pkg_files(
    name = "changelog_pkg_" + edition,
    srcs = ["//omd:changelog_" + edition],
    prefix = "share/doc/check_mk" + postfix,
    renames = {"//omd:changelog_" + edition: "ChangeLog"},
) for (edition, postfix) in [
    ("cre", ""),
    ("cce", "_cloud"),
    ("cee", "_enterprise"),
    ("cme", "_managed"),
    ("cse", "_saas"),
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
    ] + select({
        "//bazel/cmk/edition:cre": [],
        "//bazel/cmk/edition:cee": ["changelog_pkg_cee"],
        "//bazel/cmk/edition:cce": ["changelog_pkg_cce"],
        "//bazel/cmk/edition:cme": ["changelog_pkg_cme"],
        "//bazel/cmk/edition:cse": ["changelog_pkg_cse"],
    }),
    visibility = ["@@//omd:__subpackages__"],
)
