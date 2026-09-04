load("@rules_cc//cc/toolchains/impl:documented_api.bzl", "cc_args", "cc_feature")

cc_args(
    name = "static_libgcc_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    args = ["-static-libgcc"],
)

cc_feature(
    name = "static_libgcc",
    args = [":static_libgcc_args"],
    # "static_libgcc" is already claimed by a feature pulled in through
    # experimental_replace_legacy_action_config_features, so this needs
    # its own name.
    feature_name = "force_static_libgcc",
    visibility = ["//:__subpackages__"],
)
