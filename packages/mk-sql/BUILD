load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@host_crates//:defs.bzl", "aliases", "all_crate_deps")
load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_doc", "rust_library", "rust_test", "rust_test_suite")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:platform_transition_binary.bzl", "platform_transition_binary")

file_from_flag(
    name = "version.rs",
    out = "src/version.rs",
    content = ['pub const VERSION: &str = "{VERSION}";'],
    replace_labels = {"VERSION": "@cmk//version"},
    visibility = ["//visibility:private"],
)

rust_library(
    name = "mk-sql-lib",
    srcs = [
        "src/args.rs",
        "src/config.rs",
        "src/config/defines.rs",
        "src/config/ms_sql.rs",
        "src/config/section.rs",
        "src/config/system.rs",
        "src/config/yaml.rs",
        "src/constants.rs",
        "src/emit.rs",
        "src/lib.rs",
        "src/ms_sql.rs",
        "src/ms_sql/client.rs",
        "src/ms_sql/custom.rs",
        "src/ms_sql/defaults.rs",
        "src/ms_sql/instance.rs",
        "src/ms_sql/query.rs",
        "src/ms_sql/section.rs",
        "src/ms_sql/sqls.rs",
        "src/platform.rs",
        "src/setup.rs",
        "src/types.rs",
        "src/utils.rs",
        ":version.rs",  # invalidates cache
    ],
    aliases = aliases(),
    crate_name = "mk_sql",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    deps = all_crate_deps(),
)

rust_binary(
    name = "mk-sql",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    crate_name = "mk_sql",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    deps = all_crate_deps() + [":mk-sql-lib"],
)

build_test(
    name = "build_test",
    targets = [":mk-sql"],
)

platform_transition_binary(
    name = "mk-sql-musl",
    binary = ":mk-sql",
    compilation_mode = "opt",
    platform = "//bazel/platforms:x86_64-linux-musl",
    visibility = ["//visibility:public"],
)

platform_transition_binary(
    name = "mk-sql-musl-aarch64",
    binary = ":mk-sql",
    compilation_mode = "opt",
    platform = "//bazel/platforms:aarch64-linux-musl",
    visibility = ["//visibility:public"],
)

rust_test(
    name = "mk-sql-lib-test-internal",
    compile_data = [
        "tests/files/no-mssql.yml",
        "tests/files/not-yaml.yml",
        "tests/files/test-config.yml",
        "tests/files/test-mini.yml",
    ],
    crate = ":mk-sql-lib",
)

rust_library(
    name = "mk-sql-tests-common",
    testonly = 1,
    srcs = [
        "tests/common/mod.rs",
        "tests/common/tools.rs",
    ],
    crate_features = ["build_system_bazel"],
    crate_name = "common",
    crate_root = "tests/common/mod.rs",
    deps = all_crate_deps() + [
        ":mk-sql-lib",
        "@host_crates//:assert_cmd",
        "@host_crates//:tempfile",
    ],
)

rust_test_suite(
    name = "mk-sql-lib-test-external",
    srcs = [
        "tests/test_ms_sql.rs",
    ],
    compile_data = [
        "tests/files/no-mssql.yml",
        "tests/files/not-yaml.yml",
        "tests/files/test-config.yml",
        "tests/files/test-no-ms-sql.yml",
        "tests/files/test-mini.yml",
    ],
    crate_features = ["build_system_bazel"],
    env_inherit = [
        "CI_TEST_SQL_DB_ENDPOINT",
    ],
    deps = all_crate_deps() + [
        ":mk-sql",
        ":mk-sql-lib",
        ":mk-sql-tests-common",
        "@host_crates//:assert_cmd",
        "@host_crates//:tempfile",
    ],
)

rust_doc(
    name = "doc",
    crate = ":mk-sql-lib",
    rustdoc_flags = ["--document-private-items"],
)
