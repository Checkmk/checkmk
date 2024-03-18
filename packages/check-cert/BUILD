# `bazel build //:check-cert`.

load("@crate_index//:defs.bzl", "aliases", "all_crate_deps")
load("@rules_rust//rust:defs.bzl", "rust_binary")

rust_binary(
    name = "check-cert",
    srcs = glob([
        "src/**/*.rs",
    ]),
    aliases = aliases(),
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    visibility = ["//visibility:public"],
    # deps = all_crate_deps() + ["@openssl"],
    deps = all_crate_deps(),
)
