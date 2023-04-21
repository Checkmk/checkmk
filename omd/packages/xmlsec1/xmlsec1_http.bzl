load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")

XMLSEC1_VERSION = "1.2.37"

def xmlsec1():
    http_archive(
        name = "xmlsec1",
        urls = [
            "https://www.aleksey.com/xmlsec/download/xmlsec1-" + XMLSEC1_VERSION + ".tar.gz",
            "https://artifacts.lan.tribe29.com/repository/upstream-archives/xmlsec1-" + XMLSEC1_VERSION + ".tar.gz",
        ],
        sha256 = "5f8dfbcb6d1e56bddd0b5ec2e00a3d0ca5342a9f57c24dffde5c796b2be2871c",
        build_file = "@omd_packages//packages/xmlsec1:BUILD.xmlsec1",
        strip_prefix = "xmlsec1-" + XMLSEC1_VERSION,
    )
