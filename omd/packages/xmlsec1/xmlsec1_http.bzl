load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def xmlsec_workspace():
    version_str = "1.3.0"
    filename = "xmlsec1-" + version_str + ".tar.gz"
    http_archive(
        name = "xmlsec1",
        urls = [
            "https://github.com/lsh123/xmlsec/releases/download/xmlsec_" + version_str.replace(".", "_") + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "df3ad2548288411fc3d44c20879e4c4e90684a1a4fb76a06ae444f957171c9a6",
        build_file = "@omd_packages//omd/packages/xmlsec1:BUILD.xmlsec1.bazel",
        strip_prefix = "xmlsec1-" + version_str,
    )
