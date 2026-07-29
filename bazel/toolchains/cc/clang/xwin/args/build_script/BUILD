# Release settings for the two command lines rules_rust builds without action
# variables: the $CFLAGS it exports to cargo build scripts, and the linker
# arguments it hands to rustc. Always release, ignores -c dbg/fastbuild/opt.
#
# Everything here is gated `requires_none`, everything in ../mode/BUILD
# `requires_not_none`, so the two never both apply.

load("@rules_cc//cc/toolchains:args.bzl", "cc_args")
load("@rules_cc//cc/toolchains:args_list.bzl", "cc_args_list")
load("//bazel/toolchains/cc/clang/xwin/args:crt.bzl", "RELEASE_CRT_LINK_ARGS")

package(default_visibility = ["//bazel/toolchains/cc/clang:__subpackages__"])

cc_args_list(
    name = "release_defaults",
    args = [
        ":ndebug",
        ":static_release_crt",
        ":moderate_optimization_args",
        ":release_crt_link",
    ],
)

cc_args(
    name = "ndebug",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["-DNDEBUG"],
    requires_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_args(
    name = "static_release_crt",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["/MT"],
    requires_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_args(
    name = "moderate_optimization_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:c_compile",
        "@rules_cc//cc/toolchains/actions:cpp_compile_actions",
    ],
    args = ["/O2"],
    requires_none = "@rules_cc//cc/toolchains/variables:source_file",
)

cc_args(
    name = "release_crt_link",
    actions = ["@rules_cc//cc/toolchains/actions:link_actions"],
    args = RELEASE_CRT_LINK_ARGS,
    requires_none = "@rules_cc//cc/toolchains/variables:output_execpath",
)
