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
        ":cmk-compute-api-spec",
        ":cmk-convert-rrds",
        ":cmk-create-rrd",
        ":cmk-generate-api-spec",
        ":cmk-migrate-extension-rulesets",
        ":cmk-migrate-http",
        ":cmk-monitor-apache",
        ":cmk-monitor-broker",
        ":cmk-monitor-core",
        ":cmk-monitor-diskusage",
        ":cmk-monitor-mkbackup",
        ":cmk-monitor-mknotifyd",
        ":cmk-passwd",
        ":cmk-piggyback",
        ":cmk-piggyback-hub",
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
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":bin_750",
        ":bin_755",
        ":cmk_link",
    ],
    visibility = ["//visibility:public"],
)
