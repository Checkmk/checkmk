load("@rules_cc//cc/toolchains:args.bzl", "cc_args")

package(default_visibility = ["//visibility:public"])

cc_args(
    name = "no_absolute_paths_for_builtins",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = [
        "-no-canonical-prefixes",
        "-fno-canonical-system-headers",  # gcc-only
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
