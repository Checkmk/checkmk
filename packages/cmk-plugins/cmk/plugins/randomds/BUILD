load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_shell//shell:sh_library.bzl", "sh_library")

py_library(
    name = "randomds",
    srcs = glob(["**/*.py"]),
    data = ["py.typed"],
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        "//packages/cmk-plugin-apis:server_side_programs",
    ],
)

filegroup(
    name = "agents",
    srcs = [],
    visibility = ["//packages/cmk-plugins:__pkg__"],
)

filegroup(
    name = "checkman",
    srcs = glob(
        ["checkman/**/*"],
        allow_empty = True,
    ),
    visibility = ["//packages/cmk-plugins:__pkg__"],
)

sh_library(
    name = "libexec",
    srcs = glob(
        ["libexec/*"],
        allow_empty = True,
    ),
    visibility = ["//packages/cmk-plugins:__pkg__"],
)
