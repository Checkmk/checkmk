load("@rules_rust//crate_universe:defs.bzl", "crates_repository")

# Repin with `CARGO_BAZEL_REPIN=1 bazel sync --only=NAME`.
def cargo_deps(name, package):
    crates_repository(
        name = name,
        cargo_lockfile = "//" + package + ":Cargo.lock",
        lockfile = "//" + package + ":Cargo.lock.bazel",
        manifests = ["//" + package + ":Cargo.toml"],
    )
