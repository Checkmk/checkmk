load("@rules_cc//cc/toolchains:toolchain.bzl", "cc_toolchain")
load("//bazel/toolchains/cc/feature/std:standards.bzl", "STANDARDS_FEATURES")

cc_toolchain(
    name = "host_clang",
    args = [
        # Without a sysroot or `--gcc-install-dir`, llvm searches for
        # C headers in their default location, that is, `/usr/local/include`,
        # `/usr/include/<triple>`, and `/usr/include`.
        # Using those would require setting up a `new_local_repository`, which
        # is bad for the CI/CQ.
        #
        # Passing the gcc sysroot lets llvm use our hermetic C headers.
        #
        # See also: `clang -E -xc++ - -v < /dev/null`.
        "//bazel/toolchains/cc/gcc/bootlin/args:linux_sysroot",
        "//bazel/toolchains/cc/clang/args:hermetic_libcpp",
        "//bazel/toolchains/cc/clang/args:link_libs",
        "//bazel/toolchains/cc/clang/args:lld_linker",
        "//bazel/toolchains/cc/clang/args:no_absolute_paths_for_builtins",
        "//bazel/toolchains/cc/args:optimizations",
        "//bazel/toolchains/cc/args:pic_flags",
        "//bazel/toolchains/cc/args:reproducible_compile_args",
    ],
    compiler = "clang",
    dynamic_runtime_lib = select({
        "//bazel/platforms:linux_x86_64": "@clang-linux-x86_64//:dynamic_runtime_lib",
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
        "//bazel/platforms:linux_x86_64": "@clang-linux-x86_64//:static_runtime_lib",
    }),
    tags = ["manual"],
    tool_map = "//bazel/toolchains/cc/clang/tools",
)

toolchain(
    name = "host_clang_toolchain",
    exec_compatible_with = [
        "@platforms//os:linux",
    ],
    toolchain = ":host_clang",
    toolchain_type = "@bazel_tools//tools/cpp:toolchain_type",
    visibility = ["//visibility:public"],
)
