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
    # Our headers include Asio, so everybody including them must configure
    # Asio the same way, otherwise we violate the one definition rule.
    defines = [
        "ASIO_DISABLE_CONCEPTS",
        "ASIO_NO_DEPRECATED",
    ],
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
    local_defines = ["HAVE_RE2"],
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
    srcs = glob([
        "test/*.cc",
        "test/*.h",
    ]),
    deps = [
        ":livestatus_base",
        "@googletest//:gtest",
        "@re2",
    ],
)
