load("@rules_cc//cc/toolchains:args.bzl", "cc_args")
load("@rules_cc//cc/toolchains:args_list.bzl", "cc_args_list")

package(default_visibility = ["//visibility:public"])

cc_args(
    # See also `@rules_cc//cc/toolchains/args/pic_flags`
    name = "pic_flags",
    actions = ["@rules_cc//cc/toolchains/actions:compile_actions"],
    args = ["-fPIC"],
)

cc_args(
    name = "hardening",
    actions = ["@rules_cc//cc/toolchains/actions:compile_actions"],
    args = ["-fstack-protector"],
)

cc_args(
    # See https://github.com/CACI-International/cpp-toolchain/
    name = "reproducible_compile_args",
    actions = ["@rules_cc//cc/toolchains/actions:compile_actions"],
    args = [
        "-Wno-builtin-macro-redefined",
        '-D__DATE__="redacted"',
        '-D__TIMESTAMP__="redacted"',
        '-D__TIME__="redacted"',
        "-ffile-prefix-map=__BAZEL_EXECUTION_ROOT__=.",
    ],
)

cc_args_list(
    name = "optimizations",
    args = [
        "ndebug",
        "function_sections",
    ] + select({
        "@platforms//os:linux": ["gc_sections"],
        "//conditions:default": [],
    }),
)

cc_args(
    name = "ndebug",
    actions = ["@rules_cc//cc/toolchains/actions:compile_actions"],
    args = ["-DNDEBUG"],
)

cc_args(
    name = "fortify-source",
    actions = ["@rules_cc//cc/toolchains/actions:compile_actions"],
    args = ["-D_FORTIFY_SOURCE=1"],
)

cc_args(
    name = "function_sections",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = [
        "-ffunction-sections",
        "-fdata-sections",
    ],
)

cc_args(
    name = "gc_sections",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = ["-Wl,--gc-sections"],
)
