load("@rules_cc//cc/toolchains:args.bzl", "cc_args")
load("@rules_cc//cc/toolchains:args_list.bzl", "cc_args_list")

package(default_visibility = ["//visibility:public"])

cc_args(
    name = "warnings",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = [
        "-Werror",
        "-Wall",
        "-Wextra",
        "-Wpedantic",
    ],
)

cc_args(
    name = "extra_warnings",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = [
        "-Wunused-but-set-parameter",
        "-Wno-free-nonheap-object",
    ],
)

cc_args_list(
    name = "all_warnings",
    args = [
        ":warnings",
        ":extra_warnings",
    ],
)

cc_args(
    # See also `@rules_cc//cc/toolchains/args/pic_flags`
    name = "pic_flags",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = ["-fPIC"],
)

cc_args(
    name = "hardening",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = [
        "-fstack-protector",
    ],
)

cc_args(
    name = "optimization",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = [
        "-g0",
        "-O2",
        "-D_FORTIFY_SOURCE=1",
        "-DNDEBUG",
        "-ffunction-sections",
        "-fdata-sections",
    ],
)

cc_args(
    name = "optimization_extra",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = [
        "-fno-omit-frame-pointer",
    ],
)

cc_args_list(
    name = "all_optimizations",
    args = [
        ":optimization",
        ":optimization_extra",
    ],
)

cc_args(
    # See also `@rules_cc//cc/toolchains/args:unfiltered_compile_flags`.
    name = "unfiltered_compile_flags",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = [
        "-Wno-builtin-macro-redefined",
        "-D__DATE__=\"redacted\"",
        "-D__TIMESTAMP__=\"redacted\"",
        "-D__TIME__=\"redacted\"",
    ],
)

cc_args(
    name = "link_flags",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = [
        "-Wl,-no-as-needed",
        "-Wl,-z,relro,-z,now",
        "-pass-exit-codes",
    ],
)

cc_args(
    name = "link_libs",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = [
        "-lstdc++",
        "-lm",
    ],
)

cc_args_list(
    name = "all_link_flags",
    args = [
        ":link_flags",
        ":link_libs",
    ],
)

cc_args(
    name = "gc_sections",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = ["-Wl,--gc-sections"],
)

cc_args(
    name = "function_sections",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = ["-ffunction-sections"],
)

cc_args_list(
    name = "gc_functions",
    args = [
        ":function_sections",
        ":gc_sections",
    ],
)
