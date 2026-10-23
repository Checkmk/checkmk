load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("//bazel/rules:pkg.bzl", "pkg_tar")
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
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    tags = ["no-lint"],
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
    stamp = 1,
    visibility = ["//visibility:public"],
)

pkg_files(
    name = "check_always_crit_bin",
    srcs = [":check_always_crit"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/nagios/plugins",
)

pkg_tar(
    name = "check_always_crit_tar",
    srcs = [":check_always_crit_bin"],
    stamp = 1,
    visibility = ["//omd/non-free/relay:__pkg__"],
)

sh_library(
    name = "active_checks_sh",
    srcs = [
        "check_always_crit",
    ],
)
