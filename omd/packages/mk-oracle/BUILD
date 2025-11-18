load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "mk-oracle_pkg",
    srcs = ["//packages/mk-oracle"],
    attributes = pkg_attributes(mode = "0755"),
    renames = {"//packages/mk-oracle:mk-oracle": "lib/python3/cmk/plugins/oracle/agents/mk-oracle"},
    tags = ["manual"],
)

pkg_tar(
    name = "mk-oracle",
    srcs = [":mk-oracle_pkg"],
    tags = ["manual"],
    visibility = ["//omd:__subpackages__"],
)
