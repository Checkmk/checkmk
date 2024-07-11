load("@rules_cc//cc:defs.bzl", "cc_library", "cc_test")
load("//omd/packages/rules:version.bzl", "mangle_version")

CMK_VERSION = "2.4.0b1"

NEB_COPTS = [
    "-std=c++20",
    "-Ipackages/neb/third_party/include/",
    "-gdwarf-4",
    "-O3",
]

filegroup(
    name = "all_hdrs",
    srcs = glob(
        ["include/neb/*.h"],
    ) + glob(
        # patched nagios headers
        ["third_party/include/nagios/*.h"],
    ),
)

# Keep code using VERSION apart to minimize cache invalidation.
cc_library(
    name = "neb_version",
    srcs = ["src/CmkVersion.cc"],
    hdrs = ["include/neb/CmkVersion.h"],
    copts = NEB_COPTS,
    includes = ["include"],
    local_defines = [
        r'VERSION=\"' + mangle_version(CMK_VERSION) + r'\"',
    ],
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
    ] + glob(
        # patched nagios headers
        ["third_party/include/nagios/*.h"],
    ),
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
    copts = NEB_COPTS,
    includes = ["include"],
    deps = [
        "//packages/livestatus",
    ],
)

cc_library(
    name = "neb",
    includes = ["include"],
    deps = [
        ":neb_base",
        ":neb_version",
        "//packages/livestatus",
    ],
)

cc_shared_library(
    name = "neb_shared",
    deps = [":neb"],
)

cc_library(
    name = "test_utilities",
    testonly = 1,
    srcs = [
        "test/test_utilities.cc",
    ],
    hdrs = ["test/test_utilities.h"],
    copts = NEB_COPTS,
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
    copts = NEB_COPTS,
    deps = [":neb"],
)

# CC=/usr/bin/gcc-13 bazel test --test_output=all //packages/neb:all
cc_test(
    name = "test",
    size = "small",
    testonly = 1,
    srcs = [
        "test/test_CrashReport.cc",
        "test/test_DictFilter.cc",
        "test/test_MacroExpander.cc",
    ],
    copts = NEB_COPTS,
    deps = [
        ":dummy_nagios",
        ":neb",
        ":test_utilities",
        "@gtest//:gtest_main",
    ],
)
