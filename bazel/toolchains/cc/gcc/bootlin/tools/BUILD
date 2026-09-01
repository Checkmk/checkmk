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

# No --sysroot flag: gcc resolves its own relocatable default sysroot, and
# rules_foreign_cc folds the compiler into a single $CC word, which breaks
# if --sysroot is appended separately.
cc_tool(
    name = "gcc",
    src = "@gcc_toolchain//:bin/x86_64-checkmk-linux-gnu-gcc",
    data = [
        "@gcc_toolchain//:builtin_headers",
        "@gcc_toolchain//:linker_buildroot",
        "@gcc_toolchain//:multicall_support_files",
        "@gcc_toolchain//:sysroot",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "g++",
    src = "@gcc_toolchain//:bin/x86_64-checkmk-linux-gnu-g++",
    data = [
        "@gcc_toolchain//:builtin_headers",
        "@gcc_toolchain//:multicall_support_files",
        "@gcc_toolchain//:sysroot",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "ld",
    src = "@gcc_toolchain//:bin/x86_64-checkmk-linux-gnu-g++",
    data = [
        "@gcc_toolchain//:linker_builtins",
        "@gcc_toolchain//:multicall_support_files",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "ar",
    src = "@gcc_toolchain//:bin/x86_64-checkmk-linux-gnu-ar",
    tags = ["manual"],
)

cc_tool(
    name = "objcopy",
    src = "@gcc_toolchain//:bin/x86_64-checkmk-linux-gnu-objcopy",
    tags = ["manual"],
)

cc_tool(
    name = "objdump",
    src = "@gcc_toolchain//:bin/x86_64-checkmk-linux-gnu-objdump",
    tags = ["manual"],
)

cc_tool(
    name = "gcov",
    src = "@gcc_toolchain//:bin/x86_64-checkmk-linux-gnu-gcov",
    tags = ["manual"],
)

cc_tool(
    name = "strip",
    src = "@gcc_toolchain//:bin/x86_64-checkmk-linux-gnu-strip",
    tags = ["manual"],
)
