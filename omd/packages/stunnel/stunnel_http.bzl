load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_archive")
load("//:bazel_variables.bzl", "UPSTREAM_MIRROR_URL")

def stunnel(version_str, sha256):
    http_archive(
        name="stunnel",
        build_file="@omd_packages//packages/stunnel:BUILD.stunnel.bazel",
        strip_prefix="stunnel-" + version_str,
        urls=[
            "https://ftp.nluug.nl/pub/networking/stunnel/archive/5.x/stunnel-"+ version_str + ".tar.gz",
            UPSTREAM_MIRROR_URL + "stunnel-"+ version_str + ".tar.gz",
        ],
        sha256=sha256,
    )
