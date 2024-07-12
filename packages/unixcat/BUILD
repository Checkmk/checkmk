load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_test")

cc_binary(
    name = "unixcat",
    srcs = ["src/unixcat.cc"],
    copts = [
        "-fPIC",
        "-gdwarf-4",
        "-O3",
    ],
    linkopts = [
        "-pthread",
    ],
    deps = [
        "//packages/livestatus:lspoller",
    ],
)

cc_test(
    name = "test",
    size = "small",
    testonly = 1,
    srcs = ["test/test.cc"],
    deps = [":unixcat"],
)
