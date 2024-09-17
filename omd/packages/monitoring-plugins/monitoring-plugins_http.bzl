load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def monitoring_plugins(version_str, sha256):
    filename = "monitoring-plugins-" + version_str + ".tar.gz"
    http_archive(
        name = "monitoring-plugins",
        build_file = "@omd_packages//omd/packages/monitoring-plugins:BUILD.monitoring-plugins.bazel",
        urls = [
            "https://www.monitoring-plugins.org/download/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        strip_prefix = "monitoring-plugins-" + version_str,
        patches = [
            "//omd/packages/monitoring-plugins:patches/0001-check-icmp-allows-pl-of-101.dif",
            "//omd/packages/monitoring-plugins:patches/0003-cmk-password-store.dif",
            "//omd/packages/monitoring-plugins:patches/0006-check_mysql-define-own-mysql-port.dif",
            "//omd/packages/monitoring-plugins:patches/0009-check_dns-case-insensitive.dif",
            "//omd/packages/monitoring-plugins:patches/0010-get_omd_root_in_checks.dif",
            "//omd/packages/monitoring-plugins:patches/0011-check_http-sanitise-http-response-body.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
    )
