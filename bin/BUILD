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
        ":check_mk",
        ":cmk-automation-helper",
        ":cmk-broker-test",
        ":cmk-cert",
        ":cmk-config-anonymizer",
        ":cmk-convert-rrds",
        ":cmk-general-version-infos",
        ":cmk-generate-api-spec",
        ":cmk-migrate-extension-rulesets",
        ":cmk-monitor-apache",
        ":cmk-monitor-broker",
        ":cmk-monitor-core",
        ":cmk-monitor-diskusage",
        ":cmk-monitor-mkbackup",
        ":cmk-monitor-mknotifyd",
        ":cmk-monitor-otel-collector",
        ":cmk-passwd",
        ":cmk-piggyback",
        ":cmk-piggyback-hub",
        ":cmk-pwstore",
        ":cmk-transform-inventory-trees",
        ":cmk-ui-job-scheduler",
        ":cmk-ui-job-scheduler-health",
        ":cmk-update-license-usage",
        ":cmk-validate-config",
        ":cmk-validate-plugins",
        ":init-redis",
        ":livedump",
        ":message-broker-certs",
        ":mkbackup",
        ":mkevent",
        ":mkp",
        ":post-rename-site.py",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {
        "post-rename-site.py": "post-rename-site",
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
    name = "post_rename_site_py",
    srcs = ["post-rename-site.py"],
    imports = ["."],
    deps = ["//cmk/post_rename_site"],
)

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
