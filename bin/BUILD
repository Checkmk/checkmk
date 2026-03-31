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
        ":cmk-automation-helper.py",
        ":cmk-broker-test.py",
        ":cmk-cert.py",
        ":cmk-config-anonymizer",
        ":cmk-convert-rrds",
        ":cmk-general-version-infos",
        ":cmk-generate-api-spec",
        ":cmk-migrate-extension-rulesets.py",
        ":cmk-monitor-apache",
        ":cmk-monitor-broker",
        ":cmk-monitor-core",
        ":cmk-monitor-diskusage",
        ":cmk-monitor-mkbackup",
        ":cmk-monitor-mknotifyd",
        ":cmk-monitor-otel-collector",
        ":cmk-passwd.py",
        ":cmk-piggyback.py",
        ":cmk-piggyback-hub.py",
        ":cmk-pwstore",
        ":cmk-transform-inventory-trees",
        ":cmk-ui-job-scheduler.py",
        ":cmk-ui-job-scheduler-health",
        ":cmk-update-license-usage.py",
        ":cmk-validate-config.py",
        ":cmk-validate-plugins.py",
        ":init-redis.py",
        ":livedump",
        ":message-broker-certs",
        ":mkbackup.py",
        ":mkevent",
        ":mkp.py",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {
        "check_mk.py": "check_mk",
        "cmk-automation-helper.py": "cmk-automation-helper",
        "cmk-broker-test.py": "cmk-broker-test",
        "cmk-cert.py": "cmk-cert",
        "cmk-migrate-extension-rulesets.py": "cmk-migrate-extension-rulesets",
        "cmk-passwd.py": "cmk-passwd",
        "cmk-piggyback-hub.py": "cmk-piggyback-hub",
        "cmk-piggyback.py": "cmk-piggyback",
        "cmk-ui-job-scheduler.py": "cmk-ui-job-scheduler",
        "cmk-update-license-usage.py": "cmk-update-license-usage",
        "cmk-validate-config.py": "cmk-validate-config",
        "cmk-validate-plugins.py": "cmk-validate-plugins",
        "init-redis.py": "init-redis",
        "mkbackup.py": "mkbackup",
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
        ":cmk-product-usage",
        ":cmk-pwstore",
        ":cmk_link",
        ":mkeventd",
    ],
    stamp = 1,
    visibility = ["//visibility:public"],
)

pkg_files(
    name = "cmk-product-usage",
    srcs = ["//cmk/product_usage:cli.py"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    renames = {"//cmk/product_usage:cli.py": "bin/cmk-product-usage"},
)

pkg_files(
    name = "cmk-pwstore",
    srcs = ["//cmk/utils:password_store/cli.py"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    renames = {"//cmk/utils:password_store/cli.py": "bin/cmk-pwstore"},
)

# Not shipped — only exists so that static analysis tools (ruff, …)
# can discover these .py files via Bazel.
py_library(
    name = "mkeventd_main",
    srcs = ["mkeventd.py"],
    imports = ["."],
    deps = [
        "//cmk/utils",
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
    name = "cmk_update_license_usage_py",
    srcs = ["cmk-update-license-usage.py"],
    imports = ["."],
    tags = ["no-mypy"],
)

py_library(
    name = "check_mk_py",
    srcs = ["check_mk.py"],
    imports = ["."],
    tags = ["no-mypy"],
)

py_library(
    name = "cmk_automation_helper_py",
    srcs = ["cmk-automation-helper.py"],
    imports = ["."],
    tags = ["no-mypy"],
)

py_library(
    name = "cmk_broker_test_py",
    srcs = ["cmk-broker-test.py"],
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
        "//packages/cmk-ccc:crash-reporting",
        "//packages/cmk-ccc:hostaddress",
        "//packages/cmk-ccc:version",
    ],
)

py_library(
    name = "cmk_piggyback_py",
    srcs = ["cmk-piggyback.py"],
    imports = ["."],
    deps = [
        "//cmk/piggyback:backend",
        "//cmk/utils",
        "//packages/cmk-livestatus-client",
        "//packages/cmk-livestatus-client:py_livestatus",
    ],
)

py_library(
    name = "cmk_migrate_extension_rulesets_py",
    srcs = ["cmk-migrate-extension-rulesets.py"],
    imports = ["."],
    deps = [
        "//cmk/gui",
        "//cmk/update_config",
        "//cmk/utils",
        "//packages/cmk-ccc:version",
        "//packages/cmk-mkp-tool",
        "//packages/cmk-plugin-apis:discover_plugins",
        "//packages/cmk-plugin-apis:rulesets",
    ],
)

py_library(
    name = "cmk_ui_job_scheduler_py",
    srcs = ["cmk-ui-job-scheduler.py"],
    imports = ["."],
    tags = ["no-mypy"],
)

py_library(
    name = "cmk_validate_config_py",
    srcs = ["cmk-validate-config.py"],
    imports = ["."],
    tags = ["no-mypy"],
)

py_library(
    name = "cmk_validate_plugins_py",
    srcs = ["cmk-validate-plugins.py"],
    imports = ["."],
    deps = ["//cmk:validate_plugins"],
)

py_library(
    name = "init_redis_py",
    srcs = ["init-redis.py"],
    imports = ["."],
    tags = ["no-mypy"],
)

py_library(
    name = "mkbackup_py",
    srcs = ["mkbackup.py"],
    imports = ["."],
    tags = ["no-mypy"],
)

py_library(
    name = "cmk_cert_py",
    srcs = ["cmk-cert.py"],
    imports = ["."],
    deps = ["//cmk/gui"],
)

py_library(
    name = "cmk_passwd_py",
    srcs = ["cmk-passwd.py"],
    imports = ["."],
    deps = ["//cmk:cmkpasswd"],
)

py_library(
    name = "mkp_py",
    srcs = ["mkp.py"],
    imports = ["."],
    deps = [
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
        "cmk-general-version-infos",
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
