load("@rules_cc//cc:defs.bzl", "cc_library", "cc_test")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "pkg_mklink")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

cc_library(
    name = "livestatus_poller",
    srcs = [
        "src/Logger.cc",
        "src/POSIXUtils.cc",
    ],
    hdrs = [
        "include/livestatus/BitMask.h",
        "include/livestatus/ChronoUtils.h",
        "include/livestatus/Logger.h",
        "include/livestatus/POSIXUtils.h",
        "include/livestatus/Poller.h",
    ],
    copts = [
        "-O3",
        "-std=c++20",
    ],
    strip_include_prefix = "include/",
    visibility = ["//visibility:public"],
)

cc_library(
    name = "livestatus_headers",
    hdrs = glob(["include/livestatus/*.h"]),
    copts = ["-std=c++20"],
    strip_include_prefix = "include/",
    visibility = ["//visibility:public"],
    deps = ["@asio"],
)

cc_library(
    name = "livestatus_base",
    srcs = glob(
        ["src/*.cc"],
        exclude = [
            "src/Logger.cc",
            "src/POSIXUtils.cc",
        ],
    ),
    copts = [
        "-O3",
        "-std=c++20",
    ],
    local_defines = [
        "HAVE_RE2",
        "ASIO_DISABLE_CONCEPTS",
        "ASIO_NO_DEPRECATED",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":livestatus_headers",
        ":livestatus_poller",
        "@asio",
        "@re2",
    ],
)

cc_shared_library(
    name = "livestatus_shared",
    shared_lib_name = "liblivestatus.so",
    visibility = ["//visibility:public"],
    deps = [
        ":livestatus_base",
        "@re2",
    ],
)

pkg_files(
    name = "livestatus_shared_files",
    srcs = [":livestatus_shared"],
    prefix = "lib",
    renames = {":livestatus_shared": "liblivestatus.so.0.1"},
)

pkg_mklink(
    name = "liblivestatus.so.0",
    link_name = "lib/liblivestatus.so.0",
    target = "liblivestatus.so.0.1",
)

pkg_mklink(
    name = "liblivestatus.so",
    link_name = "lib/liblivestatus.so",
    target = "liblivestatus.so.0.1",
)

pkg_tar(
    name = "livestatus_pkg",
    srcs = [
        "liblivestatus.so",
        "liblivestatus.so.0",
        ":livestatus_shared_files",
    ],
    visibility = ["//visibility:public"],
)

cc_test(
    name = "test",
    size = "small",
    srcs = glob(["test/*.cc"]),
    copts = ["-std=c++20"],
    deps = [
        ":livestatus_base",
        "@gtest//:gtest_main",
        "@re2",
    ],
)
