load("@rules_cc//cc:defs.bzl", "cc_library", "cc_test")

# CC=/usr/bin/gcc-13 bazel build //packages/livestatus
cc_library(
    name = "livestatus",
    srcs = glob(["src/*.cc"]),
    hdrs = glob(["include/livestatus/*.h"]),
    copts = [
        "-std=c++20",
        "-Iexternal/re2",
        "-DHAVE_RE2",
        "-DASIO_DISABLE_CONCEPTS",
        "-DASIO_NO_DEPRECATED",
        "-fPIC",
        "-gdwarf-4",
        "-O3",
    ],
    includes = ["include"],
    visibility = ["//visibility:public"],
    deps = [
        "@asio",
        "@re2",
        "@rrdtool",
    ],
)

# CC=/usr/bin/gcc-13 bazel test --test_output=all //packages/livestatus:all
cc_test(
    name = "test",
    testonly = 1,
    srcs = glob(["test/*.cc"]),
    copts = [
        "-std=c++20",
        "-Iexternal/re2",
        "-fPIC",
        "-gdwarf-4",
        "-O3",
    ],
    deps = [
        ":livestatus",
        "@gtest//:gtest_main",
        "@re2",
    ],
)
