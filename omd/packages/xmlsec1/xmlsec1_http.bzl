load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def xmlsec1(version_str, sha256):
    http_archive(
        name = "xmlsec1",
        urls = [
            "https://www.aleksey.com/xmlsec/download/xmlsec1-" + version_str + ".tar.gz",
            UPSTREAM_MIRROR_URL + "xmlsec1-" + version_str + ".tar.gz",
        ],
        sha256 = sha256,
        build_file = "@omd_packages//packages/xmlsec1:BUILD.xmlsec1",
        strip_prefix = "xmlsec1-" + version_str,
    )
