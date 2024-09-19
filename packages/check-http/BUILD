load("@cargo_deps_site//:defs.bzl", "aliases", "all_crate_deps")
load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_library")

rust_library(
    name = "check-http-lib",
    srcs = [
        "src/checking_types.rs",
        "src/checks.rs",
        "src/http.rs",
        "src/http/client.rs",
        "src/http/request.rs",
        "src/lib.rs",
        "src/output.rs",
        "src/runner.rs",
    ],
    aliases = aliases(),
    crate_name = "check_http",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    deps = all_crate_deps() + ["@openssl"],
)

rust_binary(
    name = "check-http",
    srcs = [
        "src/cli.rs",
        "src/main.rs",
        "src/pwstore.rs",
    ],
    aliases = aliases(),
    crate_name = "check_http",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":check-http-lib"],
)
