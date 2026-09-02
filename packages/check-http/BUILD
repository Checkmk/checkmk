load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_rust//rust:defs.bzl", "rust_doc", "rust_library", "rust_test", "rust_test_suite")
load("@site_crates//:defs.bzl", "aliases", "all_crate_deps")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:patchelf.bzl", "set_runpath")
load("//bazel/rules:xcomp/rust.bzl", "rust_binary")

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

rust_test(
    name = "check-http-lib-test-internal",
    crate = ":check-http-lib",
)

rust_test_suite(
    name = "check-http-lib-test-external",
    srcs = [
        "tests/test_http.rs",
    ],
    deps = all_crate_deps() + [
        ":check-http-lib",
    ],
)

file_from_flag(
    name = "version.rs",
    out = "src/version.rs",
    content = ['pub const VERSION: &str = "{VERSION}";'],
    replace_labels = {"VERSION": "@cmk//version"},
    visibility = ["//visibility:private"],
)

rust_binary(
    name = "check-http",
    srcs = [
        "src/cli.rs",
        "src/main.rs",
        "src/pwstore.rs",
        ":version.rs",
    ],
    aliases = aliases(),
    crate_name = "check_http",
    edition = "2021",
    opt = True,
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    strip = True,
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":check-http-lib"],
)

build_test(
    name = "build_test",
    targets = ["check-http"],
)

set_runpath(
    name = "check_http_runpath",
    srcs = [":check-http"],
    rpaths = ["$ORIGIN/../../../lib"],
    tags = ["manual"],
)

pkg_files(
    name = "check_http_pkg",
    srcs = [":check_http_runpath"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "lib/nagios/plugins/",
    renames = {":check_http_runpath": "check_httpv2"},
    visibility = ["//omd:__pkg__"],
)

pkg_tar(
    name = "check_http_tar",
    srcs = [":check_http_pkg"],
    stamp = 1,
)

rust_doc(
    name = "doc",
    crate = ":check-http-lib",
    rustdoc_flags = [
        '--cfg=feature="reqwest/native-tls-vendored"',
        "--document-private-items",
    ],
)

sh_library(
    name = "helpers",
    srcs = [
        ".f12",
        "run",
    ],
)
