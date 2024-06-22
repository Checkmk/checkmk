load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_test")

cc_binary(
    name = "unixcat",
    srcs = ["src/unixcat.cc"],
    copts = [
        "-std=c++20",
        "-fPIC",
        "-gdwarf-4",
        "-O3",
    ],
    deps = [
        "//packages/livestatus",
        "@re2",
    ],
)

cc_test(
    name = "test",
    testonly = 1,
    srcs = ["test/test.cc"],
    deps = [":unixcat"],
)
