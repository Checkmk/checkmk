load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def redfish_mkp_workspace():
    commit_hash = "35b0ef91252bbba9b147ec12dc120bcc70bb3cf6"
    version_str = "2.3.38"
    filename = "redfish-" + version_str + ".mkp"
    upstream_url = "https://github.com/Yogibaer75/Check_MK-Things/raw/" + commit_hash + "/check%20plugins%202.3/redfish/"

    http_file(
        name = "redfish_mkp",
        urls = [
            upstream_url + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = "c388a2b5525a55a6e0b175c014a3cb375062b4643d2ceed7ee188c054b2f0c8c",
    )
