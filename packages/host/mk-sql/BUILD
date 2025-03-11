load("@cargo_deps_host//:defs.bzl", "aliases", "all_crate_deps")
load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_library", "rust_test", "rust_test_suite")

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
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":mk-sql-lib"],
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
        "@cargo_deps_host//:assert_cmd",
        "@cargo_deps_host//:tempfile",
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
        "@cargo_deps_host//:assert_cmd",
        "@cargo_deps_host//:tempfile",
    ],
)
