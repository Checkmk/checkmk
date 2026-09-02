load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_shell//shell:sh_library.bzl", "sh_library")

py_library(
    name = "tsm",
    srcs = glob(["**/*.py"]),
    data = glob([
        "agents/*",
        "checkman/*",
    ]),
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:bakery",
        "//packages/cmk-plugin-apis:graphing",
        "//packages/cmk-plugin-apis:rulesets",
    ],
)

filegroup(
    name = "agents",
    srcs = glob(["agents/**/*"]),
    visibility = ["//packages/cmk-plugins:__pkg__"],
)

sh_library(
    name = "agents_sh",
    srcs = [
        "agents/mk_tsm",
        # mk_tsm sources tsm.cfg, so shellcheck needs the example config as an
        # input to follow the "shellcheck source=" directive in it.
        "//agents/cfg_examples:agents_cfg_examples_sh",
    ],
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
