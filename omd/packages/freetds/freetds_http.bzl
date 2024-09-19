load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def freetds_workspace():
    version_str = "1.4.22"
    filename = "freetds-" + version_str + ".tar.gz"
    http_archive(
        name = "freetds",
        build_file = "@omd_packages//omd/packages/freetds:BUILD.freetds.bazel",
        urls = [
            "https://www.freetds.org/files/stable/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "6acb9086350425f5178e544bbe2d54a001097e8e20277a2b766ad0799a2e7d87",
        strip_prefix = "freetds-" + version_str,
    )
