load("@rules_cc//cc/toolchains:tool.bzl", "cc_tool")
load("@rules_cc//cc/toolchains:tool_map.bzl", "cc_tool_map")

cc_tool_map(
    name = "tools",
    tags = ["manual"],
    tools = {
        "@rules_cc//cc/toolchains/actions:ar_actions": ":ar",
        "@rules_cc//cc/toolchains/actions:assembly_actions": ":clang",
        "@rules_cc//cc/toolchains/actions:c_compile": ":clang",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions": ":clang++",
        "@rules_cc//cc/toolchains/actions:link_actions": ":lld",
        "@rules_cc//cc/toolchains/actions:objcopy_embed_data": ":objcopy",
        "@rules_cc//cc/toolchains/actions:strip": ":strip",
    },
    visibility = ["//visibility:public"],
)

cc_tool(
    name = "clang",
    src = "@clang-linux-x86_64//:bin/clang",
    data = ["@clang-linux-x86_64//:builtin_headers"],
    tags = ["manual"],
)

cc_tool(
    name = "clang++",
    src = "@clang-linux-x86_64//:bin/clang++",
    data = ["@clang-linux-x86_64//:builtin_headers"],
    tags = ["manual"],
)

cc_tool(
    name = "lld",
    src = "@clang-linux-x86_64//:bin/clang",
    data = ["@clang-linux-x86_64//:linker_builtins"],
    tags = ["manual"],
)

cc_tool(
    name = "ar",
    src = "@clang-linux-x86_64//:bin/llvm-ar",
    tags = ["manual"],
)

cc_tool(
    name = "objcopy",
    src = "@clang-linux-x86_64//:bin/llvm-objcopy",
    tags = ["manual"],
)

cc_tool(
    name = "objdump",
    src = "@clang-linux-x86_64//:bin/llvm-objdump",
    tags = ["manual"],
)

cc_tool(
    name = "strip",
    src = "@clang-linux-x86_64//:bin/llvm-strip",
    tags = ["manual"],
)
