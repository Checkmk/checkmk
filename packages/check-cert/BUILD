load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_doc", "rust_library", "rust_test", "rust_test_suite")
load("@site_crates//:defs.bzl", "aliases", "all_crate_deps")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")

file_from_flag(
    name = "version.rs",
    out = "src/version.rs",
    content = ['pub const VERSION: &str = "{VERSION}";'],
    replace_labels = {"VERSION": "@cmk//version"},
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
        "src/pwstore.rs",
        "src/starttls/postgres.rs",
        "src/starttls/smtp.rs",
        "src/starttls/stream_io.rs",
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

rust_test(
    name = "check-cert-lib-test-internal",
    compile_data = ["assets/certificate.der"],
    crate = ":check-cert-lib",
)

rust_test(
    name = "postgres_starttls_test",
    srcs = [
        "tests/starttls/common/mock_stream.rs",
        "tests/starttls/postgres.rs",
    ],
    crate_root = "tests/starttls/postgres.rs",
    deps = [":check-cert-lib"],
)

rust_test(
    name = "smtp_starttls_test",
    srcs = [
        "tests/starttls/common/mock_stream.rs",
        "tests/starttls/smtp.rs",
    ],
    crate_root = "tests/starttls/smtp.rs",
    deps = [":check-cert-lib"],
)

rust_test(
    name = "starttls_stream_io_test",
    srcs = [
        "tests/starttls/stream_io.rs",
    ],
    crate_root = "tests/starttls/stream_io.rs",
    deps = [":check-cert-lib"],
)

rust_test_suite(
    name = "check-cert-lib-test-external",
    srcs = [
        "tests/certificate.rs",
        "tests/igca_cert.rs",
        "tests/truststore.rs",
        "tests/verify.rs",
    ],
    compile_data = [
        "assets/IGC_A.der",
        "assets/cert.der",
        "assets/ee-pss-sha1-cert.pem",
        "assets/ee-pss-sha256-cert.pem",
        "assets/root-ca.der",
    ],
    deps = [
        ":check-cert-lib",
        "@site_crates//:assertor",
        "@site_crates//:openssl",
        "@site_crates//:tempfile",
    ],
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

build_test(
    name = "build_test",
    targets = ["check-cert"],
)

rust_doc(
    name = "doc",
    crate = ":check-cert-lib",
    rustdoc_flags = [
        '--cfg=feature="vendored"',
        "--document-private-items",
    ],
)
