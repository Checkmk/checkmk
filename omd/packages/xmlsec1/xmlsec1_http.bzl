load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def xmlsec_workspace():
    version_str = "1.2.37"
    filename = "xmlsec1-" + version_str + ".tar.gz"
    http_archive(
        name = "xmlsec1",
        urls = [
            "https://github.com/lsh123/xmlsec/releases/download/xmlsec-" + version_str.replace(".", "_") + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "5f8dfbcb6d1e56bddd0b5ec2e00a3d0ca5342a9f57c24dffde5c796b2be2871c",
        build_file = "@omd_packages//omd/packages/xmlsec1:BUILD.xmlsec1.bazel",
        strip_prefix = "xmlsec1-" + version_str,
    )
