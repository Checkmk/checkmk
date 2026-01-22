load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
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

pkg_files(
    name = "unixcat_pkg",
    srcs = [
        ":unixcat",
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
    tags = ["cpp"],
    deps = [":unixcat"],
)
