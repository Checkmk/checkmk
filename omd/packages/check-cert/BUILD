load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:make_deployable.bzl", "make_deployable_file")

genrule(
    name = "check-cert-strip",
    srcs = ["//packages/check-cert"],
    outs = ["check-cert.strip"],
    cmd = "strip -s $< -o $@",
)

make_deployable_file(
    name = "deployable_check-cert",
    src = ":check-cert-strip",
    out = "check-cert",
    rpath = "\\$ORIGIN/../../../lib",
    tags = ["manual"],
)

pkg_files(
    name = "check-cert_pkg",
    srcs = [":deployable_check-cert"],
    attributes = pkg_attributes(mode = "0755"),
    renames = {":deployable_check-cert": "lib/nagios/plugins/check_cert"},
    tags = ["manual"],
)

pkg_tar(
    name = "check-cert",
    srcs = [":check-cert_pkg"],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
