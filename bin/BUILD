load("@aspect_rules_py//py:defs.bzl", "py_library")
load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files", "pkg_mklink")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:xcomp/cc.bzl", "cc_binary")

cc_binary(
    name = "mkevent",
    srcs = ["mkevent.cc"],
    copts = [
        "-g",
        "-O3",
        "-Wall",
        "-Wextra",
    ],
    features = [
        "static_libstdcpp",
    ],
    tags = ["no-lint"],
)

cc_binary(
    name = "mkeventd_open514",
    srcs = ["mkeventd_open514.cc"],
    copts = [
        "-g",
        "-O3",
        "-Wall",
        "-Wextra",
    ],
    features = [
        "static_libstdcpp",
    ],
    tags = ["no-lint"],
)

pkg_mklink(
    name = "cmk_link",
    link_name = "bin/cmk",
    target = "check_mk",
)

pkg_files(
    name = "bin_750",
    srcs = [
        ":mkeventd_open514",
    ],
    attributes = pkg_attributes(
        mode = "0750",
    ),
    prefix = "bin",
)

pkg_files(
    name = "bin_755",
    srcs = [
        ":check_mk.py",
        ":cmk-generate-api-spec",
        ":cmk-migrate-extension-rulesets.py",
        ":cmk-migrate-oracle-rulesets.py",
        ":cmk-monitor-apache",
        ":cmk-monitor-broker",
        ":cmk-monitor-core",
        ":cmk-monitor-diskusage",
        ":cmk-monitor-mkbackup",
        ":cmk-monitor-mknotifyd",
        ":cmk-monitor-otel-collector",
        ":cmk-piggyback.py",
        ":cmk-piggyback-hub.py",
        ":cmk-ui-job-scheduler.py",
        ":cmk-ui-job-scheduler-health",
        ":cmk-validate-config.py",
        ":init-redis.py",
        ":message-broker-certs",
        ":mkevent",
        ":mkp.py",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {
        "check_mk.py": "check_mk",
        "cmk-migrate-extension-rulesets.py": "cmk-migrate-extension-rulesets",
        "cmk-migrate-oracle-rulesets.py": "cmk-migrate-oracle-rulesets",
        "cmk-piggyback-hub.py": "cmk-piggyback-hub",
        "cmk-piggyback.py": "cmk-piggyback",
        "cmk-ui-job-scheduler.py": "cmk-ui-job-scheduler",
        "cmk-validate-config.py": "cmk-validate-config",
        "init-redis.py": "init-redis",
        "mkp.py": "mkp",
    },
)

pkg_files(
    name = "mkeventd",
    srcs = ["mkeventd.py"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {"mkeventd.py": "mkeventd"},
)

pkg_files(
    name = "cmk-create-rrd",
    srcs = ["cmk-create-rrd.py"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {"cmk-create-rrd.py": "cmk-create-rrd"},
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":bin_750",
        ":bin_755",
        ":cmk-create-rrd",
        ":cmk_link",
        ":mkeventd",
    ],
    stamp = 1,
    visibility = ["//visibility:public"],
)

# Not shipped — only exists so that static analysis tools (ruff, …)
# can discover these .py files via Bazel.
py_library(
    name = "mkeventd_main",
    srcs = ["mkeventd.py"],
    imports = ["."],
    deps = [
        "//cmk/utils:paths",
        "//packages/cmk-ec",
    ],
)

py_library(
    name = "cmk-create-rrd_main",
    srcs = ["cmk-create-rrd.py"],
    imports = ["."],
    deps = ["//cmk/rrd"],
)

py_library(
    name = "check_mk_py",
    srcs = ["check_mk.py"],
    imports = ["."],
    tags = ["no-mypy"],
)

py_library(
    name = "cmk_piggyback_hub_py",
    srcs = ["cmk-piggyback-hub.py"],
    imports = ["."],
    deps = [
        "//cmk/piggyback:hub",
        "//cmk/utils",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version",
        "//packages/cmk-crash:crash",
    ],
)

py_library(
    name = "cmk_piggyback_py",
    srcs = ["cmk-piggyback.py"],
    imports = ["."],
    deps = [
        "//cmk/piggyback:backend",
        "//cmk/utils:paths",
        "//packages/cmk-livestatus-client",
    ],
)

py_library(
    name = "cmk_migrate_extension_rulesets_py",
    srcs = ["cmk-migrate-extension-rulesets.py"],
    imports = ["."],
    deps = [
        "//cmk/gui:app",
        "//cmk/gui:config",
        "//cmk/gui:session_context",
        "//cmk/gui/rule_specs:loader",
        "//cmk/gui/rule_specs:types",
        "//cmk/gui/watolib",
        "//cmk/update_config",
        "//cmk/utils",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:version",
        "//packages/cmk-mkp-tool",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:rulesets",
        "//packages/cmk-wsgi",
    ],
)

py_library(
    name = "cmk_migrate_oracle_rulesets_py",
    srcs = ["cmk-migrate-oracle-rulesets.py"],
    imports = ["."],
    deps = [
        "//cmk/gui:app",
        "//cmk/gui/watolib",
        "//cmk/update_config",
        "//cmk/utils",
        "//cmk/utils:paths",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "cmk_ui_job_scheduler_py",
    srcs = ["cmk-ui-job-scheduler.py"],
    imports = ["."],
    deps = ["//cmk/gui/job_scheduler"],
)

py_library(
    name = "cmk_validate_config_py",
    srcs = ["cmk-validate-config.py"],
    imports = ["."],
    deps = [
        "//cmk:validate_config",
        "//cmk/base:config",
        "//cmk/gui:app",
        "//cmk/utils:paths",
        "//cmk/utils:redis",
        "//packages/cmk-ccc:version",
        "//packages/cmk-wsgi",
    ],
)

py_library(
    name = "init_redis_py",
    srcs = ["init-redis.py"],
    imports = ["."],
    tags = ["no-mypy"],
    deps = ["//cmk/gui/search:index"],
)

py_library(
    name = "mkp_py",
    srcs = ["mkp.py"],
    imports = ["."],
    deps = [
        "//cmk/gui/search:index",
        "//cmk/utils",
        "//packages/cmk-ccc:store",
        "//packages/cmk-ccc:version",
        "//packages/cmk-ec",
        "//packages/cmk-mkp-tool",
        "//packages/cmk-plugin-apis:discover_plugins",
    ],
)

sh_library(
    name = "bin_sh",
    srcs = [
        ".f12",
        "apply_unsign_msi_patch.sh",
        "cmk-monitor-apache",
        "cmk-monitor-broker",
        "cmk-monitor-core",
        "cmk-monitor-diskusage",
        "cmk-monitor-mkbackup",
        "cmk-monitor-mknotifyd",
        "cmk-monitor-otel-collector",
        "cmk-ui-job-scheduler-health",
        "message-broker-certs",
    ],
)
