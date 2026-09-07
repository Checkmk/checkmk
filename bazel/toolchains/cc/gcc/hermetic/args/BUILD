load("@rules_cc//cc/toolchains/args:sysroot.bzl", "cc_sysroot")

cc_sysroot(
    name = "linux_sysroot",
    actions = [
        # Won't work with `link_actions`.
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    data = [
        "@gcc_toolchain//:include-x86_64-checkmk-linux-gnu",
        "@gcc_toolchain//:lib-gcc-include",
        "@gcc_toolchain//:sysroot",
    ],
    sysroot = "@gcc_toolchain//:sysroot",
    visibility = ["//visibility:public"],
)
