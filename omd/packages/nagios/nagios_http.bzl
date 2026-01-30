load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def nagios_workspace():
    version_str = "3.5.1"
    filename = "nagios-" + version_str + ".tar.gz"
    http_archive(
        name = "nagios",
        build_file = "@omd_packages//omd/packages/nagios:BUILD.nagios.bazel",
        strip_prefix = "nagios",
        patches = [
            "//omd/packages/nagios/patches:0001-do-not-copy-brokermodules.dif",
            "//omd/packages/nagios/patches:0002-include-omd-site-config.dif",
            "//omd/packages/nagios/patches:0003-remove-rrs-feed.dif",
            "//omd/packages/nagios/patches:0004-remove-updateversioninfo.dif",
            "//omd/packages/nagios/patches:0005-start-without-hosts-or-services.dif",
            "//omd/packages/nagios/patches:0006-fix_f5_reload_bug.dif",
            "//omd/packages/nagios/patches:0007-fix_downtime_struct.dif",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        urls = [
            "https://assets.nagios.com/downloads/nagioscore/releases/" + filename,
            UPSTREAM_MIRROR_URL + "/CMK-29802/" + filename,
        ],
        sha256 = "ca9dd68234fa090b3c35ecc8767b2c9eb743977eaf32612fa9b8341cc00a0f99",
    )
