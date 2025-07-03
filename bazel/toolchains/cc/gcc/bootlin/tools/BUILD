# See https://github.com/bazelbuild/rules_cc/tree/main/examples/rule_based_toolchain

load("@rules_cc//cc/toolchains:tool.bzl", "cc_tool")
load("@rules_cc//cc/toolchains:tool_map.bzl", "cc_tool_map")

cc_tool_map(
    name = "tools",
    tags = ["manual"],
    tools = {
        "@rules_cc//cc/toolchains/actions:ar_actions": ":ar",
        "@rules_cc//cc/toolchains/actions:assembly_actions": ":gcc",
        "@rules_cc//cc/toolchains/actions:c_compile": ":gcc",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions": ":g++",
        "@rules_cc//cc/toolchains/actions:link_actions": ":ld",
        "@rules_cc//cc/toolchains/actions:objcopy_embed_data": ":objcopy",
        "@rules_cc//cc/toolchains/actions:strip": ":strip",
    },
    visibility = ["//visibility:public"],
)

cc_tool(
    name = "gcc",
    src = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:bin/x86_64-linux-gcc.br_real",
    }),
    data = [
        ":exec_platform_builtin_headers",
        ":exec_platform_multicall_support_files",
        "@gcc-linux-x86_64//:linker_buildroot",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "g++",
    src = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:bin/x86_64-linux-g++.br_real",
    }),
    data = [
        ":exec_platform_builtin_headers",
        ":exec_platform_multicall_support_files",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "ld",
    src = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:bin/x86_64-linux-g++.br_real",
    }),
    data = [
        ":exec_platform_linker_builtins",
        ":exec_platform_multicall_support_files",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "ar",
    src = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:bin/x86_64-linux-ar",
    }),
    tags = ["manual"],
)

cc_tool(
    name = "objcopy",
    src = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:bin/x86_64-linux-objcopy",
    }),
    tags = ["manual"],
)

cc_tool(
    name = "objdump",
    src = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:bin/x86_64-linux-objdump",
    }),
    tags = ["manual"],
)

cc_tool(
    name = "gcov",
    src = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:bin/x86_64-linux-gcov",
    }),
    tags = ["manual"],
)

cc_tool(
    name = "strip",
    src = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:bin/x86_64-linux-strip",
    }),
    tags = ["manual"],
)

#################################
#   Platform-specific aliases   #
#################################

# These aliases are used to reduce duplication of `select` statements throughout
# this build file. The select statements in these aliases are evaluated under
# the exec configuration.

alias(
    name = "exec_platform_builtin_headers",
    actual = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:builtin_headers",
    }),
    tags = ["manual"],
    visibility = ["//visibility:private"],
)

alias(
    name = "exec_platform_multicall_support_files",
    actual = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:multicall_support_files",
    }),
    tags = ["manual"],
    visibility = ["//visibility:private"],
)

alias(
    name = "exec_platform_linker_builtins",
    actual = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:linker_builtins",
    }),
    tags = ["manual"],
    visibility = ["//visibility:private"],
)
