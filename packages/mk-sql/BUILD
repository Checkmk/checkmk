load("@host_crates//:defs.bzl", "aliases", "all_crate_deps")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files", "strip_prefix")
load("@rules_rust//rust:defs.bzl", "rust_doc", "rust_library", "rust_test_suite")
load("//bazel/rules:crlf_files.bzl", "crlf_files")
load("//bazel/rules:file_from_flag.bzl", "file_from_flag")
load("//bazel/rules:pkg.bzl", "pkg_tar")
load("//bazel/rules:xcomp/qemu_test.bzl", "qemu_test")
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

rust_binary(
    name = "mk-sql-windows",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    # Same artifact name as the Windows-node cargo build; the -windows
    # target name only disambiguates from the host binary.
    binary_name = "mk-sql",
    crate_name = "mk_sql",
    edition = "2021",
    opt = True,
    platform = "//bazel/platforms:x86_64-windows-msvc",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    strip = True,
    tags = ["manual"],
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":mk-sql-lib"],
)

static_crt_test(
    name = "mk-sql-windows-static-crt",
    binary = ":mk-sql-windows",
)

rust_binary(
    name = "mk-sql-musl",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    crate_name = "mk_sql",
    edition = "2021",
    opt = True,
    platform = "//bazel/platforms:x86_64-linux-musl",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    strip = True,
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":mk-sql-lib"],
)

rust_binary(
    name = "mk-sql-musl-aarch64",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    crate_name = "mk_sql",
    edition = "2021",
    opt = True,
    platform = "//bazel/platforms:aarch64-linux-musl",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    strip = True,
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

# The lib unit tests, cross compiled for Windows (cfg(windows) code
# paths: the SQL Server registry discovery and the platform code). Not
# directly runnable on Linux; executed under Wine by :mk-sql-tests-wine.
rust_test(
    name = "mk-sql-lib-test-internal-windows",
    compile_data = [
        "tests/files/no-mssql.yml",
        "tests/files/not-yaml.yml",
        "tests/files/test-config.yml",
        "tests/files/test-mini.yml",
    ],
    crate = ":mk-sql-lib",
    platform = "//bazel/platforms:x86_64-windows-msvc",
    tags = ["manual"],
)

filegroup(
    name = "test-registry-fixtures",
    srcs = glob(["tests/files/windows-registry/2.5.0/*.reg"]),
)

# Runs the Windows lib test binary under the pinned Wine. The
# registry-discovery tests expect the CI Windows node's SQL Server
# instances in the registry, and their own test sets; the prepare hook
# stages both into the throwaway Wine prefix, from wine-test-instances.reg
# and :test-registry-fixtures.
rust_wine_test(
    name = "mk-sql-tests-wine",
    binaries = [":mk-sql-lib-test-internal-windows"],
    data = [
        "wine-test-instances.reg",
        ":test-registry-fixtures",
    ],
    prepare = "wine-prepare.sh",
    prepare_args = [
        "$(rootpath wine-test-instances.reg)",
        "$(rootpaths :test-registry-fixtures)",
    ],
    skip_file = "wine-skipped-tests.txt",
)

# The integration tests, cross compiled for Windows and run inside the
# real-Windows QEMU VM by :mk-sql-tests-qemu below. They run the binary the
# runner stages at <cwd>/packages/mk-sql/mk-sql (build_system_bazel), so
# unlike :mk-sql-lib-test-external they do not depend on the host :mk-sql.
[
    rust_test(
        name = "%s-windows" % t,
        srcs = ["tests/%s.rs" % t],
        compile_data = [
            "tests/files/no-mssql.yml",
            "tests/files/not-yaml.yml",
            "tests/files/test-config.yml",
            "tests/files/test-no-ms-sql.yml",
            "tests/files/test-mini.yml",
        ],
        crate_features = ["build_system_bazel"],
        crate_root = "tests/%s.rs" % t,
        platform = "//bazel/platforms:x86_64-windows-msvc",
        tags = ["manual"],
        deps = all_crate_deps() + [
            ":mk-sql-lib",
            ":mk-sql-tests-common",
            "@host_crates//:assert_cmd",
            "@host_crates//:tempfile",
        ],
    )
    for t in [
        "test_ms_sql",
        "test_running_instances",
    ]
]

# cmd.exe needs CRLF line ends, which a Linux checkout lacks.
crlf_files(
    name = "qemu_tests_script",
    srcs = ["rust-test-qemu.cmd"],
    suffixes = [".cmd"],
)

pkg_files(
    name = "qemu_tests_root",
    testonly = True,
    srcs = [
        ":mk-sql-lib-test-internal-windows",
        ":qemu_tests_script",
        ":test_ms_sql-windows",
        ":test_running_instances-windows",
    ],
    tags = ["manual"],
)

pkg_files(
    name = "qemu_tests_binary",
    srcs = [":mk-sql-windows"],
    prefix = "packages/mk-sql",
    tags = ["manual"],
)

pkg_files(
    name = "qemu_tests_fixtures",
    srcs = [
        "tests/files/ci-scripts/manage-test-registry-set.ps1",
        ":test-registry-fixtures",
    ],
    strip_prefix = strip_prefix.from_pkg(),
)

# The guest's directory, the tests' cwd:
#   *.exe                     the test binaries
#   packages\mk-sql\          mk-sql.exe
#   tests\files\              the registry test sets and
#                             manage-test-registry-set.ps1
pkg_tar(
    name = "qemu_tests_stage",
    testonly = True,
    srcs = [
        ":qemu_tests_binary",
        ":qemu_tests_fixtures",
        ":qemu_tests_root",
        "//bazel/tools/windows_vm:run_rust_tests",
    ],
    extension = "tar.gz",
    tags = ["manual"],
)

# Runs the Windows lib and integration tests inside the real-Windows QEMU
# VM against the image's SQL Server instances, with the registry fixtures
# imported. The remote tests use the guest's own SQL Server too (see
# rust_test_qemu.py).
qemu_test(
    name = "mk-sql-tests-qemu",
    src = "rust_test_qemu.py",
    args = ["$(rootpath qemu-skipped-tests.txt)"],
    data = ["qemu-skipped-tests.txt"],
    stage = ":qemu_tests_stage",
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
