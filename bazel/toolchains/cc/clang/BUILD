load("@rules_cc//cc/toolchains:toolchain.bzl", "cc_toolchain")

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
        "//bazel/toolchains/cc/args:all_optimizations",
        # TODO: The next ones are also declared as features.
        "//bazel/toolchains/cc/args:pic_flags",
        "//bazel/toolchains/cc/args:unfiltered_compile_flags",
    ],
    compiler = "clang",
    dynamic_runtime_lib = select({
        "//bazel/platforms:linux_x86_64": "@clang-linux-x86_64//:dynamic_runtime_lib",
    }),
    enabled_features = ["@rules_cc//cc/toolchains/args:experimental_replace_legacy_action_config_features"],
    known_features = ["@rules_cc//cc/toolchains/args:experimental_replace_legacy_action_config_features"],
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
