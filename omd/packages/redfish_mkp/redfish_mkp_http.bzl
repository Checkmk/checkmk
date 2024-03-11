load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def redfish_mkp(commit_hash, version_str, sha256):
    filename = "redfish-" + version_str + ".mkp"
    upstream_url = "https://github.com/Yogibaer75/Check_MK-Things/raw/" + commit_hash + "/check%20plugins%202.3/redfish/"

    http_file(
        name = "redfish_mkp",
        urls = [
            upstream_url + filename,
            UPSTREAM_MIRROR_URL + filename,
        ],
        sha256 = sha256,
    )
