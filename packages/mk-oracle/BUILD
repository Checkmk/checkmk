load("@host_crates//:defs.bzl", "aliases", "all_crate_deps")
load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_library", "rust_test", "rust_test_suite")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:platform_transition_binary.bzl", "platform_transition_binary")

file_from_flag(
    name = "version.rs",
    out = "src/version.rs",
    content = ['pub const VERSION: &str = "{VERSION}";'],
    replace_labels = {"VERSION": "//bazel/cmk/version"},
    visibility = ["//visibility:private"],
)

rust_library(
    name = "mk-oracle-lib",
    srcs = [
        "src/args.rs",
        "src/config.rs",
        "src/config/authentication.rs",
        "src/config/connection.rs",
        "src/config/defines.rs",
        "src/config/options.rs",
        "src/config/ora_sql.rs",
        "src/config/section.rs",
        "src/config/system.rs",
        "src/config/yaml.rs",
        "src/constants.rs",
        "src/emit.rs",
        "src/lib.rs",
        "src/ora_sql.rs",
        "src/ora_sql/backend.rs",
        "src/ora_sql/custom.rs",
        "src/ora_sql/defaults.rs",
        "src/ora_sql/instance.rs",
        "src/ora_sql/section.rs",
        "src/ora_sql/sqls.rs",
        "src/ora_sql/types.rs",
        "src/platform.rs",
        "src/setup.rs",
        "src/types.rs",
        "src/utils.rs",
        ":version.rs",  # invalidates cache
    ],
    aliases = aliases(),
    crate_name = "mk_oracle",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    deps = all_crate_deps(),
)

rust_binary(
    name = "mk-oracle",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    crate_name = "mk_oracle",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    deps = all_crate_deps() + [":mk-oracle-lib"],
)

platform_transition_binary(
    name = "mk-oracle-musl",
    binary = ":mk-oracle",
    platform = "//bazel/platforms:x86_64-unknown-linux-musl",
    visibility = ["//visibility:public"],
)

rust_test(
    name = "mk-oracle-lib-test-internal",
    compile_data = [
        "tests/files/not-ora_sql.yml",
        "tests/files/not-yaml.yml",
        "tests/files/test-config.yml",
        "tests/files/test-mini.yml",
    ],
    crate = ":mk-oracle-lib",
)

rust_library(
    name = "mk-oracle-tests-common",
    testonly = 1,
    srcs = [
        "tests/common/mod.rs",
        "tests/common/tools.rs",
    ],
    crate_features = ["build_system_bazel"],
    crate_name = "common",
    crate_root = "tests/common/mod.rs",
    deps = all_crate_deps() + [
        ":mk-oracle-lib",
        "@host_crates//:assert_cmd",
        "@host_crates//:tempfile",
    ],
)

rust_test_suite(
    name = "mk-oracle-lib-test-external",
    srcs = [
        "tests/test_ora_sql.rs",
    ],
    compile_data = [
        "tests/files/not-ora_sql.yml",
        "tests/files/not-yaml.yml",
        "tests/files/test-config.yml",
        "tests/files/test-mini.yml",
    ],
    crate_features = ["build_system_bazel"],
    env_inherit = [
        "CI_TEST_SQL_DB_ENDPOINT",
        "CI_ORA2_DB_TEST",
    ],
    deps = all_crate_deps() + [
        ":mk-oracle",
        ":mk-oracle-lib",
        ":mk-oracle-tests-common",
        "@host_crates//:assert_cmd",
        "@host_crates//:tempfile",
    ],
)
