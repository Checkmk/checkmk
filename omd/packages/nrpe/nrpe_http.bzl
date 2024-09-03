load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def nrpe_workspace():
    version_str = "3.2.1"
    filename = "nrpe-" + version_str + ".tar.gz"
    http_archive(
        name = "nrpe",
        build_file = "@omd_packages//omd/packages/nrpe:BUILD.nrpe.bazel",
        strip_prefix = "nrpe-" + version_str,
        urls = [
            "https://github.com/NagiosEnterprises/nrpe/releases/download/" + "nrpe-" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "8ad2d1846ab9011fdd2942b8fc0c99dfad9a97e57f4a3e6e394a4ead99c0f1f0",
    )
