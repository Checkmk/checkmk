load("//bazel/rules:py_cmk_test.bzl", "py_cmk_test")
load("//bazel/rules:xcomp/cc.bzl", "cc_binary")

cc_binary(
    name = "fake_network.so",
    testonly = True,
    srcs = ["fake_network.c"],
    linkopts = [
        # Without it, the toolchain makes the library depend on libstdc++.
        "-Wl,--as-needed",
        "-ldl",
    ],
    linkshared = True,
    local_defines = ["_GNU_SOURCE"],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
)

py_cmk_test(
    name = "active_checks",
    size = "medium",
    srcs = glob(["*.py"]),
    args = ["tests/integration/active_checks"],
    data = [
        ":fake_network.so",
        "//active_checks:check_mkevents",
    ],
    env = {
        "CHECK_MKEVENTS": "$(rootpath //active_checks:check_mkevents)",
        "FAKE_NETWORK": "$(rootpath :fake_network.so)",
    },
    deps = ["//packages/cmk-ec"],
)
