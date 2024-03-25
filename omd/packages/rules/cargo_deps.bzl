load("@rules_rust//crate_universe:defs.bzl", "crate", "crates_repository")

# Repin with `CARGO_BAZEL_REPIN=1 bazel sync --only=NAME`.
def cargo_deps(name, package):
    crates_repository(
        name = name,
        cargo_lockfile = "//" + package + ":Cargo.lock",
        lockfile = "//" + package + ":Cargo.lock.bazel",
        manifests = ["//" + package + ":Cargo.toml"],
        annotations = {
            "openssl-sys": [
                crate.annotation(
                    build_script_env = {
                        "OPENSSL_STATIC": "0",
                        "OPENSSL_NO_VENDOR": "1",
                    },
                    # Defining `deps = ["@openssl"]` here results in static linkage,
                    # even with OPENSSL_NO_VENDOR=1 and OPENSSL_STATIC=0
                ),
            ],
        },
    )
