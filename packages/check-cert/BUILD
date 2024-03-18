# //packages/check-cert:check-cert

load("@check-cert-deps//:defs.bzl", "aliases", "all_crate_deps")
load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_library")

rust_library(
    name = "check-cert-lib",
    srcs = [
        "src/check.rs",
        "src/checker/certificate.rs",
        "src/checker/fetcher.rs",
        "src/checker/verification.rs",
        "src/fetcher.rs",
        "src/lib.rs",
        "src/truststore.rs",
    ],
    aliases = aliases(),
    crate_name = "check_cert",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    deps = all_crate_deps() + ["@openssl"],
)

rust_binary(
    name = "check-cert",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    crate_name = "check_cert",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":check-cert-lib"],
)
