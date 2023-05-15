load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def pnp4nagios(version_str, sha256):
    filename = "pnp4nagios-" + version_str + ".tar.gz"
    http_archive(
        name = "pnp4nagios",
        build_file = "@omd_packages//packages/pnp4nagios:BUILD.pnp4nagios.bazel",
        strip_prefix = "pnp4nagios-" + version_str,
        urls = [
            "https://sourceforge.net/projects/pnp4nagios/files/PNP-0.6/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
    )
