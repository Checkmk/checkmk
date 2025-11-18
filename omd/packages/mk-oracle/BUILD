load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

pkg_files(
    name = "mk-oracle_pkg",
    # HACK
    # * mk-oracle needs to be build against an old glibc version to run on older systems
    # * that's why we pre-built it on a rhel8 before-hand and put it in the workspace
    # * see package_helper.groovy
    srcs = [":mk-oracle.rhel8"],
    attributes = pkg_attributes(mode = "0755"),
    renames = {":mk-oracle.rhel8": "lib/python3/cmk/plugins/oracle/agents/mk-oracle"},
    tags = ["manual"],
)

pkg_tar(
    name = "mk-oracle",
    srcs = [":mk-oracle_pkg"],
    tags = ["manual"],
    visibility = ["//omd:__subpackages__"],
)
