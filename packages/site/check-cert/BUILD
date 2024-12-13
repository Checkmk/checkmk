load("@cargo_deps_site//:defs.bzl", "aliases", "all_crate_deps")
load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_library")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")

file_from_flag(
    name = "version.rs",
    out = "src/version.rs",
    content = ["pub const VERSION: &str = %r;"],
    value = "//:cmk_version",
    visibility = ["//visibility:private"],
)

rust_library(
    name = "check-cert-lib",
    srcs = [
        "src/check.rs",
        "src/checker/certificate.rs",
        "src/checker/fetcher.rs",
        "src/checker/info.rs",
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
    deps = all_crate_deps(),
)

rust_binary(
    name = "check-cert",
    srcs = [
        "src/main.rs",
        ":version.rs",
    ],
    aliases = aliases(),
    crate_name = "check_cert",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":check-cert-lib"],
)
