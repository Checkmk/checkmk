load("@bazel_skylib//rules:build_test.bzl", "build_test")
load("@host_crates//:defs.bzl", "aliases", "all_crate_deps")
load("@rules_rust//rust:defs.bzl", "rust_binary", "rust_doc", "rust_library", "rust_test", "rust_test_suite")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")

file_from_flag(
    name = "version.rs",
    out = "src/version.rs",
    content = ['pub const VERSION: &str = "{VERSION}";'],
    replace_labels = {"VERSION": "@cmk//version"},
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
        "src/ora_sql/system.rs",
        "src/ora_sql/types.rs",
        "src/platform.rs",
        "src/setup.rs",
        "src/types.rs",
        "src/utils.rs",
        ":version.rs",  # invalidates cache
    ],
    aliases = aliases(),
    compile_data = [
        "sqls/asm_diskgroup.10020000.all.sql",
        "sqls/asm_diskgroup.12010000.all.sql",
        "sqls/asm_instance.0.all.sql",
        "sqls/dataguard_stats.10020000.all.sql",
        "sqls/instance.0.all.sql",
        "sqls/instance.12010002.all.sql",
        "sqls/io_stats.0.all.sql",
        "sqls/jobs.10020000.all.sql",
        "sqls/jobs.12010000.all.sql",
        "sqls/locks.10020000.all.sql",
        "sqls/locks.12010000.all.sql",
        "sqls/logswitches.0.all.sql",
        "sqls/longactivesessions.10010000.all.sql",
        "sqls/longactivesessions.12010000.all.sql",
        "sqls/performance.10010000.all.sql",
        "sqls/performance.12010000.all.sql",
        "sqls/processes.0.all.sql",
        "sqls/recovery_area.0.all.sql",
        "sqls/recovery_status.10010000.all.sql",
        "sqls/recovery_status.12010000.all.sql",
        "sqls/resumable.0.all.sql",
        "sqls/rman.10020000.all.sql",
        "sqls/rman.12010000.all.sql",
        "sqls/sessions.0.all.sql",
        "sqls/sessions.12010000.all.sql",
        "sqls/systemparameter.0.all.sql",
        "sqls/tablespaces.10020000.all.sql",
        "sqls/tablespaces.12010000.all.sql",
        "sqls/ts_quotas.0.all.sql",
        "sqls/undostat.10020000.all.sql",
        "sqls/undostat.12010000.all.sql",
    ],
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
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":mk-oracle-lib"],
)

build_test(
    name = "build_test",
    targets = [":mk-oracle"],
)

rust_test(
    name = "mk-oracle-lib-test-internal",
    compile_data = [
        "tests/files/not-ora_sql.yml",
        "tests/files/not-yaml.yml",
        "tests/files/test-config.yml",
        "tests/files/test-mini.yml",
        "tests/files/endpoints.txt",
    ],
    crate = ":mk-oracle-lib",
    env_inherit = [
        "MK_CONFDIR",
    ],
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
        "tests/files/tns/tnsnames.ora",
        "tests/files/not-ora_sql.yml",
        "tests/files/not-yaml.yml",
        "tests/files/test-config.yml",
        "tests/files/test-mini.yml",
        "tests/files/endpoints.txt",
    ],
    crate_features = ["build_system_bazel"],
    env_inherit = [
        "CI_ORA2_DB_TEST",
        "LD_LIBRARY_PATH",
        "MK_CONFDIR",
        "MK_LIBDIR",
    ],
    deps = all_crate_deps() + [
        ":mk-oracle",
        ":mk-oracle-lib",
        ":mk-oracle-tests-common",
        "@host_crates//:assert_cmd",
        "@host_crates//:tempfile",
    ],
)

rust_doc(
    name = "doc",
    crate = ":mk-oracle-lib",
)
