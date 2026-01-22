load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:define_from_flag.bzl", "define_from_flag")
load("//bazel/rules:xcomp/cc.bzl", "cc_library", "cc_test")

define_from_flag(
    name = "cmk_version_define",
    macro = "VERSION",
    value = "@cmk//version",
)

# Keep code using VERSION apart to minimize cache invalidation.
cc_library(
    name = "neb_version",
    srcs = ["src/CmkVersion.cc"],
    hdrs = ["include/neb/CmkVersion.h"],
    strip_include_prefix = "include/",
    deps = [":cmk_version_define"],
)

# Our generated & patched headers for Nagios 3 & 4
cc_library(
    name = "neb_nagios_headers",
    hdrs = glob(
        [
            "third_party/include/nagios/*.h",
            "third_party/include/nagios4/*.h",
        ],
    ),
    strip_include_prefix = "third_party/include/",
    tags = ["manual"],
)

cc_library(
    name = "neb_base",
    srcs = [
        "include/neb/CmkVersion.h",
        "src/MacroExpander.cc",
        "src/NebComment.cc",
        "src/NebCore.cc",
        "src/NebDowntime.cc",
        "src/NebHost.cc",
        "src/NebService.cc",
        "src/TimeperiodsCache.cc",
        "src/module.cc",
    ],
    hdrs = [
        "include/neb/Comment.h",
        "include/neb/Downtime.h",
        "include/neb/MacroExpander.h",
        "include/neb/NebComment.h",
        "include/neb/NebContact.h",
        "include/neb/NebContactGroup.h",
        "include/neb/NebCore.h",
        "include/neb/NebDowntime.h",
        "include/neb/NebGlobalFlags.h",
        "include/neb/NebHost.h",
        "include/neb/NebHostGroup.h",
        "include/neb/NebPaths.h",
        "include/neb/NebService.h",
        "include/neb/NebServiceGroup.h",
        "include/neb/NebTimeperiod.h",
        "include/neb/TimeperiodsCache.h",
        "include/neb/nagios.h",
    ],
    copts = [
        "-O3",
        "-std=c++20",
    ],
    strip_include_prefix = "include/",
    deps = [
        ":neb_nagios_headers",
        ":neb_version",
        "//packages/livestatus:livestatus_headers",
        "@asio",
    ],
)

cc_shared_library(
    name = "neb_shared",
    dynamic_deps = ["//packages/livestatus:livestatus_shared"],
    visibility = ["//visibility:public"],
    deps = [
        ":neb_base",
        ":neb_version",
    ],
)

pkg_files(
    name = "neb_shared_files",
    srcs = [":neb_shared"],
    prefix = "lib/mk-livestatus/",
    renames = {":neb_shared": "livestatus.o"},
)

pkg_tar(
    name = "neb_pkg",
    srcs = [":neb_shared_files"],
    stamp = 1,
    visibility = ["//visibility:public"],
)

alias(
    name = "neb",
    actual = "neb_shared",
    visibility = ["//visibility:public"],
)

cc_library(
    name = "test_utilities",
    testonly = 1,
    srcs = [
        "test/test_utilities.cc",
    ],
    hdrs = ["test/test_utilities.h"],
    deps = [
        ":neb_base",
        ":neb_version",
        "//packages/livestatus:livestatus_base",
    ],
)

cc_library(
    name = "dummy_nagios",
    testonly = 1,
    srcs = ["test/DummyNagios.cc"],
    deps = [
        ":neb_base",
        ":neb_version",
    ],
)

cc_test(
    name = "test",
    size = "small",
    srcs = [
        "test/test_CrashReport.cc",
        "test/test_DictFilter.cc",
        "test/test_MacroExpander.cc",
    ],
    copts = [
        "-std=c++20",
    ],
    tags = ["cpp"],
    deps = [
        ":dummy_nagios",
        ":test_utilities",
        "@gtest//:gtest_main",
    ],
)
