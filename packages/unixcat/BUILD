load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_test")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

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
    visibility = ["//omd:__pkg__"],
)

cc_test(
    name = "test",
    size = "small",
    srcs = ["test/test.cc"],
    deps = [":unixcat"],
)
