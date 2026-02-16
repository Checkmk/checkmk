load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:patchelf.bzl", "set_runpath")
load("//bazel/rules:xcomp/cc.bzl", "cc_binary", "cc_test")

cc_binary(
    name = "unixcat",
    srcs = ["src/unixcat.cc"],
    copts = [
        "-std=c++20",
        "-O3",
    ],
    linkopts = [
        "-pthread",
    ],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/livestatus:livestatus_poller",
    ],
)

set_runpath(
    name = "unixcat-runpath",
    srcs = [":unixcat"],
    rpaths = ["$ORIGIN/../lib"],
    tags = ["manual"],
)

pkg_files(
    name = "unixcat_pkg",
    srcs = [
        ":unixcat-runpath",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
)

pkg_tar(
    name = "unixcat_tar",
    srcs = [
        ":unixcat_pkg",
    ],
    stamp = 1,
    visibility = ["//omd:__pkg__"],
)

cc_test(
    name = "test",
    size = "small",
    srcs = ["test/test.cc"],
    deps = [":unixcat"],
)
