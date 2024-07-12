load("@rules_cc//cc:defs.bzl", "cc_library", "cc_test")

cc_library(
    name = "lspoller",
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
    copts = ["-O3"],
    includes = ["include"],
    visibility = ["//visibility:public"],
)

# CC=/usr/bin/gcc-13 bazel build //packages/livestatus
cc_library(
    name = "livestatus",
    srcs = glob(
        ["src/*.cc"],
        exclude = [
            "src/Logger.cc",
            "src/POSIXUtils.cc",
        ],
    ),
    hdrs = glob(["include/livestatus/*.h"]),
    copts = [
        "-Iexternal/re2",
        "-O3",
    ],
    includes = ["include"],
    local_defines = [
        "HAVE_RE2",
        "ASIO_DISABLE_CONCEPTS",
        "ASIO_NO_DEPRECATED",
    ],
    visibility = ["//visibility:public"],
    deps = [
        ":lspoller",
        "@asio",
        "@re2",
        # rrdgraph for rrd_xport
        "@rrdtool_native//:rrdgraph",
    ],
)

cc_shared_library(
    name = "livestatus_shared",
    deps = [":livestatus"],
)

# CC=/usr/bin/gcc-13 bazel test --test_output=all //packages/livestatus:all
cc_test(
    name = "test",
    size = "small",
    testonly = 1,
    srcs = glob(["test/*.cc"]),
    copts = [
        "-Iexternal/re2",
        "-O3",
    ],
    deps = [
        ":livestatus",
        "@gtest//:gtest_main",
        "@re2",
    ],
)
