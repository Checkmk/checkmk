load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def pnp4nagios_workspace():
    version_str = "0.6.26"
    filename = "pnp4nagios-" + version_str + ".tar.gz"
    http_archive(
        name = "pnp4nagios",
        build_file = "@omd_packages//omd/packages/pnp4nagios:BUILD.pnp4nagios.bazel",
        strip_prefix = "pnp4nagios-" + version_str,
        urls = [
            UPSTREAM_MIRROR_URL + filename,
            "https://sourceforge.net/projects/pnp4nagios/files/PNP-0.6/" + filename,
        ],
        sha256 = "ab59a8a02d0f70de3cf89b12fe1e9216e4b1127bc29c04a036cd06dde72ee8fb",
    )
