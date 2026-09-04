load("@rules_cc//cc/toolchains/impl:documented_api.bzl", "cc_args", "cc_feature")

cc_args(
    name = "static_libstdcpp_args",
    actions = [
        "@rules_cc//cc/toolchains/actions:link_actions",
    ],
    # -static-libstdc++ only works because //bazel/toolchains/cc/gcc/args:link_libs
    # scopes its own -lstdc++ as as-needed-droppable. Without that, GCC's driver
    # leaves an explicit non-droppable dynamic -lstdc++ that this flag can't override.
    args = ["-static-libstdc++"],
)

cc_feature(
    name = "static_libstdcpp",
    args = [":static_libstdcpp_args"],
    feature_name = "static_libstdcpp",
    # GCC still links libgcc_s dynamically unless -static-libgcc is passed too.
    implies = ["//bazel/toolchains/cc/feature/static_libgcc"],
    visibility = ["//:__subpackages__"],
)
