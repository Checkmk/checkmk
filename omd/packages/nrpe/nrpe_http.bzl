load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def nrpe(version_str, sha256):
    filename = "nrpe-" + version_str + ".tar.gz"
    http_archive(
        name = "nrpe",
        build_file = "@omd_packages//packages/nrpe:BUILD.nrpe.bazel",
        strip_prefix = "nrpe-" + version_str,
        urls = [
            "https://github.com/NagiosEnterprises/nrpe/releases/download/" + "nrpe-" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
    )
