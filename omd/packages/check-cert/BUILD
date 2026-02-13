load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")

genrule(
    name = "check-cert-strip",
    srcs = ["//packages/check-cert"],
    outs = ["check-cert.strip"],
    cmd = "strip -s $< -o $@",
)

set_runpath(
    name = "check_cert_runpath",
    srcs = [":check-cert-strip"],
    rpaths = ["$ORIGIN/../../../lib"],
    tags = ["manual"],
)

pkg_files(
    name = "check-cert_pkg",
    srcs = [":check_cert_runpath"],
    attributes = pkg_attributes(mode = "0755"),
    renames = {":check_cert_runpath": "lib/nagios/plugins/check_cert"},
    tags = ["manual"],
)

pkg_tar(
    name = "check-cert",
    srcs = [":check-cert_pkg"],
    stamp = 1,
    tags = ["manual"],
    visibility = ["//visibility:public"],
)
