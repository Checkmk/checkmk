load("@rules_cc//cc/toolchains:toolchain.bzl", "cc_toolchain")

cc_toolchain(
    name = "host_gcc",
    args = [
        "//bazel/toolchains/cc/gcc/bootlin/args:linux_sysroot",
        "//bazel/toolchains/cc/gcc/args:no_absolute_paths_for_builtins",
        # TODO: Make warnings a feature rather than args as it might break
        #       3rd party code.
        # "//bazel/toolchains/cc/args:warnings",
        "//bazel/toolchains/cc/args:all_optimizations",
        # TODO: The next ones are also declared as features.
        "//bazel/toolchains/cc/args:pic_flags",
        "//bazel/toolchains/cc/args:unfiltered_compile_flags",
    ],
    compiler = "gcc",
    dynamic_runtime_lib = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:dynamic_runtime_lib",
    }),
    enabled_features = ["@rules_cc//cc/toolchains/args:experimental_replace_legacy_action_config_features"],
    known_features = ["@rules_cc//cc/toolchains/args:experimental_replace_legacy_action_config_features"],
    static_runtime_lib = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:static_runtime_lib",
    }),
    tags = ["manual"],
    tool_map = "//bazel/toolchains/cc/gcc/bootlin/tools",
)

toolchain(
    name = "host_gcc_toolchain",
    exec_compatible_with = [
        "@platforms//os:linux",
    ],
    toolchain = ":host_gcc",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
    visibility = ["//visibility:public"],
)
