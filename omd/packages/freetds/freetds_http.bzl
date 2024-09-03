load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def freetds_workspace():
    version_str = "0.95.95"
    filename = "freetds-" + version_str + ".tar.gz"
    http_archive(
        name = "freetds",
        build_file = "@omd_packages//omd/packages/freetds:BUILD.freetds.bazel",
        urls = [
            "https://www.freetds.org/files/stable/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "be7c90fc771f30411eff6ae3a0d2e55961f23a950a4d93c44d4c488006e64c70",
        strip_prefix = "freetds-" + version_str,
    )
