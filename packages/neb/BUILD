load("@rules_cc//cc:defs.bzl", "cc_library", "cc_test")

CMK_VERSION = "2.4.0b1"

# Keep code using VERSION apart to minimize cache invalidation.
cc_library(
    name = "neb_version",
    srcs = ["src/CmkVersion.cc"],
    hdrs = ["include/neb/CmkVersion.h"],
    includes = ["include"],
    local_defines = [r'VERSION=\"' + CMK_VERSION + r'\"'],
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
    includes = ["third_party/include"],
    tags = ["no-clang-tidy"],
)

cc_library(
    name = "neb_base",
    srcs = [
        "include/neb/CmkVersion.h",
        "src/MacroExpander.cc",
        "src/NebCore.cc",
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
    copts = ["-O3"],
    includes = ["include"],
    deps = [
        ":neb_nagios_headers",
        "//packages/livestatus",
    ],
)

cc_library(
    name = "neb",
    includes = ["include"],
    deps = [
        ":neb_base",
        ":neb_nagios_headers",
        ":neb_version",
        "//packages/livestatus",
    ],
)

cc_shared_library(
    name = "neb_shared",
    visibility = ["//visibility:public"],
    deps = [":neb"],
)

cc_library(
    name = "test_utilities",
    testonly = 1,
    srcs = [
        "test/test_utilities.cc",
    ],
    hdrs = ["test/test_utilities.h"],
    deps = [
        ":neb",
        "//packages/livestatus",
    ],
)

cc_library(
    name = "dummy_nagios",
    testonly = 1,
    srcs = ["test/DummyNagios.cc"],
    hdrs = ["test/DummyNagios.cc"],
    deps = [":neb"],
)

cc_test(
    name = "test",
    size = "small",
    srcs = [
        "test/test_CrashReport.cc",
        "test/test_DictFilter.cc",
        "test/test_MacroExpander.cc",
    ],
    deps = [
        ":dummy_nagios",
        ":neb",
        ":test_utilities",
        "@gtest//:gtest_main",
    ],
)
