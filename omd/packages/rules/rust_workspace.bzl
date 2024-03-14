load("@rules_rust//rust:repositories.bzl", "rules_rust_dependencies", "rust_register_toolchains")
load("@rules_rust//crate_universe:repositories.bzl", "crate_universe_dependencies")

def rust_workspace():
    rules_rust_dependencies()
    rust_register_toolchains(
        versions = ["1.75.0"],
        edition = "2021",
    )
    crate_universe_dependencies()
