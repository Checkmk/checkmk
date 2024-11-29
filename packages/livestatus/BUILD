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
    strip_include_prefix = "include/",
    visibility = ["//visibility:public"],
)

cc_library(
    name = "livestatus_headers",
    hdrs = glob(["include/livestatus/*.h"]),
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
    copts = ["-O3"],
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

cc_test(
    name = "test",
    size = "small",
    srcs = glob(["test/*.cc"]),
    deps = [
        ":livestatus_base",
        "@gtest//:gtest_main",
        "@re2",
    ],
)
