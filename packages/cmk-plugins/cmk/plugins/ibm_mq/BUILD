load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_shell//shell:sh_library.bzl", "sh_library")

py_library(
    name = "ibm_mq",
    srcs = glob(["**/*.py"]),
    data = glob(["checkman/*"]),
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:inventory_ui",
        "//packages/cmk-plugin-apis:rulesets",
        requirement("python-dateutil"),
    ],
)

filegroup(
    name = "agents",
    srcs = [],
    visibility = ["//packages/cmk-plugins:__pkg__"],
)

filegroup(
    name = "checkman",
    srcs = glob(["checkman/**/*"]),
    visibility = ["//packages/cmk-plugins:__pkg__"],
)

sh_library(
    name = "libexec",
    srcs = [],
    visibility = ["//packages/cmk-plugins:__pkg__"],
)
