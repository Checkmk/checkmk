# Adapted from https://github.com/CACI-International/cpp-toolchain
load("@rules_cc//cc/toolchains/impl:documented_api.bzl", "cc_args", "cc_feature", "cc_mutually_exclusive_category")

cc_mutually_exclusive_category(
    name = "opt_level",
)

cc_args(
    name = "no_optimization_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = ["-O0"],
)

cc_args(
    name = "debug_optimization_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = ["-Og"],
)

cc_args(
    name = "moderate_optimization_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = ["-O2"],
)

cc_args(
    name = "max_optimization_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = ["-O3"],
)

cc_args(
    name = "size_optimization_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    args = ["-Oz"],
)

cc_feature(
    name = "no_optimization",
    args = ["no_optimization_args"],
    feature_name = "no_optimization",
    mutually_exclusive = ["opt_level"],
    visibility = ["//:__subpackages__"],
)

cc_feature(
    name = "debug_optimization",
    args = ["debug_optimization_args"],
    feature_name = "debug_optimization",
    mutually_exclusive = ["opt_level"],
    visibility = ["//:__subpackages__"],
)

cc_feature(
    name = "moderate_optimization",
    args = ["moderate_optimization_args"],
    feature_name = "moderate_optimization",
    mutually_exclusive = ["opt_level"],
    visibility = ["//:__subpackages__"],
)

cc_feature(
    name = "max_optimization",
    args = ["max_optimization_args"],
    feature_name = "max_optimization",
    mutually_exclusive = ["opt_level"],
    visibility = ["//:__subpackages__"],
)

cc_feature(
    name = "size_optimization",
    args = ["size_optimization_args"],
    feature_name = "size_optimization",
    mutually_exclusive = ["opt_level"],
    visibility = ["//:__subpackages__"],
)
