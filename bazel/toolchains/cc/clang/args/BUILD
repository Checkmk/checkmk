load("@rules_cc//cc/toolchains:args.bzl", "cc_args")
load("@rules_cc//cc/toolchains:args_list.bzl", "cc_args_list")

package(default_visibility = ["//visibility:public"])

cc_args(
    name = "_libcpp",
    actions = [
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["-stdlib=libc++"],
    target_compatible_with = ["@platforms//os:linux"],
    visibility = ["//visibility:private"],
)

cc_args(
    name = "_static_link_libcpp",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = [
        "-l:libc++.a",
        "-l:libc++abi.a",
    ],
    visibility = ["//visibility:private"],
)

cc_args(
    name = "_hermetic_runtime",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = [
        # Would link against libgcc_s by default, which is not in the
        # hermetic repository.
        # See also: https://clang.llvm.org/docs/Toolchain.html
        "--rtlib=compiler-rt",
        "--unwindlib=libunwind",
        "-l:libunwind.a",
    ],
    visibility = ["//visibility:private"],
)

cc_args_list(
    name = "hermetic_libcpp",
    args = [
        ":_libcpp",
        ":_static_link_libcpp",
        ":_hermetic_runtime",
    ],
)

cc_args(
    name = "link_libs",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = [
        "-lm",
    ],
)

cc_args(
    name = "lld_linker",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = ["-fuse-ld=lld"],
    target_compatible_with = ["@platforms//os:linux"],
)

cc_args(
    name = "no_absolute_paths_for_builtins",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = [
        "-no-canonical-prefixes",
    ],
)
