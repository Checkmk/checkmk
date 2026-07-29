load("@rules_cc//cc/toolchains:tool.bzl", "cc_tool")
load("@rules_cc//cc/toolchains:tool_map.bzl", "cc_tool_map")

cc_tool_map(
    name = "tools",
    tags = ["manual"],
    tools = {
        "@rules_cc//cc/toolchains/actions:ar_actions": ":llvm-lib",
        "@rules_cc//cc/toolchains/actions:assembly_actions": ":clang-cl",
        "@rules_cc//cc/toolchains/actions:c_compile": ":clang-cl",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions": ":clang-cl",
        "@rules_cc//cc/toolchains/actions:link_actions": ":lld-link",
        "@rules_cc//cc/toolchains/actions:objcopy_embed_data": ":objcopy",
        "@rules_cc//cc/toolchains/actions:strip": ":strip",
    },
    visibility = ["//visibility:public"],
)

# The tool basename must contain "clang-cl" so cc-rs detects the compiler
# family in cargo build scripts.
cc_tool(
    name = "clang-cl",
    src = "@llvm_toolchain//:clang-cl",
    allowlist_include_directories = [
        "@xwin_sysroot//:crt_include",
        "@xwin_sysroot//:sdk_include_shared",
        "@xwin_sysroot//:sdk_include_ucrt",
        "@xwin_sysroot//:sdk_include_um",
    ],
    data = [
        "@llvm_toolchain//:builtin_headers",
        "@llvm_toolchain//:compiler_builtins",
        "@xwin_sysroot//:includes",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "lld-link",
    src = "@llvm_toolchain//:lld-link",
    data = [
        # bin/lld-link is a symlink; linker_builtins carries its target.
        "@llvm_toolchain//:linker_builtins",
        "@xwin_sysroot//:libs",
    ],
    tags = ["manual"],
)

cc_tool(
    name = "llvm-lib",
    src = "@llvm_toolchain//:llvm-lib",
    # bin/llvm-lib is a symlink to llvm-ar.
    data = ["@llvm_toolchain//:llvm-ar"],
    tags = ["manual"],
)

cc_tool(
    name = "objcopy",
    src = "@llvm_toolchain//:llvm-objcopy",
    tags = ["manual"],
)

cc_tool(
    name = "strip",
    src = "@llvm_toolchain//:llvm-strip",
    # bin/llvm-strip is a symlink to llvm-objcopy.
    data = ["@llvm_toolchain//:llvm-objcopy"],
    tags = ["manual"],
)
