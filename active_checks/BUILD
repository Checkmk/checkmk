load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:xcomp/cc.bzl", "cc_binary")

cc_binary(
    name = "check_mkevents",
    srcs = ["check_mkevents.cc"],
    copts = [
        "-g",
        "-O3",
        "-Wall",
        "-Wextra",
    ],
    features = [
        "static_libstdcpp",
    ],
)

pkg_files(
    name = "active_checks_bin",
    srcs = [
        ":check_always_crit",
        ":check_mkevents",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/nagios/plugins",
)

pkg_tar(
    name = "pkg_tar",
    srcs = [":active_checks_bin"],
    visibility = ["//visibility:public"],
)
