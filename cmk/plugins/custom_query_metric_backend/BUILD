load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "strip_prefix")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

py_library(
    name = "custom_query_metric_backend",
    srcs = glob(["**/*.py"]),
    imports = ["../../.."],
    target_compatible_with = select({
        "@//:gpl+nonfree_repo": [],
        "@//:gpl_repo": ["@platforms//:incompatible"],
    }),
    visibility = [
        "//cmk:__subpackages__",
        "//tests:__subpackages__",
    ],
    deps = [
        "//cmk/gui/nonfree/ultimate",
        "//cmk/utils",
        "//non-free/packages/cmk-metric-backend",
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
    ],
)

filegroup(
    name = "checkman",
    srcs = glob(["**/checkman/**"]),
    visibility = ["//cmk/plugins:__pkg__"],
)

filegroup(
    name = "libexec",
    srcs = glob(["**/libexec/*"]),
    visibility = ["//cmk/plugins:__pkg__"],
)

pkg_files(
    name = "libexec_pkg",
    srcs = [":libexec"],
    attributes = pkg_attributes(mode = "0755"),
    prefix = "lib/python3/cmk/plugins/custom_query_metric_backend",
    strip_prefix = strip_prefix.from_pkg(""),
)

pkg_tar(
    name = "pkg_tar",
    srcs = [":libexec_pkg"],
    tags = ["manual"],
    visibility = ["//omd:__pkg__"],
)
