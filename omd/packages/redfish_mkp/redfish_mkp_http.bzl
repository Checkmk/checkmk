load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")

def redfish_mkp(version_str, sha256):
    http_file(
        name = "redfish_mkp",
        url = "https://github.com/Yogibaer75/Check_MK-Things/raw/master/check%20plugins%202.3/redfish/redfish-" + version_str + ".mkp",
        sha256 = sha256,
    )
