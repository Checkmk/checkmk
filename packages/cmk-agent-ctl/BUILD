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
    name = "cmk-agent-ctl-lib",
    srcs = [
        "src/agent_receiver_api.rs",
        "src/certs.rs",
        "src/cli.rs",
        "src/configuration.rs",
        "src/configuration/config.rs",
        "src/configuration/migrate.rs",
        "src/constants.rs",
        "src/lib.rs",
        "src/log_ext.rs",
        "src/mailslot_transport.rs",
        "src/misc.rs",
        "src/modes.rs",
        "src/modes/daemon.rs",
        "src/modes/delete_connection.rs",
        "src/modes/dump.rs",
        "src/modes/import_connection.rs",
        "src/modes/pull.rs",
        "src/modes/push.rs",
        "src/modes/registration.rs",
        "src/modes/renew_certificate.rs",
        "src/modes/status.rs",
        "src/monitoring_data.rs",
        "src/monitoring_data/linux.rs",
        "src/monitoring_data/win.rs",
        "src/setup.rs",
        "src/site_spec.rs",
        "src/tls_server.rs",
        "src/types.rs",
        ":version.rs",  # invalidates the cache
    ],
    aliases = aliases(),
    crate_name = "cmk_agent_ctl",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    deps = all_crate_deps(),
)

rust_test(
    name = "cmk-agent-ctl-lib-internal",
    crate = ":cmk-agent-ctl-lib",
    deps = all_crate_deps() + [
        ":cmk-agent-ctl-lib",
        "@host_crates//:assert_cmd",
        "@host_crates//:lazy_static",
        "@host_crates//:predicates",
        "@host_crates//:tempfile",
        "@host_crates//:time",
    ],
)

# The lib tests compiled for Windows (cfg(windows) code paths: mailslot
# transport, monitoring_data/win, Windows setup). Not directly runnable
# on Linux; executed under Wine by :cmk-agent-ctl-tests-wine.
rust_test(
    name = "cmk-agent-ctl-lib-internal-windows",
    crate = ":cmk-agent-ctl-lib",
    platform = "//bazel/platforms:x86_64-windows-msvc",
    tags = ["manual"],
    deps = all_crate_deps() + [
        ":cmk-agent-ctl-lib",
        "@host_crates//:assert_cmd",
        "@host_crates//:lazy_static",
        "@host_crates//:predicates",
        "@host_crates//:tempfile",
        "@host_crates//:time",
    ],
)

# The external (integration) tests compiled for Windows, spawning the
# cross-built controller. Executed under Wine by :cmk-agent-ctl-tests-wine
# alongside the lib tests.
[
    rust_test(
        name = "%s-windows" % t,
        srcs = ["tests/%s.rs" % t],
        crate_features = ["build_system_bazel"],
        crate_root = "tests/%s.rs" % t,
        data = [":cmk-agent-ctl-windows"],
        platform = "//bazel/platforms:x86_64-windows-msvc",
        tags = ["manual"],
        deps = all_crate_deps() + [
            ":cmk-agent-ctl-lib",
            ":cmk-agent-ctl-tests-common",
            "@host_crates//:assert_cmd",
            "@host_crates//:lazy_static",
            "@host_crates//:predicates",
            "@host_crates//:tempfile",
        ],
    )
    for t in [
        "test_cli",
        "test_pull",
        "test_status",
    ]
]

# Runs the Windows test binaries (lib + external) under the pinned Wine —
# the Linux stand-in for `cargo test --target x86_64-pc-windows-msvc`
# (non-elevated subset; see wine-skipped-tests.txt).
rust_wine_test(
    name = "cmk-agent-ctl-tests-wine",
    binaries = [
        ":cmk-agent-ctl-lib-internal-windows",
        ":test_cli-windows",
        ":test_pull-windows",
        ":test_status-windows",
    ],
    data = [":cmk-agent-ctl-windows"],
    prepare = "wine-prepare.sh",
    prepare_args = ["$(rootpath :cmk-agent-ctl-windows)"],
    skip_file = "wine-skipped-tests.txt",
    tags = [
        # The tests bind loopback ports; concurrent instances collide.
        "exclusive",
    ],
)

rust_library(
    name = "cmk-agent-ctl-tests-common",
    testonly = 1,
    srcs = [
        "tests/common/agent/linux.rs",
        "tests/common/agent/mod.rs",
        "tests/common/agent/win.rs",
        "tests/common/certs.rs",
        "tests/common/mod.rs",
    ],
    crate_features = ["build_system_bazel"],
    crate_name = "common",
    crate_root = "tests/common/mod.rs",
    deps = all_crate_deps() + [
        ":cmk-agent-ctl-lib",
        "@host_crates//:assert_cmd",
        "@host_crates//:lazy_static",
        "@host_crates//:predicates",
        "@host_crates//:tempfile",
        "@host_crates//:time",
    ],
)

rust_test_suite(
    name = "cmk-agent-ctl-lib-external",
    srcs = [
        "tests/test_cli.rs",
        "tests/test_pull.rs",
        "tests/test_status.rs",
    ],
    crate_features = ["build_system_bazel"],
    env = {
        "CMK_AGENT_CTL_PATH": "$(execpaths :cmk-agent-ctl)",
        "ROOTPATH": "$(location :cmk-agent-ctl)",
        "RUST_BACKTRACE": "1",
    },
    env_inherit = [
        "CMK_AGENT_CTL_LOG_TO_FILE",
        "DEBUG_CONNECTION_TIMEOUT",
        "DEBUG_HOME_DIR",
        "DEBUG_MAX_CONNECTIONS",
        "ENV_PROGRAM_DATA",
        "MK_LOGDIR",
    ],
    deps = all_crate_deps() + [
        ":cmk-agent-ctl",
        ":cmk-agent-ctl-lib",
        ":cmk-agent-ctl-tests-common",
        "@host_crates//:assert_cmd",
        "@host_crates//:lazy_static",
        "@host_crates//:predicates",
        "@host_crates//:tempfile",
    ],
)

rust_binary(
    name = "cmk-agent-ctl",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    crate_name = "cmk_agent_ctl",
    edition = "2021",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    deps = all_crate_deps() + [":cmk-agent-ctl-lib"],
)

rust_binary(
    name = "cmk-agent-ctl-musl",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    crate_name = "cmk_agent_ctl",
    edition = "2021",
    opt = True,
    platform = "//bazel/platforms:x86_64-linux-musl",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    strip = True,
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":cmk-agent-ctl-lib"],
)

rust_binary(
    name = "cmk-agent-ctl-musl-aarch64",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    crate_name = "cmk_agent_ctl",
    edition = "2021",
    opt = True,
    platform = "//bazel/platforms:aarch64-linux-musl",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    strip = True,
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":cmk-agent-ctl-lib"],
)

rust_binary(
    name = "cmk-agent-ctl-windows",
    srcs = ["src/main.rs"],
    aliases = aliases(),
    # Same artifact name as the Windows-node cargo build; the -windows
    # target name only disambiguates from the host binary.
    binary_name = "cmk-agent-ctl",
    crate_name = "cmk_agent_ctl",
    edition = "2021",
    opt = True,
    platform = "//bazel/platforms:x86_64-windows-msvc",
    proc_macro_deps = all_crate_deps(
        proc_macro = True,
    ),
    strip = True,
    tags = ["manual"],
    visibility = ["//visibility:public"],
    deps = all_crate_deps() + [":cmk-agent-ctl-lib"],
)

static_crt_test(
    name = "cmk-agent-ctl-windows-static-crt",
    binary = ":cmk-agent-ctl-windows",
)

rust_doc(
    name = "doc",
    crate = ":cmk-agent-ctl-lib",
    rustdoc_flags = ["--document-private-items"],
    tags = ["manual"],
)
