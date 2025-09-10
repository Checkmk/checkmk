load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:make_deployable.bzl", "make_deployable_file")

make_deployable_file(
    name = "deployable_mk-oracle",
    src = "//packages/mk-oracle:mk-oracle-musl",
    out = "mk-oracle",
    rpath = "\\$ORIGIN/../../../share",
    tags = ["manual"],
)

pkg_files(
    name = "mk-oracle_pkg",
    srcs = [":deployable_mk-oracle"],
    attributes = pkg_attributes(mode = "0755"),
    renames = {":deployable_mk-oracle": "share/check_mk/agents/linux/mk-oracle"},
    tags = ["manual"],
)

pkg_tar(
    name = "mk-oracle",
    srcs = [":mk-oracle_pkg"],
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
