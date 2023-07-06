load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def xmlsec1(version_str, sha256):
    filename = "xmlsec1-" + version_str + ".tar.gz"
    http_archive(
        name = "xmlsec1",
        urls = [
            "https://www.aleksey.com/xmlsec/download/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
        build_file = "@omd_packages//omd/packages/xmlsec1:BUILD.xmlsec1",
        strip_prefix = "xmlsec1-" + version_str,
    )
