load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def nagios(version_str, sha256):
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
        sha256 = sha256,
    )
