load("@host_crates//:defs.bzl", "aliases", "all_crate_deps")
load("@rules_rust//rust:defs.bzl", "rust_doc", "rust_library", "rust_test_suite")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:xcomp/rust.bzl", "rust_binary", "rust_test")
load("//bazel/rules:xcomp/rust_wine_test.bzl", "rust_wine_test")
load("//bazel/testing:static_crt.bzl", "static_crt_test")

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
        "src/config/merge.rs",
        "src/config/migration.rs",
        "src/config/options.rs",
        "src/config/ora_sql.rs",
        "src/config/section.rs",
        "src/config/system.rs",
        "src/config/target.rs",
        "src/config/yaml.rs",
        "src/constants.rs",
        "src/emit.rs",
        "src/lib.rs",
        "src/ora_sql.rs",
        "src/ora_sql/backend.rs",
        "src/ora_sql/custom.rs",
        "src/ora_sql/defaults.rs",
        "src/ora_sql/detect.rs",
        "src/ora_sql/instance.rs",
        "src/ora_sql/pdbs.rs",
        "src/ora_sql/perf.rs",
        "src/ora_sql/section.rs",
        "src/ora_sql/spots.rs",
        "src/ora_sql/sqls.rs",
        "src/ora_sql/system.rs",
        "src/ora_sql/types.rs",
        "src/permissions_linux.rs",
        "src/permissions_windows.rs",
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
    opt = True,
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    strip = True,
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":mk-oracle-lib"],
)

rust_binary(
    name = "mk-oracle-windows",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    # Same artifact name as the Windows-node cargo build; the -windows
    # target name only disambiguates from the host binary.
    binary_name = "mk-oracle",
    crate_name = "mk_oracle",
    edition = "2021",
    opt = True,
    platform = "//bazel/platforms:x86_64-windows-msvc",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    strip = True,
    tags = ["manual"],
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":mk-oracle-lib"],
)

static_crt_test(
    name = "mk-oracle-windows-static-crt",
    binary = ":mk-oracle-windows",
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
        "tests/test_mk_oracle_bin.rs",
        "tests/test_ora_discovery.rs",
        "tests/test_ora_no_db.rs",
        "tests/test_ora_with_db.rs",
    ],
    compile_data = [
        "tests/files/tns/tnsnames.ora",
        "tests/files/not-ora_sql.yml",
        "tests/files/not-yaml.yml",
        "tests/files/test-config.yml",
        "tests/files/test-mini.yml",
    ] + glob([
        "tests/files/orasql_abs/**/*.sql",
        "tests/files/orasql_runtime/**/*.sql",
        "tests/files/orasql_config/**/*.sql",
    ]),
    crate_features = ["build_system_bazel"],
    data = [
        "references/output-multiple.cfg",
        "references/output-multiple.ps1",
        "references/output-optional.cfg",
        "references/output-optional.ps1",
        "references/output-xe-no-tnsalias.cfg",
    ],
    env_inherit = [
        # CI_ORA2_DB_TEST: mandatory reference endpoint. CI_ORA1_DB_TEST:
        # optional second endpoint, included by the endpoint-iterating tests
        # when set.
        "CI_ORA1_DB_TEST",
        "CI_ORA2_DB_TEST",
        "LD_LIBRARY_PATH",
        "MK_CONFDIR",
        "MK_LIBDIR",
        "ORACLE_HOME",
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

# The lib unit tests, cross compiled for Windows: the legacy Windows
# job's unfiltered `cargo test` runs these on Windows too (they cover
# permissions_windows.rs and the registry/platform code). Executed
# under Wine by :mk-oracle-tests-wine.
rust_test(
    name = "mk-oracle-lib-test-internal-windows",
    compile_data = [
        "tests/files/not-ora_sql.yml",
        "tests/files/not-yaml.yml",
        "tests/files/test-config.yml",
        "tests/files/test-mini.yml",
    ],
    crate = ":mk-oracle-lib",
    platform = "//bazel/platforms:x86_64-windows-msvc",
    tags = ["manual"],
)

# Runs the Windows lib test binary under the pinned Wine.
rust_wine_test(
    name = "mk-oracle-tests-wine",
    binaries = [":mk-oracle-lib-test-internal-windows"],
    prepare = "wine-prepare.sh",
    skip_file = "wine-skipped-tests.txt",
)
