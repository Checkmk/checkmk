load("@rules_pkg//pkg:mappings.bzl", "pkg_attributes", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("//bazel/rules:xcomp/cc.bzl", "cc_binary")

#
# Don't add new stuff to this file!
#
# See doc/documentation/arch-migrations.rst
#

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
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
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
    platform = "//bazel/platforms:x86_64-linux-gcc-hermetic",
    tags = ["no-lint"],
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
        ":cmk-ui-job-scheduler-health",
        ":mkevent",
    ],
    attributes = pkg_attributes(
        mode = "0755",
    ),
    prefix = "bin",
    renames = {
        "cmk-migrate-extension-rulesets.py": "cmk-migrate-extension-rulesets",
        "cmk-migrate-oracle-rulesets.py": "cmk-migrate-oracle-rulesets",
    },
)

pkg_tar(
    name = "pkg_tar",
    srcs = [
        ":bin_750",
        ":bin_755",
    ],
    stamp = 1,
    visibility = ["//visibility:public"],
)

# Not shipped — only exists so that static analysis tools (ruff, …)
# can discover these .py files via Bazel.
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
        "//cmk/utils:redis",
        "//packages/cmk-ccc:log",
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
        "//cmk/utils:paths",
        "//packages/cmk-ccc:log",
        "//packages/cmk-ccc:version",
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
    ],
)
