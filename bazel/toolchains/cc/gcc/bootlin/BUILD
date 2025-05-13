load("@rules_cc//cc/toolchains:toolchain.bzl", "cc_toolchain")
load("//bazel/toolchains/cc/feature/std:standards.bzl", "STANDARDS_FEATURES")

cc_toolchain(
    name = "host_gcc",
    args = [
        "//bazel/toolchains/cc/gcc/bootlin/args:linux_sysroot",
        "//bazel/toolchains/cc/gcc/args:link_libs",
        "//bazel/toolchains/cc/gcc/args:no_absolute_paths_for_builtins",
        "//bazel/toolchains/cc/args:optimizations",
        "//bazel/toolchains/cc/args:pic_flags",
        "//bazel/toolchains/cc/args:reproducible_compile_args",
    ],
    compiler = "gcc",
    dynamic_runtime_lib = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:dynamic_runtime_lib",
    }),
    enabled_features = [
        "@rules_cc//cc/toolchains/args:experimental_replace_legacy_action_config_features",
        "//bazel/toolchains/cc/feature/optimize:moderate_optimization",
    ],
    known_features = [
        "@rules_cc//cc/toolchains/args:experimental_replace_legacy_action_config_features",
        "//bazel/toolchains/cc/feature/optimize:no_optimization",
        "//bazel/toolchains/cc/feature/optimize:debug_optimization",
        "//bazel/toolchains/cc/feature/optimize:size_optimization",
        "//bazel/toolchains/cc/feature/optimize:moderate_optimization",
        "//bazel/toolchains/cc/feature/optimize:max_optimization",
    ] + ["//bazel/toolchains/cc/feature/std:" + std for std in STANDARDS_FEATURES],
    static_runtime_lib = select({
        "//bazel/platforms:linux_x86_64": "@gcc-linux-x86_64//:static_runtime_lib",
    }),
    tags = ["manual"],
    tool_map = "//bazel/toolchains/cc/gcc/bootlin/tools",
)

toolchain(
    name = "host_gcc_toolchain",
    exec_compatible_with = [
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    target_compatible_with = [
        "//bazel/platforms:hermetic",
        "@platforms//cpu:x86_64",
        "@platforms//os:linux",
    ],
    toolchain = ":host_gcc",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
    visibility = ["//visibility:public"],
)
