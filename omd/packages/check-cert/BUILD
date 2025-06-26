load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:make_deployable.bzl", "make_deployable_file")

make_deployable_file(
    name = "deployable_check-cert",
    src = "//packages/check-cert",
    out = "check-cert",
    rpath = "\\$ORIGIN/../../../lib",
)

pkg_files(
    name = "check-cert_pkg",
    srcs = [":deployable_check-cert"],
    attributes = pkg_attributes(mode = "0755"),
    renames = {":deployable_check-cert": "lib/nagios/plugins/check_cert"},
)

pkg_tar(
    name = "check-cert",
    srcs = [":check-cert_pkg"],
    visibility = ["//visibility:public"],
)
