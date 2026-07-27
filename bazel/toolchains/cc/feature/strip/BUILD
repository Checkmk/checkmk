load("@rules_cc//cc/toolchains/impl:documented_api.bzl", "cc_args", "cc_feature")

cc_args(
    name = "strip_all_symbols_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = ["-Wl,-s"],
)

cc_feature(
    name = "strip_all_symbols",
    args = [":strip_all_symbols_args"],
    feature_name = "strip_all_symbols",
    visibility = ["//:__subpackages__"],
)
