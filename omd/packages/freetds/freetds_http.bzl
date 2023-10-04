load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def freetds(version_str, sha256):
    filename = "freetds-" + version_str + ".tar.gz"
    http_archive(
        name = "freetds",
        build_file = "@omd_packages//omd/packages/freetds:BUILD.freetds.bazel",
        urls = [
            "https://www.freetds.org/files/stable/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        strip_prefix = "freetds-" + version_str,
    )
