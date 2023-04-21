load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

def xmlsec1(version_str, sha256):
    http_archive(
        name = "xmlsec1",
        urls = [
            "https://www.aleksey.com/xmlsec/download/xmlsec1-" + version_str + ".tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/xmlsec1-" + version_str + ".tar.gz",
        ],
        sha256 = sha256,
        build_file = "@omd_packages//packages/xmlsec1:BUILD.xmlsec1",
        strip_prefix = "xmlsec1-" + version_str,
    )
