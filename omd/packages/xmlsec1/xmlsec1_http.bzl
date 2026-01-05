load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def xmlsec_workspace():
    version_str = "1.3.8"
    filename = "xmlsec1-" + version_str + ".tar.gz"
    http_archive(
        name = "xmlsec1",
        urls = [
            "https://github.com/lsh123/xmlsec/releases/download/" + version_str + "/" + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "d0180916ae71be28415a6fa919a0684433ec9ec3ba1cc0866910b02e5e13f5bd",
        build_file = "@omd_packages//omd/packages/xmlsec1:BUILD.xmlsec1.bazel",
        strip_prefix = "xmlsec1-" + version_str,
    )
