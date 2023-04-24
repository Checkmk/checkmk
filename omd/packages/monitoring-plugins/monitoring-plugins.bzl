load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def monitoring_plugins(version_str, sha256):
    http_archive(
        name="monitoring-plugins",
        build_file="@omd_packages//packages/monitoring-plugins:BUILD.monitoring-plugins.bazel",
        urls=[
            "https://www.monitoring-plugins.org/download/monitoring-plugins-" + version_str + ".tar.gz",
            UPSTREAM_MIRROR_URL + "monitoring-plugins-" + version_str + ".tar.gz",
        ],
        sha256=sha256,
        strip_prefix="monitoring-plugins-" + version_str,
        patches=[
            "//packages/monitoring-plugins:patches/0001-check-icmp-allows-pl-of-101.dif",
            "//packages/monitoring-plugins:patches/0003-cmk-password-store.dif",
            "//packages/monitoring-plugins:patches/0006-check_mysql-define-own-mysql-port.dif",
            "//packages/monitoring-plugins:patches/0009-check_dns-case-insensitive.dif",
            "//packages/monitoring-plugins:patches/0010-get_omd_root_in_checks.dif",
            "//packages/monitoring-plugins:patches/0011-check_http-sanitise-http-response-body.dif",
        ],
        patch_args=["-p1"],
        patch_tool="patch",
    )
