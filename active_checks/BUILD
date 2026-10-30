load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("//bazel/rules:pkg.bzl", "pkg_tar")
load("//bazel/rules:xcomp/cc.bzl", "cc_binary", "cc_library", "cc_test")

cc_library(
    name = "deadline",
    hdrs = ["deadline.h"],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
)

cc_library(
    name = "arguments",
    srcs = ["arguments.cc"],
    hdrs = ["arguments.h"],
    copts = [
        "-std=c++20",
        "-g",
        "-O3",
        "-Wall",
        "-Wextra",
    ],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
)

cc_test(
    name = "test_arguments",
    size = "small",
    srcs = ["test/test_arguments.cc"],
    copts = ["-std=c++20"],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    tags = ["cpp"],
    deps = [
        ":arguments",
        "@gtest//:gtest_main",
    ],
)

cc_library(
    name = "connection_schedule",
    srcs = ["connection_schedule.cc"],
    hdrs = ["connection_schedule.h"],
    copts = [
        "-std=c++20",
        "-g",
        "-O3",
        "-Wall",
        "-Wextra",
    ],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    deps = [":deadline"],
)

cc_test(
    name = "test_connection_schedule",
    size = "small",
    srcs = ["test/test_connection_schedule.cc"],
    copts = ["-std=c++20"],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    tags = ["cpp"],
    deps = [
        ":connection_schedule",
        ":deadline",
        "@gtest//:gtest_main",
    ],
)

cc_binary(
    name = "check_mkevents",
    srcs = ["check_mkevents.cc"],
    copts = [
        "-std=c++20",
        "-g",
        "-O3",
        "-Wall",
        "-Wextra",
    ],
    features = [
        "static_libstdcpp",
    ],
    linkopts = [
        "-pthread",
    ],
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    visibility = ["//tests/integration/active_checks:__pkg__"],
    deps = [
        ":arguments",
        ":connection_schedule",
        ":deadline",
    ],
)

pkg_files(
    name = "active_checks_bin",
    srcs = [
        ":check_always_crit",
        ":check_mkevents",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/nagios/plugins",
)

pkg_tar(
    name = "pkg_tar",
    srcs = [":active_checks_bin"],
    stamp = 1,
    visibility = ["//visibility:public"],
)

pkg_files(
    name = "check_always_crit_bin",
    srcs = [":check_always_crit"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/nagios/plugins",
)

pkg_tar(
    name = "check_always_crit_tar",
    srcs = [":check_always_crit_bin"],
    stamp = 1,
    visibility = ["//omd/non-free/relay:__pkg__"],
)

sh_library(
    name = "active_checks_sh",
    srcs = [
        "check_always_crit",
    ],
)
