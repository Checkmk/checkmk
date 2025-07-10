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
    src = "@gcc-linux-x86_64//:bin/x86_64-linux-gcc.br_real",
    data = [
        "@gcc-linux-x86_64//:builtin_headers",
        "@gcc-linux-x86_64//:linker_buildroot",
        "@gcc-linux-x86_64//:multicall_support_files",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "g++",
    src = "@gcc-linux-x86_64//:bin/x86_64-linux-g++.br_real",
    data = [
        "@gcc-linux-x86_64//:builtin_headers",
        "@gcc-linux-x86_64//:multicall_support_files",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "ld",
    src = "@gcc-linux-x86_64//:bin/x86_64-linux-g++.br_real",
    data = [
        "@gcc-linux-x86_64//:linker_builtins",
        "@gcc-linux-x86_64//:multicall_support_files",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "ar",
    src = "@gcc-linux-x86_64//:bin/x86_64-linux-ar",
    tags = ["manual"],
)

cc_tool(
    name = "objcopy",
    src = "@gcc-linux-x86_64//:bin/x86_64-linux-objcopy",
    tags = ["manual"],
)

cc_tool(
    name = "objdump",
    src = "@gcc-linux-x86_64//:bin/x86_64-linux-objdump",
    tags = ["manual"],
)

cc_tool(
    name = "gcov",
    src = "@gcc-linux-x86_64//:bin/x86_64-linux-gcov",
    tags = ["manual"],
)

cc_tool(
    name = "strip",
    src = "@gcc-linux-x86_64//:bin/x86_64-linux-strip",
    tags = ["manual"],
)
