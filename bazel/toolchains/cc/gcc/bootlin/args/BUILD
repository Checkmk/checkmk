load("@rules_cc//cc/toolchains/args:sysroot.bzl", "cc_sysroot")

cc_sysroot(
    name = "linux_sysroot",
    actions = [
        # Won't work with `link_actions`.
        "@rules_cc//cc/toolchains/actions:compile_actions",
    ],
    data = [
        "@gcc-linux-x86_64//:include-x86_64-buildroot-linux-gnu",
        "@gcc-linux-x86_64//:lib-gcc-include",
        "@gcc-linux-x86_64//:sysroot",
    ],
    sysroot = "@gcc-linux-x86_64//:sysroot",
    visibility = ["//visibility:public"],
)
