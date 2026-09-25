load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@cmk_requirements//:requirements.bzl", "requirement")
load("@rules_shell//shell:sh_library.bzl", "sh_library")

py_library(
    name = "ssh",
    srcs = glob(["**/*.py"]),
    data = glob(
        [
            "agents/*",
            "checkman/*",
            "libexec/*",
        ],
        allow_empty = True,
    ) + ["py.typed"],
    imports = ["../../.."],
    visibility = ["//visibility:public"],
    deps = [
        "//packages/cmk-plugin-apis:agent_based",
        "//packages/cmk-plugin-apis:bakery",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-plugin-apis:server_side_calls",
        requirement("pydantic"),
    ],
)

filegroup(
    name = "agents",
    srcs = glob(
        ["agents/**/*"],
        allow_empty = True,
    ),
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
