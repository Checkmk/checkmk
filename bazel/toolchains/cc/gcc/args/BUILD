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
    # -as-needed scoping around -lstdc++ is load-bearing: it's what lets
    # //bazel/toolchains/cc/feature/static_libstdcpp's -static-libstdc++ actually
    # produce a static link. Without it, GCC's driver still emits an
    # unconditional dynamic -lstdc++ that -static-libstdc++ can't override.
    args = [
        "-Wl,--push-state,-as-needed",
        "-lstdc++",
        "-Wl,--pop-state",
        "-lm",
    ],
)
