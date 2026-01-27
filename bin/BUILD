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
        ":check_mk",
        ":cmk-automation-helper",
        ":cmk-broker-test",
        ":cmk-cert",
        ":cmk-config-anonymizer.py",
        ":cmk-convert-rrds",
        ":cmk-create-rrd",
        ":cmk-general-version-infos",
        ":cmk-generate-api-spec",
        ":cmk-metric-backend-monitoring.py",
        ":cmk-migrate-extension-rulesets",
        ":cmk-migrate-http",
        ":cmk-monitor-apache",
        ":cmk-monitor-broker",
        ":cmk-monitor-core",
        ":cmk-monitor-diskusage",
        ":cmk-monitor-metric-backend",
        ":cmk-monitor-mkbackup",
        ":cmk-monitor-mknotifyd",
        ":cmk-monitor-otel-collector",
        ":cmk-passwd",
        ":cmk-piggyback",
        ":cmk-piggyback-hub",
        ":cmk-pwstore",
        ":cmk-telemetry",
        ":cmk-transform-inventory-trees",
        ":cmk-ui-job-scheduler",
        ":cmk-ui-job-scheduler-health",
        ":cmk-update-config",
        ":cmk-update-license-usage",
        ":cmk-validate-config",
        ":cmk-validate-plugins",
        ":init-redis",
        ":livedump",
        ":message-broker-certs",
        ":mkbackup",
        ":mkevent",
        ":mkeventd",
        ":mkp",
        ":post-rename-site",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {
        ":cmk-config-anonymizer.py": "cmk-config-anonymizer",
    },
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":bin_750",
        ":bin_755",
        ":cmk-pwstore",
        ":cmk-telemetry",
        ":cmk_link",
    ],
    stamp = 1,
    visibility = ["//visibility:public"],
)

pkg_files(
    name = "cmk-pwstore",
    srcs = ["//cmk:utils/password_store/cli.py"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    renames = {"//cmk:utils/password_store/cli.py": "bin/cmk-pwstore"},
)

pkg_files(
    name = "cmk-telemetry",
    srcs = ["//cmk:product_telemetry/cmk_telemetry_cli.py"],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    renames = {"//cmk:product_telemetry/cmk_telemetry_cli.py": "bin/cmk-telemetry"},
)
