load("@host_crates//:defs.bzl", "aliases", "all_crate_deps")
load("//bazel/rules:xcomp/rust.bzl", "rust_binary")
load("//bazel/testing:static_crt.bzl", "static_crt_test")

rust_binary(
    name = "robotmk_ext-windows",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    # Same artifact name as the Windows-node cargo build; the -windows
    # target name only disambiguates from the host binary.
    binary_name = "robotmk_ext",
    crate_name = "robotmk_ext",
    edition = "2021",
    opt = True,
    platform = "//bazel/platforms:x86_64-windows-msvc",
    strip = True,
    tags = ["manual"],
    visibility = ["//visibility:public"],
    deps = all_crate_deps(),
)

static_crt_test(
    name = "robotmk_ext-windows-static-crt",
    binary = ":robotmk_ext-windows",
)
