load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_test")

cc_binary(
    name = "unixcat",
    srcs = ["src/unixcat.cc"],
    copts = ["-O3"],
    linkopts = [
        "-pthread",
    ],
    deps = [
        "//packages/livestatus:livestatus_poller",
    ],
)

cc_test(
    name = "test",
    size = "small",
    srcs = ["test/test.cc"],
    deps = [":unixcat"],
)
