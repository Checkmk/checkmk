load("@rules_cc//cc/toolchains:args.bzl", "cc_args")

package(default_visibility = ["//bazel/toolchains/cc/clang:__subpackages__"])

cc_args(
    name = "no_absolute_paths_for_builtins",
    actions = ["@rules_cc//cc/toolchains/actions:compile_actions"],
    args = ["-no-canonical-prefixes"],
    requires_not_none = "@rules_cc//cc/toolchains/variables:source_file",
)
