load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def stunnel_workspace():
    version_str = "5.78"
    filename = "stunnel-" + version_str + ".tar.gz"
    http_archive(
        name = "stunnel",
        build_file = "@omd_packages//omd/packages/stunnel:BUILD.stunnel.bazel",
        strip_prefix = "stunnel-" + version_str,
        patches = [
            "//omd/packages/stunnel:0001-fix-hup-race-data-loss.patch",
            "//omd/packages/stunnel:0002-fix-hup-buffer-full-livelock.patch",
        ],
        patch_args = ["-p1"],
        patch_tool = "patch",
        urls = [
            "https://ftp.nluug.nl/pub/networking/stunnel/archive/5.x/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "8727e53bb8b7528f850327a2a149158422c02183bc120d1d733cc65b1e2c349d",
    )
