load("@rules_cc//cc:defs.bzl", "cc_library", "cc_test")

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
    copts = ["-O3"],
    includes = ["include"],
    visibility = ["//visibility:public"],
)

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
        ":livestatus_poller",
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
